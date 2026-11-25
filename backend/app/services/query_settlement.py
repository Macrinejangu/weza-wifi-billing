"""Settle a pending payment from Safaricom's status query, with no callback (WEZA-63).

Why this exists: if the callback never arrives (our server was down, Safaricom
gave up), a customer can pay and stay "pending" forever. The status query asks
Safaricom directly what happened to OUR CheckoutRequestID.

Fail-closed rules enforced here:
* Only a PAID answer settles a payment. UNKNOWN changes nothing. FAILED also
  changes nothing: the official Daraja text for the query has not been fully
  verified, so a query-only "failed" is left pending for staff to review.
* The query reply carries no amount, phone or receipt. A payment settled this
  way therefore has mpesa_receipt_number NULL and callback_received_at NULL.
  Staff can match it to the M-Pesa statement later.
* The decision is made UNDER a row lock on the payment (then the purchase, the
  same lock order as payment_settlement.py), so two sweeps, or a sweep racing
  a late callback, settle at most once. The database decides, not Python.
* Fulfilment (session plus router call) runs only after the settlement is
  committed, and only for a freshly applied success.

The audit event carries payload key "origin": "status_query" so it can be told
apart from a replayed callback (payload key replay_of_event_id).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import Payment, Purchase
from app.payments.settlement_plan import SettlementAction, decide_query_settlement
from app.payments.statuses import PaymentStatus
from app.services.payment_event_outcome import mark_event_outcome
from app.services.payment_event_service import (
    EventOutcome,
    EventSource,
    record_received_event,
)
from app.services.payment_fulfilment import (
    FulfilmentOutcome,
    FulfilmentResult,
    fulfil_payment,
)
from app.services.payment_settlement import (
    _PAYABLE_PURCHASE_STATUSES,  # reused so both settlement paths agree
    MAX_RESULT_DESC_CHARS,
    PURCHASE_PAID,
)

logger = logging.getLogger(__name__)

# Marks audit rows written by this module (see module docstring).
QUERY_ORIGIN = "status_query"

# Same shape as fulfil_payment, injected so tests can fake the router.
Fulfiller = Callable[[Session, int], FulfilmentResult]

_EVENT_OUTCOME = {
    SettlementAction.APPLY_SUCCESS: EventOutcome.APPLIED,
    SettlementAction.ALREADY_SETTLED: EventOutcome.DUPLICATE,
    SettlementAction.REJECT: EventOutcome.REJECTED,
    SettlementAction.KEEP_PENDING: EventOutcome.REJECTED,
}


@dataclass(frozen=True)
class QuerySettlementResult:
    """What happened, for the sweeper, the staff route and logs."""

    action: SettlementAction
    payment_id: int
    payment_status: PaymentStatus
    # None unless this call freshly applied a success.
    fulfilment: FulfilmentOutcome | None = None


def settle_from_query(
    db: Session,
    *,
    payment_id: int,
    query_result: StkQueryResult,
    fulfil: Fulfiller = fulfil_payment,
) -> QuerySettlementResult:
    """Apply one status-query answer to one payment.

    Raises:
        LookupError: the payment does not exist.
        ValueError: the stored payment status is not a known value. Nothing
            is changed.
    Any database error rolls back and is re-raised; the audit event then
    stays 'received', an honest "not processed".
    """
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise LookupError(f"payment {payment_id} does not exist")
    checkout_request_id = payment.checkout_request_id

    if query_result.outcome is not StkQueryOutcome.PAID:
        # UNKNOWN: we could not tell. FAILED: not trusted on its own yet.
        # Either way nothing is written, so repeated sweeps add no rows.
        logger.info(
            "status query did not confirm payment: payment_id=%s outcome=%s",
            payment_id, query_result.outcome.value,
        )
        return QuerySettlementResult(
            SettlementAction.KEEP_PENDING, payment_id, PaymentStatus(payment.status)
        )

    # Audit first (commits at once). Because the row exists before we lock,
    # a crash mid-settlement leaves a visible 'received' row.
    event_id = record_received_event(
        db,
        source=EventSource.QUERY,
        payload={
            "origin": QUERY_ORIGIN,
            "query_outcome": query_result.outcome.value,
            "result_code": query_result.result_code,
        },
        checkout_request_id=checkout_request_id,
        result_code=query_result.result_code,
    )

    try:
        result = _settle_under_lock(db, event_id, payment_id, query_result)
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "query settlement: payment_id=%s checkout_request_id=%s action=%s",
        payment_id, checkout_request_id, result.action.value,
    )

    if result.action is SettlementAction.APPLY_SUCCESS:
        fulfilment = _fulfil_safely(db, fulfil, payment_id)
        return QuerySettlementResult(
            result.action, payment_id, result.payment_status, fulfilment
        )
    return result


def _settle_under_lock(
    db: Session, event_id: int, payment_id: int, query_result: StkQueryResult
) -> QuerySettlementResult:
    payment = db.execute(
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
        # The status was read earlier without a lock; re-read the real row.
        .execution_options(populate_existing=True)
    ).scalar_one()

    action = decide_query_settlement(
        current_status=PaymentStatus(payment.status),
        query_outcome=StkQueryOutcome.PAID,
    )
    note: str | None = None

    if action is SettlementAction.APPLY_SUCCESS:
        conflict = _apply_success(db, payment, query_result)
        if conflict is not None:
            action, note = SettlementAction.REJECT, conflict
    elif action is SettlementAction.ALREADY_SETTLED:
        note = f"status query repeat; payment already {payment.status}"
    else:
        note = f"status query says paid but payment is {payment.status}; staff review"
        action = SettlementAction.REJECT

    mark_event_outcome(
        db,
        event_id=event_id,
        outcome=_EVENT_OUTCOME[action],
        payment_id=payment.id,
        note=note,
    )
    return QuerySettlementResult(action, payment.id, PaymentStatus(payment.status))


def _apply_success(
    db: Session, payment: Payment, query_result: StkQueryResult
) -> str | None:
    """Mark payment successful and purchase paid. Return a note on conflict.

    Lock order is payment (already held) then purchase.
    """
    purchase = db.execute(
        select(Purchase)
        .where(Purchase.id == payment.purchase_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    if purchase.status not in _PAYABLE_PURCHASE_STATUSES:
        return f"purchase is {purchase.status}; payment needs staff review"

    try:
        # Savepoint: if a unique index rejects the change, only this block is
        # undone and the audit event can still be recorded.
        with db.begin_nested():
            payment.status = PaymentStatus.SUCCESSFUL.value
            payment.result_code = query_result.result_code
            payment.result_desc = (query_result.result_desc or "")[:MAX_RESULT_DESC_CHARS]
            payment.paid_at = datetime.now(UTC)
            purchase.status = PURCHASE_PAID
            db.flush()
    except IntegrityError:
        db.refresh(payment)
        db.refresh(purchase)
        return "conflicts with an existing successful payment"
    return None


def _fulfil_safely(db: Session, fulfil: Fulfiller, payment_id: int) -> FulfilmentOutcome:
    """The payment is already committed as successful, so nothing here may
    escape: a router or database problem must not make it look unpaid."""
    try:
        return fulfil(db, payment_id).outcome
    except Exception:
        logger.exception("fulfilment raised past its guard: payment_id=%s", payment_id)
        return FulfilmentOutcome.UNEXPECTED_ERROR
    