"""Apply a verified M-Pesa callback to a payment (WEZA-50, phase 2).

Phase 1 (the route) parses and verifies the callback and asks Safaricom's
status query. It runs WITHOUT a database lock because it makes a network
call. This module is phase 2: one short transaction that

1. locks the payment row (SELECT ... FOR UPDATE),
2. re-reads its status UNDER the lock,
3. lets decide_settlement() choose the action,
4. applies it and marks the audit event, then
5. commits once.

Why the database does the work: two identical callbacks can arrive in the
same instant. The row lock makes the second one wait, and when it resumes it
sees the first one's result and does nothing. Python-level "if already paid"
checks without a lock would let both through.

Payment status only. Activation (granting internet) is a separate state
handled later (WEZA-51); this module never touches the network service.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.mpesa.callback_payload import StkCallback
from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.models import Payment, Purchase
from app.payments.callback_verification import CallbackVerdict
from app.payments.result_codes import failure_reason_for
from app.payments.settlement_plan import SettlementAction, decide_settlement
from app.payments.statuses import PaymentStatus
from app.services.payment_event_outcome import mark_event_outcome
from app.services.payment_event_service import EventOutcome

# Purchase statuses (ck_purchases_status). A purchase can be paid only from
# these two; anything else means the purchase was already settled or closed.
PURCHASE_PAID = "paid"
_PAYABLE_PURCHASE_STATUSES = {"pending", "expired"}

# payments.result_desc is Text, but we still cap what we store from a sender
# we cannot authenticate. The full body is kept in raw_callback anyway.
MAX_RESULT_DESC_CHARS = 500

# How each action is recorded on the audit event.
_EVENT_OUTCOME = {
    SettlementAction.APPLY_SUCCESS: EventOutcome.APPLIED,
    SettlementAction.APPLY_FAILURE: EventOutcome.APPLIED,
    SettlementAction.ALREADY_SETTLED: EventOutcome.DUPLICATE,
    SettlementAction.REJECT: EventOutcome.REJECTED,
    SettlementAction.KEEP_PENDING: EventOutcome.REJECTED,
}


@dataclass(frozen=True)
class SettlementResult:
    """What happened, for the route's reply and for logging."""

    action: SettlementAction
    payment_id: int
    payment_status: PaymentStatus


def settle_payment(
    db: Session,
    *,
    event_id: int,
    payment_id: int,
    verdict: CallbackVerdict,
    query_outcome: StkQueryOutcome | None,
    callback: StkCallback,
    raw_payload: dict[str, Any],
) -> SettlementResult:
    """Apply the callback in one transaction and commit.

    The amount, phone and IDs were verified in phase 1 against stored
    columns that never change after initiation, so they need no re-check
    here. The STATUS does change, which is why it is re-read under the lock.

    Raises:
        LookupError: the payment does not exist.
        ValueError: the event already has a final outcome, or the stored
            status is not a known value. Nothing is changed.
    Any exception rolls the whole transaction back and is re-raised.
    """
    try:
        result = _settle_under_lock(
            db,
            event_id=event_id,
            payment_id=payment_id,
            verdict=verdict,
            query_outcome=query_outcome,
            callback=callback,
            raw_payload=raw_payload,
        )
        db.commit()
    except Exception:
        db.rollback()  # event stays 'received': honest "not processed"
        raise
    return result


def _settle_under_lock(
    db: Session,
    *,
    event_id: int,
    payment_id: int,
    verdict: CallbackVerdict,
    query_outcome: StkQueryOutcome | None,
    callback: StkCallback,
    raw_payload: dict[str, Any],
) -> SettlementResult:
    payment = db.execute(
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
        # Phase 1 may have loaded this payment into the session already.
        # Without this, SQLAlchemy would reuse the stale in-memory status.
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if payment is None:
        raise LookupError(f"payment {payment_id} does not exist")

    action = decide_settlement(
        verdict=verdict,
        current_status=PaymentStatus(payment.status),
        query_outcome=query_outcome,
    )
    note: str | None = None

    if action is SettlementAction.APPLY_SUCCESS:
        conflict = _apply_success(db, payment, callback, raw_payload)
        if conflict is not None:
            action, note = SettlementAction.REJECT, conflict
    elif action is SettlementAction.APPLY_FAILURE:
        _apply_failure(payment, callback, raw_payload)
    elif action is SettlementAction.ALREADY_SETTLED:
        note = f"repeat callback; payment already {payment.status}"
    elif action is SettlementAction.KEEP_PENDING:
        note = "not confirmed by status query; payment left unchanged"
    else:
        note = f"callback not applied: {verdict.value}"

    mark_event_outcome(
        db,
        event_id=event_id,
        outcome=_EVENT_OUTCOME[action],
        payment_id=payment.id,
        note=note,
    )
    return SettlementResult(
        action=action,
        payment_id=payment.id,
        payment_status=PaymentStatus(payment.status),
    )


def _apply_success(
    db: Session,
    payment: Payment,
    callback: StkCallback,
    raw_payload: dict[str, Any],
) -> str | None:
    """Mark payment successful and purchase paid. Return a note on conflict.

    Lock order is always payment then purchase, so two workers cannot
    deadlock each other.
    """
    purchase = db.execute(
        select(Purchase)
        .where(Purchase.id == payment.purchase_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    if purchase.status not in _PAYABLE_PURCHASE_STATUSES:
        return f"purchase is {purchase.status}; payment needs staff review"

    now = datetime.now(UTC)
    try:
        # Savepoint: if a unique index rejects the change, only this block
        # is undone and the audit event can still be recorded.
        with db.begin_nested():
            payment.status = PaymentStatus.SUCCESSFUL.value
            payment.mpesa_receipt_number = callback.mpesa_receipt_number
            payment.result_code = callback.result_code
            payment.result_desc = (callback.result_desc or "")[:MAX_RESULT_DESC_CHARS]
            payment.raw_callback = raw_payload
            payment.callback_received_at = now
            payment.paid_at = now
            purchase.status = PURCHASE_PAID
            db.flush()
    except IntegrityError:
        # uq_one_successful_payment or the unique receipt number.
        db.refresh(payment)
        return "conflicts with an existing successful payment or receipt"
    return None


def _apply_failure(
    payment: Payment, callback: StkCallback, raw_payload: dict[str, Any]
) -> None:
    """Mark the payment failed. The purchase stays pending so the customer
    can try again with a new payment."""
    payment.status = PaymentStatus.FAILED.value
    payment.result_code = callback.result_code
    payment.result_desc = (callback.result_desc or "")[:MAX_RESULT_DESC_CHARS]
    # Our own vocabulary, never raw Daraja text.
    payment.failure_reason = failure_reason_for(callback.result_code).value
    payment.raw_callback = raw_payload
    payment.callback_received_at = datetime.now(UTC)