"""Status values for payments and for internet activation.

A purchase is tracked on two INDEPENDENT tracks. Keeping them separate is a
core business rule: a successful payment must never be treated as working
internet, and a failed activation must never undo a successful payment.

    Payment track     (changed only by payment verification code)
        pending -> successful   verified success
        pending -> failed       Safaricom reported a failure (final)
        pending -> expired      our own timeout; the outcome is UNKNOWN
        expired -> successful   a late verified success repairs it

Only "failed" (reported by Safaricom) and "successful" are final. "expired"
is not a failure: we simply stopped waiting, so money may still have moved.

    Activation track  (changed only by the activation coordinator)
        not_started -> waiting -> succeeded
                       waiting -> failed -> waiting   (staff retry)

Activation may return from failed to waiting only through a deliberate retry.
"""
from enum import StrEnum


class PaymentStatus(StrEnum):
    """Outcome of the M-Pesa payment attempt."""

    PENDING = "pending"  # STK Push sent; no verified result received yet
    SUCCESSFUL = "successful"  # Verified successful result received
    FAILED = "failed"  # Safaricom reported failure; no money taken (final)
    EXPIRED = "expired"  # Our timeout fired; outcome unknown, may be repaired


class ActivationStatus(StrEnum):
    """Progress of granting the customer internet access on the router."""

    NOT_STARTED = "not_started"  # Payment not yet verified; nothing requested
    WAITING = "waiting"  # Activation requested; router has not confirmed
    SUCCEEDED = "succeeded"  # Router confirmed access is active
    FAILED = "failed"  # Router reported failure; staff can retry
