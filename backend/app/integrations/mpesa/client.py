"""Client for the Safaricom Daraja API (sandbox only).

This step provides the OAuth access token. Later steps add the STK Push call
to the same class.

Design rules, because this code sits in the payment path:
  * Every outbound call has an explicit timeout.
  * Only idempotent calls are retried. Fetching a token is safe to repeat. An
    STK Push is NEVER retried, since a repeat could prompt the customer twice.
  * Errors are raised as the types in errors.py so callers can tell "Daraja
    refused" from "outcome unknown".
  * Tokens, keys and response bodies never appear in logs or error messages.
"""

import logging
import threading
import time
from collections.abc import Callable

import httpx

from app.config import DarajaSettings
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaError,
    DarajaMalformedResponseError,
    DarajaRejectedError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.integrations.mpesa.stk_body import build_stk_push_body
from app.payments.daraja_password import daraja_timestamp
from app.integrations.mpesa.token_cache import TokenCache
from dataclasses import dataclass


logger = logging.getLogger(__name__)

# Sandbox only. The project never talks to the production Daraja API, and
# config.daraja_settings() refuses any environment other than "sandbox".
SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
TOKEN_PATH = "/oauth/v1/generate"

# Kept short so a customer waits at most ~16 seconds in the worst case
# (3 attempts x 5 s, plus the pauses between them) before seeing an error.
TOKEN_TIMEOUT_SECONDS = 5.0
TOKEN_MAX_ATTEMPTS = 3
TOKEN_RETRY_DELAY_SECONDS = 0.5 # multiplied by the attempt number

STK_PUSH_PATH = "/mpesa/stkpush/v1/processrequest"

# One attempt only. An STK Push is never retried: a repeat could put a second
# prompt on the customer's phone.
STK_PUSH_TIMEOUT_SECONDS = 10.0

# Daraja's text fields are untrusted: keep only short strings for logs.
_MAX_LOGGED_TEXT = 100


@dataclass(frozen=True)
class StkPushAccepted:
    """Daraja ACCEPTED the request and prompted the customer.

    This does NOT mean the customer paid. The payment is only settled by the
    callback (or the status query). Store these IDs on the pending payment: the
    CheckoutRequestID is how the callback is matched to it.
    """
    checkout_request_id: str
    merchant_request_id: str

def _safe_text(value: object) -> str | None:
    """Return `value` only if it is a short string, else None."""
    if isinstance(value, str) and 0 < len(value) <= _MAX_LOGGED_TEXT:
        return value
    return None




