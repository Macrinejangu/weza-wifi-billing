"""Safe staff retry for a paid customer who is not connected (WEZA-63).

A retry only runs fulfil_payment again. It never starts, repeats or checks a
payment with M-Pesa: nothing in this module imports the Daraja client.

Rules:
* Only a verified (successful) payment can be retried.
* Only cases a retry can actually fix are retried. Everything else is refused
  with a fixed code, so staff are never offered a button that cannot work.
* Every accepted retry is written to the audit log BEFORE the router is called
  and completed afterwards, so a crash mid-retry leaves a visible trace.
* Duplicates are prevented by the row locks inside fulfil_payment: a second
  retry after success is refused, and never makes a second router call.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdminAuditLog, Payment
from app.services.activation_recovery import RecoveryReason, get_case
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment

logger = logging.getLogger(__name__)

AUDIT_ACTION = "Retried payment activation"

_RETRYABLE_REASONS = {
    RecoveryReason.PAID_NO_SESSION,
    RecoveryReason.NOT_STARTED,
    RecoveryReason.FAILED,
    RecoveryReason.UNCONFIRMED,
}


class RetryRefused(Exception):
    """A retry was not started. `code` is stable; `message` is safe to show staff."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RetryResult:
    payment_id: int
    session_id: int | None
    outcome: FulfilmentOutcome
    reason_before: RecoveryReason
    audit_id: int


def retry_activation(
    db: Session,
    payment_id: int,
    *,
    staff_id: int,
    router: Callable[[int], dict] | None = None,
    require_device: bool = False,
    now: datetime | None = None,
) -> RetryResult:
    """Retry network activation for one paid customer.

    Raises:
        LookupError: the payment does not exist.
        RetryRefused: the case cannot or need not be retried.
    """
    payment_status = db.scalar(select(Payment.status).where(Payment.id == payment_id))
    if payment_status is None:
        raise LookupError("Payment not found")
    if payment_status != "successful":
        raise RetryRefused(
            "payment_not_confirmed",
            "Only a confirmed payment can be retried.",
        )

    # grace=0: staff decide when to retry, so the automatic waiting period
    # does not apply. Locks inside fulfil_payment keep this safe.
    case = get_case(
        db, payment_id, now=now, require_device=require_device, grace=timedelta(0)
    )
    if case is None:
        raise RetryRefused("nothing_to_retry", "This customer is already connected.")
    if case.reason not in _RETRYABLE_REASONS:
        raise RetryRefused(
            "needs_staff_review",
            "A retry cannot fix this case. It needs staff review.",
        )

    audit = AdminAuditLog(
        admin_id=staff_id,
        action=AUDIT_ACTION,
        entity_type="payment",
        entity_id=payment_id,
        description=f"Staff retried activation ({case.reason.value}).",
        old_values={
            "reason": case.reason.value,
            "session_id": case.session_id,
            "session_status": case.session_status,
            "activation_status": case.activation_status,
            "last_error_code": case.last_error_code,
        },
    )
    db.add(audit)
    db.commit()  # committed first: fulfil_payment ends with a rollback
    audit_id = audit.id

    result = fulfil_payment(db, payment_id, router=router)

    try:
        finished = db.get(AdminAuditLog, audit_id)
        finished.new_values = {
            "outcome": result.outcome.value,
            "session_id": result.session_id,
        }
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("could not record retry outcome: audit_id=%s", audit_id)

    return RetryResult(
        payment_id=payment_id,
        session_id=result.session_id,
        outcome=result.outcome,
        reason_before=case.reason,
        audit_id=audit_id,
    )
