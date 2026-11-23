"""Process one stored M-Pesa callback end to end (WEZA-50).

The route has already passed the security gates and saved the raw message as
a 'received' audit event. This module then runs:

  Phase 1 (no row lock): parse, find our payment, verify, ask Safaricom's
  status query. The query is a network call, so it must never run while a
  row lock is held.
  Phase 2: settle_payment() locks the row briefly and applies the result.

Fail closed: anything unparseable, unmatched, unverifiable or unconfirmed
leaves the payment pending and grants nothing. Every path ends with the
audit event moved to a final outcome.
"""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.mpesa.callback_payload import (
    MalformedCallbackError,
    parse_stk_callback,
)
from app.integrations.mpesa.errors import DarajaError
from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import Payment
from app.payments.callback_verification import ExpectedPayment, verify_callback
from app.payments.settlement_plan import SettlementAction, requires_status_query
from app.payments.statuses import PaymentStatus
from app.services.payment_event_outcome import mark_event_outcome
from app.services.payment_event_service import EventOutcome
from app.services.payment_settlement import settle_payment

logger = logging.getLogger(__name__)


class StatusQuerier(Protocol):
    """The one thing we need from the Daraja client. Tests supply a fake."""

    def stk_query(self, checkout_request_id: str) -> StkQueryResult: ...


@dataclass(frozen=True)
class CallbackProcessing:
    """What happened, for logging and the route's reply."""

    outcome: EventOutcome
    payment_id: int | None
    action: SettlementAction | None


def process_callback(
    db: Session,
    daraja: StatusQuerier | None,
    *,
    event_id: int,
    payload: object,
    raw_payload: dict[str, Any],
) -> CallbackProcessing:
    """Handle one callback. `payload` is the parsed JSON (any shape: it is
    untrusted); `raw_payload` is the JSONB-safe copy stored for audit.
    """
    try:
        callback = parse_stk_callback(payload)
    except MalformedCallbackError:
        _close_event(db, event_id, EventOutcome.REJECTED, None, "malformed callback payload")
        return CallbackProcessing(EventOutcome.REJECTED, None, None)

    payment = db.execute(
        select(Payment).where(Payment.checkout_request_id == callback.checkout_request_id)
    ).scalar_one_or_none()
    if payment is None:
        _close_event(db, event_id, EventOutcome.UNMATCHED, None, "no payment with this checkout id")
        return CallbackProcessing(EventOutcome.UNMATCHED, None, None)

    # Copy what we need now: the rollback below expires the ORM object.
    payment_id = payment.id
    stored_status = payment.status
    try:
        if not payment.merchant_request_id:
            raise ValueError("stored payment has no merchant request id")
        expected = ExpectedPayment(
            checkout_request_id=payment.checkout_request_id,
            merchant_request_id=payment.merchant_request_id,
            amount=payment.amount,
            phone_number=payment.phone_number,
        )
    except ValueError:
        # Our own data is incomplete (e.g. NULL merchant id). We cannot verify,
        # so we do not apply; the status query path can resolve it later.
        _close_event(db, event_id, EventOutcome.REJECTED, payment_id, "stored payment cannot be verified")
        return CallbackProcessing(EventOutcome.REJECTED, payment_id, None)

    verdict = verify_callback(callback, expected)

    query_outcome: StkQueryOutcome | None = None
    # An unknown status string raises ValueError here: nothing is applied.
    if requires_status_query(verdict, PaymentStatus(stored_status)):
        db.rollback()  # end the read transaction BEFORE the network call
        query_outcome = _ask_status(daraja, callback.checkout_request_id, payment_id)

    result = settle_payment(
        db,
        event_id=event_id,
        payment_id=payment_id,
        verdict=verdict,
        query_outcome=query_outcome,
        callback=callback,
        raw_payload=raw_payload,
    )
    logger.info(
        "callback processed: payment_id=%s checkout_request_id=%s verdict=%s action=%s",
        payment_id, callback.checkout_request_id, verdict.value, result.action.value,
    )
    return CallbackProcessing(_outcome_for(result.action), payment_id, result.action)


def _ask_status(
    daraja: StatusQuerier | None, checkout_request_id: str, payment_id: int
) -> StkQueryOutcome | None:
    """One status query. Any failure to get an answer returns None, which the
    settlement table treats as 'not confirmed': the payment stays pending."""
    if daraja is None:
        logger.error("status query skipped, Daraja not configured: payment_id=%s", payment_id)
        return None
    try:
        return daraja.stk_query(checkout_request_id).outcome
    except (DarajaError, ValueError) as error:
        # Type only: messages could carry request details.
        logger.warning(
            "status query gave no answer: payment_id=%s error=%s",
            payment_id, type(error).__name__,
        )
        return None


def _outcome_for(action: SettlementAction) -> EventOutcome:
    if action in (SettlementAction.APPLY_SUCCESS, SettlementAction.APPLY_FAILURE):
        return EventOutcome.APPLIED
    if action is SettlementAction.ALREADY_SETTLED:
        return EventOutcome.DUPLICATE
    return EventOutcome.REJECTED


def _close_event(
    db: Session, event_id: int, outcome: EventOutcome, payment_id: int | None, note: str
) -> None:
    """Finish the audit event for paths that never reach settle_payment."""
    try:
        mark_event_outcome(db, event_id=event_id, outcome=outcome, payment_id=payment_id, note=note)
        db.commit()
    except Exception:
        db.rollback()
        raise