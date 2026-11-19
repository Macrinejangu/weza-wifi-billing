"""Status values for payments and for internet activation.

A purchase is tracked on two INDEPENDENT tracks. Keeping them separate is a
core business rule: a successful payment must never be treated as working
internet, and a failed activation must never undo a successful payment.

    Payment track     (changed only by the Daraja callback handler)
        pending -> successful
        pending -> failed

    Activation track  (changed only by the activation coordinator)
        not_started -> waiting -> succeeded
                       waiting -> failed -> waiting   (staff retry)

Payment statuses are final once set. Activation may return from failed to
waiting only through a deliberate retry.
"""
from enum import StrEnum


class PaymentStatus(StrEnum):
    """Outcome of the M-Pesa payment attempt."""

    PENDING = "pending"  # STK Push sent; no verified result received yet
    SUCCESSFUL = "successful"  # Verified successful callback received
    FAILED = "failed"  # Cancelled, timed out or rejected; no money taken


class ActivationStatus(StrEnum):
    """Progress of granting the customer internet access on the router."""

    NOT_STARTED = "not_started"  # Payment not yet verified; nothing requested
    WAITING = "waiting"  # Activation requested; router has not confirmed
    SUCCEEDED = "succeeded"  # Router confirmed access is active
    FAILED = "failed"  # Router reported failure; staff can retry