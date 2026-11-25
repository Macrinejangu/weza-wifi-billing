"""Ask Safaricom what happened to a pending payment (WEZA-63).

Two entry points share one rule:
  check_payment()         one payment, started by staff from the dashboard.
  sweep_stale_payments()  every pending payment older than a threshold. Meant
                          to be run on a schedule, so a payment whose callback
                          never arrived is resolved without staff noticing.

Fail-closed rules:
* This module only ever sends the status QUERY, never an STK Push, so it can
  never prompt or charge a customer.
* Only a PAID answer changes a payment, and that is done by settle_from_query
  under row locks. UNKNOWN, FAILED and every Daraja error leave the payment
  pending: "we could not tell" is never treated as "failed".
* The status is read, the read transaction is ended, and only then is the
  network called, so no database lock is held during a slow Daraja request.
* One bad payment never stops a sweep: its error is counted and logged (type
  only, never messages that could carry request details) and the loop goes on.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.mpesa.errors import DarajaError
from app.integrations.mpesa.stk_query import StkQueryResult
from app.models import AdminAuditLog, Payment
from app.payments.settlement_plan import SettlementAction
from app.payments.statuses import PaymentStatus
from app.services.activation_recovery import DEFAULT_PENDING_AFTER
from app.services.callback_processing import StatusQuerier
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment
from app.services.query_settlement import Fulfiller, settle_from_query

logger = logging.getLogger(__name__)

AUDIT_ACTION = "Checked payment status with M-Pesa"

# One query per payment, one after another, so a big backlog cannot trip
# Daraja's spike arrest. A sweep that finds more simply continues next run.
DEFAULT_SWEEP_LIMIT = 20
MAX_SWEEP_LIMIT = 100

# "expired" is not set anywhere yet, but the payment states allow a late
# verified success to repair it, so it is checkable too.
_CHECKABLE_STATUSES = {PaymentStatus.PENDING.value, PaymentStatus.EXPIRED.value}


class CheckOutcome(StrEnum):
    """What a status check did, in terms staff and the sweeper understand."""

    SETTLED = "settled"  # Safaricom said PAID; payment is now successful
    ALREADY_SETTLED = "already_settled"  # a callback or another check got there first
    STILL_PENDING = "still_pending"  # Safaricom said unknown or failed; nothing changed
    REJECTED = "rejected"  # paid answer could not be applied; needs staff review
    NO_ANSWER = "no_answer"  # the query itself failed (timeout, Daraja down, no client)


class PaymentNotCheckable(Exception):
    """The payment cannot be checked. `code` is stable; `message` is safe to show staff."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CheckResult:
    payment_id: int
    outcome: CheckOutcome
    payment_status: str
    # What Safaricom said ("paid", "failed", "unknown"); None if no answer came.
    # Lets staff see a query-only "failed" that we deliberately did not apply.
    query_outcome: str | None
    fulfilment: FulfilmentOutcome | None = None


@dataclass(frozen=True)
class SweepSummary:
    examined: int
    settled: int
    already_settled: int
    still_pending: int
    rejected: int
    no_answer: int
    errors: int


_OUTCOME_FOR_ACTION = {
    SettlementAction.APPLY_SUCCESS: CheckOutcome.SETTLED,
    SettlementAction.ALREADY_SETTLED: CheckOutcome.ALREADY_SETTLED,
    SettlementAction.KEEP_PENDING: CheckOutcome.STILL_PENDING,
    SettlementAction.REJECT: CheckOutcome.REJECTED,
}


def check_payment(
    db: Session,
    daraja: StatusQuerier | None,
    payment_id: int,
    *,
    fulfil: Fulfiller = fulfil_payment,
    staff_id: int | None = None,
) -> CheckResult:
    """Ask Safaricom about one payment and apply a PAID answer.

    Raises:
        LookupError: the payment does not exist.
        PaymentNotCheckable: it is not open, or has no checkout request id.
    """
    status_before, checkout_request_id = _read_checkable(db, payment_id)
    db.rollback()  # end the read transaction BEFORE the network call

    query_result = _ask(daraja, checkout_request_id, payment_id)
    if query_result is None:
        result = CheckResult(payment_id, CheckOutcome.NO_ANSWER, status_before, None)
    else:
        settled = settle_from_query(
            db, payment_id=payment_id, query_result=query_result, fulfil=fulfil
        )
        result = CheckResult(
            payment_id=payment_id,
            # An action we do not recognise is treated as needing review.
            outcome=_OUTCOME_FOR_ACTION.get(settled.action, CheckOutcome.REJECTED),
            payment_status=settled.payment_status.value,
            query_outcome=query_result.outcome.value,
            fulfilment=settled.fulfilment,
        )

    if staff_id is not None:
        _record_staff_check(db, staff_id, status_before, result)
    return result