class DarajaClient:
    """Talks to Daraja on behalf of the payment service.

    `http_client` and `sleep` are passed in so tests can fake the network and
    skip real pauses.
    """

    def __init__(
            self,
            settings: DarajaSettings,
            http_client: httpx.Client,
            token_cache: TokenCache | None = None,
            sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._http=http_client
        self._token_cache = token_cache if token_cache is not None else TokenCache()
        self._sleep=sleep
        # One lock for the whole "check cache, fetch, store" sequence. 
        # Each new token invalidates the previous one, so concurrent fetches would break each other's tokens.
        self._token_lock = threading.Lock()


    def get_access_token(self) -> str:
        """Return a valid access token, fetching a new one only if needed.

        Raises DarajaAuthError, DarajaTimeoutError or DarajaUnavailableError.
        Nothing has been sent to the customer when these are raised.
        """
        with self._token_lock:
            # Check inside the lock: a request that waited for the lock should
            # reuse the token the first request just fetched.
            token = self._token_cache.get()
            if token is not None:
                return token

            token, expires_in = self._fetch_token()
            self._token_cache.store(token, expires_in)
            return token

    def invalidate_token(self) -> None:
        """Forget the cached token, for example after Daraja rejects it."""
        with self._token_lock:
            self._token_cache.invalidate()

    def _fetch_token(self) -> tuple[str, int]:
        """Request a token from Daraja, retrying transient failures."""
        url = f"{SANDBOX_BASE_URL}{TOKEN_PATH}"
        last_error: DarajaError = DarajaUnavailableError("Token request was not attempted.")

        for attempt in range(1, TOKEN_MAX_ATTEMPTS + 1):
            try:
                response = self._http.get(
                    url,
                    params={"grant_type":"client_credentials"},
                    auth=(self._settings.consumer_key, self._settings.consumer_secret),
                    timeout=TOKEN_TIMEOUT_SECONDS,
                )
            except httpx.TimeoutException:
                # Must be caught before TransportError, which it belongs to.
                last_error = DarajaTimeoutError("Daraja token request timed out.")
            except httpx.TransportError:
                last_error = DarajaUnavailableError ("Could not reach Daraja for a token.")
            else:
                if response.status_code < 500:
                    # A definite answer: parse it. Do not retry refusals.
                    return self._parse_token_response(response)
                last_error = DarajaUnavailableError(
                    f"Daraja token endpoint returned HTTP {response.status_code}."
                )

            logger.warning(
                "Daraja token request failed (attempt %d of %d): %s",
                attempt,
                TOKEN_MAX_ATTEMPTS,
                type(last_error).__name__,
            )
            if attempt < TOKEN_MAX_ATTEMPTS:
                self._sleep(TOKEN_RETRY_DELAY_SECONDS * attempt)

        raise last_error

    @staticmethod
    def _parse_token_response(response: httpx.Response) -> tuple[str, int]:
        """Validate Daraja's token response. Never trust its shape or types."""
        if response.status_code != 200:
            # Wrong credentials and similar. The body is deliberately not included: error bodies can echo request details.
            raise DarajaAuthError(
                f"Daraja refused the token request (HTTP {response.status_code})."
            )
        try:
            body = response.json()
            token = body["access_token"]
            # Daraja documents expires_in inconsistently (string or number).
            expires_in = int(body["expires_in"])
        except(ValueError, KeyError, TypeError):
            # `from None` so the original error, which may hold body text, is not attached to the exception and written to logs.
            raise DarajaAuthError("Daraja returned an unusable token response.") from None
        if not isinstance(token, str) or not token:
            raise DarajaAuthError("Daraja returned an unusable token response.")
        if expires_in <= 0:
            # A token that is already expired is unusable. Reject it here so the
            # cache's ValueError never escapes as an unhandled error.
            raise DarajaAuthError("Daraja returned an unusable token response.")
        return token, expires_in

    def stk_push(
            self,
            *,
            amount: int,
            phone_number: str,
            account_reference: str,
            description: str,
            timestamp: str | None=None
    ) -> StkPushAccepted:
        """Ask Daraja to prompt the customer to pay. Sends ONE request, never retries.

        Raises ValueError if an input is invalid (nothing is sent). Otherwise:
        * DarajaAuthError: no token, so NOTHING was sent.
        * DarajaRejectedError: Daraja refused. No prompt was sent.
        * DarajaTimeoutError, DarajaUnavailableError,
            DarajaMalformedResponseError: the outcome is UNKNOWN (see
            `outcome_unknown`). The customer may already have a prompt, so the
            caller must record the payment as pending, resolve it with the
            status query, and must not retry this call.

        `timestamp` exists for tests. Normally it is generated here, AFTER the
        token is obtained, because token retries can take many seconds.
        """
        try:
            token=self.get_access_token()
        except  DarajaError as error:
            # Token errors can say "outcome unknown", but no push was sent yet.
            raise DarajaAuthError(
                "Could not obtain an access token; no push was sent."
            ) from error

        stamp = timestamp if timestamp is not None else daraja_timestamp()
        body = build_stk_push_body(
            self._settings,
            amount=amount,
            phone_number=phone_number,
            account_reference=account_reference,
            description=description,
            timestamp=stamp,
        )

        try:
            response = self._http.post(
                f"{SANDBOX_BASE_URL}{STK_PUSH_PATH}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=STK_PUSH_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException:
            # `from None`: the original error is not needed and is kept out of logs.
            raise DarajaTimeoutError("Daraja STK Push timed out; outcome unknown.") from None
        except httpx.TransportError:
            # We cannot tell whether the request arrived, so the outcome is unknown.
            raise DarajaUnavailableError("Could not complete the STK Push request; outcome unknown.")from None

        return self._parse_stk_push_response(response)

    def _parse_stk_push_response(self, response: httpx.Response) -> StkPushAccepted:
        """Validate Daraja's reply. Never trust its shape or types."""
        status = response.status_code
        if status >= 500:
            raise DarajaUnavailableError(
                f"Daraja returned HTTP {status} for the push; outcome unknown."
            )

        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            body = {}

        if status != 200:
            if status in (401, 403):
                # The token may have been invalidated elsewhere. Drop it so the
                # next request fetches a fresh one. This push is NOT retried.
                self.invalidate_token()
            raise DarajaRejectedError(
                f"Daraja refused the STK Push (HTTP {status}).",
                http_status=status,
                error_code=_safe_text(body.get("errorCode")),
                request_id=_safe_text(body.get("requestId")),
            )

        raw_code = body.get("ResponseCode")
        if raw_code is None:
            raise DarajaMalformedResponseError("Daraja push reply had no ResponseCode; outcome unknown.")
        # Accepted only for exactly "0" or 0. Anything else fails closed.
        if str(raw_code).strip() != "0":
            raise DarajaRejectedError(
                "Daraja did not accept the STK Push.",
                http_status=200,
                error_code=_safe_text(str(raw_code)),
                request_id=_safe_text(body.get("requestId")),
            )

        checkout_id = body.get("CheckoutRequestID")
        merchant_id = body.get("MerchantRequestID")

        if (
            not isinstance(checkout_id, str)
            or not checkout_id
            or not isinstance(merchant_id, str)
            or not merchant_id
        ):
            # Daraja said "accepted" but gave us nothing to match the callback
            # to. The prompt may exist, so the outcome is unknown.
            raise DarajaMalformedResponseError("Daraja push reply was missing request IDs; outcome unknown.")

        logger.info("STK Push accepted: checkout_request_id=%s", checkout_id)
        return StkPushAccepted(
            checkout_request_id=checkout_id,
            merchant_request_id=merchant_id,
        )