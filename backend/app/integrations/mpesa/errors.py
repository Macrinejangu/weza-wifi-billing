"""Errors raised by the Daraja client.

Callers must be able to tell "Daraja refused this" apart from "we do not know
what happened". Each error therefore carries `outcome_unknown`:

    False  Nothing was sent, or Daraja clearly refused. Safe to report a
           failure to the caller.
    True   The request may have reached Daraja (timeout, bad response). For an
           STK Push the customer may already have a prompt on their phone, so
           the caller must record the payment as PENDING and resolve it later
           with the status query. It must never retry the push or mark the
           payment failed.

Messages in these errors end up in logs. Never put access tokens, the consumer
secret, the passkey or full phone numbers in them. Never show them to
customers either: the API layer maps each error to a safe, generic response.
"""

class DarajaError(Exception):
    """Base class for every error raised by the Daraja client."""

    # Fail closed: unless a subclass proves otherwise, we assume the request did not succeed. 
    # Subclasses where the outcome is truly uncertain set True.
    outcome_unknown: bool=False


class DarajaAuthError(DarajaError):
    """The OAuth access token could not be obtained.

    Usually wrong or missing credentials in our own configuration, or Daraja
    refusing the token request. It happens before any payment request is sent,
    so nothing was charged.
    """

class DarajaUnavailableError(DarajaError):
    """Daraja could not be reached or answered with a server error (HTTP 5xx).

    We cannot tell whether the request was processed, so the outcome is unknown.
    """
    outcome_unknown=True

class DarajaTimeoutError(DarajaUnavailableError):
    """Daraja did not answer within our timeout.

    A separate type so the API layer can answer 504 rather than 502. Like its
    parent, the outcome is unknown: the prompt may still reach the customer.
    """

class DarajaMalformedResponseError(DarajaError):
    """Daraja answered, but the body is not the shape we expect.

    We never trust a response we cannot validate, and we cannot tell whether
    the request was accepted, so the outcome is unknown.
    """
    outcome_unknown=True

class DarajaRejectedError(DarajaError):
    """Daraja clearly refused the request, for example with an error body.

    `error_code` and `request_id` come from Daraja's error body when present.
    They are for logs and admin investigation only. Customer-facing messages
    come from our own failure-reason codes, never from Daraja's raw text.
    """

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        error_code: str | None = None,
        request_id: str | None = None,) -> None:
        super().__init__(message)
        self.http_status=http_status
        self.error_code=error_code
        self.request_id=request_id