def sweep_stale_payments(
    db: Session,
    daraja: StatusQuerier | None,
    *,
    now: datetime | None = None,
    pending_after: timedelta = DEFAULT_PENDING_AFTER,
    limit: int = DEFAULT_SWEEP_LIMIT,
    fulfil: Fulfiller = fulfil_payment,
) -> SweepSummary:
    """Check every pending payment older than `pending_after`, lowest id first.

    Safe to run twice at once or to overlap a late callback: the settlement
    itself is guarded by row locks, so a payment is settled at most once.
    """
    if not 1 <= limit <= MAX_SWEEP_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_SWEEP_LIMIT}")
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now - pending_after

    payment_ids = db.scalars(
        select(Payment.id)
        .where(Payment.status == PaymentStatus.PENDING.value)
        # Nothing to ask Safaricom about without a checkout id. The finder
        # still lists these as stale for staff.
        .where(Payment.checkout_request_id.is_not(None))
        .where(func.coalesce(Payment.initiated_at, Payment.created_at) <= cutoff)
        .order_by(Payment.id)
        .limit(limit)
    ).all()
    db.rollback()

    counts = dict.fromkeys(CheckOutcome, 0)
    errors = 0
    for payment_id in payment_ids:
        try:
            result = check_payment(db, daraja, payment_id, fulfil=fulfil)
        except PaymentNotCheckable:
            # A callback settled it between our list and our check: fine.
            counts[CheckOutcome.ALREADY_SETTLED] += 1
        except (LookupError, ValueError, SQLAlchemyError) as error:
            db.rollback()
            errors += 1
            logger.error(
                "sweep could not check payment: payment_id=%s error=%s",
                payment_id, type(error).__name__,
            )
        else:
            counts[result.outcome] += 1

    summary = SweepSummary(
        examined=len(payment_ids),
        settled=counts[CheckOutcome.SETTLED],
        already_settled=counts[CheckOutcome.ALREADY_SETTLED],
        still_pending=counts[CheckOutcome.STILL_PENDING],
        rejected=counts[CheckOutcome.REJECTED],
        no_answer=counts[CheckOutcome.NO_ANSWER],
        errors=errors,
    )
    logger.info("sweep finished: %s", summary)
    return summary


def _read_checkable(db: Session, payment_id: int) -> tuple[str, str]:
    row = db.execute(
        select(Payment.status, Payment.checkout_request_id).where(Payment.id == payment_id)
    ).one_or_none()
    if row is None:
        raise LookupError("Payment not found")
    status, checkout_request_id = row
    if status not in _CHECKABLE_STATUSES:
        raise PaymentNotCheckable("payment_not_open", "Only a pending payment can be checked.")
    if not checkout_request_id:
        raise PaymentNotCheckable(
            "no_checkout_request_id",
            "This payment has no M-Pesa request to check. It needs staff review.",
        )
    return status, checkout_request_id


def _ask(
    daraja: StatusQuerier | None, checkout_request_id: str, payment_id: int
) -> StkQueryResult | None:
    """One status query. Any failure to get an answer returns None."""
    if daraja is None:
        logger.error("status check skipped, Daraja not configured: payment_id=%s", payment_id)
        return None
    try:
        return daraja.stk_query(checkout_request_id)
    except (DarajaError, ValueError) as error:
        # Type only: messages could carry request details.
        logger.warning(
            "status check gave no answer: payment_id=%s error=%s",
            payment_id, type(error).__name__,
        )
        return None


def _record_staff_check(
    db: Session, staff_id: int, status_before: str, result: CheckResult
) -> None:
    """Who checked what, and what came of it. Never lets an audit problem
    change the answer the staff member gets."""
    try:
        db.add(AdminAuditLog(
            admin_id=staff_id,
            action=AUDIT_ACTION,
            entity_type="payment",
            entity_id=result.payment_id,
            description=f"Staff checked payment status ({result.outcome.value}).",
            old_values={"payment_status": status_before},
            new_values={
                "outcome": result.outcome.value,
                "query_outcome": result.query_outcome,
                "payment_status": result.payment_status,
            },
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("could not record staff payment check: payment_id=%s", result.payment_id)
        