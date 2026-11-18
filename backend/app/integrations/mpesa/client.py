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
from app.integrations.mpesa.errors import(
    DarajaAuthError,
    DarajaError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.integrations.mpesa.token_cache import TokenCache

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
                    f"Daraja toke endpoint returned HTTP {response.status_code}."
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
                f"Daraja refused the token request (HTTP {response.status_code})"
            )
        try:
            body = response.json()
            token = body["access_token"]
            # Daraja documents expires_in inconsistently (string or number).
            expires_in = int(body["expires_in"])
        except(ValueError, KeyError, TypeError):
            # `from None` so the original error, which may hold body text, is not attached to the exception and written to logs.
            raise DarajaAuthError("Daraja returned an unusable token response.")
        if not isinstance(token, str) or not token:
            raise DarajaAuthError("Daraja returned an unusable token response.")
        return token, expires_in