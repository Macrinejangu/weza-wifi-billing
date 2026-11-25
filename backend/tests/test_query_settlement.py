"""Tests for settle_from_query (WEZA-63). No network: fulfilment is a fake."""

import pytest
from sqlalchemy import func, select

from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import Payment, PaymentEvent, Purchase
from app.payments.result_codes import failure_reason_for
from app.payments.settlement_plan import SettlementAction
from app.services.payment_fulfilment import FulfilmentOutcome, FulfilmentResult
from app.services.query_settlement import QUERY_ORIGIN, settle_from_query

from test_payment_settlement import make_payment, make_purchase

PAID = StkQueryResult(StkQueryOutcome.PAID, result_code=0, result_desc="ok")
UNKNOWN = StkQueryResult(StkQueryOutcome.UNKNOWN)
FAILED = StkQueryResult(
    StkQueryOutcome.FAILED,
    result_code=1032,
    failure_reason=failure_reason_for(1032),
    result_desc="cancelled",
)


class FakeFulfil:
    """Records every call. Optionally raises."""

    def __init__(self, error=None):
        self.error, self.calls = error, []

    def __call__(self, db, payment_id):
        self.calls.append(payment_id)
        if self.error is not None:
            raise self.error
        return FulfilmentResult(payment_id, 1, FulfilmentOutcome.ACTIVATED)


@pytest.fixture
def pending(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    db.commit()
    return payment.id, purchase.id


def reload(db, model, row_id):
    db.expire_all()
    return db.get(model, row_id)


def events(db, payment_id):
    db.expire_all()
    return db.scalars(
        select(PaymentEvent).where(PaymentEvent.payment_id == payment_id)
    ).all()


def test_paid_query_settles_and_starts_fulfilment(db, pending):
    payment_id, purchase_id = pending
    fulfil = FakeFulfil()

    result = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)

    payment = reload(db, Payment, payment_id)
    assert result.action is SettlementAction.APPLY_SUCCESS
    assert result.fulfilment is FulfilmentOutcome.ACTIVATED
    assert payment.status == "successful"
    assert payment.paid_at is not None
    assert payment.result_code == 0
    # The query reply has no receipt, and we must never invent one.
    assert payment.mpesa_receipt_number is None
    assert payment.callback_received_at is None
    assert reload(db, Purchase, purchase_id).status == "paid"
    assert fulfil.calls == [payment_id]

    [event] = events(db, payment_id)
    assert event.source == "query"
    assert event.processing_status == "applied"
    assert event.payload["origin"] == QUERY_ORIGIN


def test_repeat_paid_query_is_a_duplicate_and_fulfils_once(db, pending):
    payment_id, _ = pending
    fulfil = FakeFulfil()

    first = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)
    second = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)

    assert first.action is SettlementAction.APPLY_SUCCESS
    assert second.action is SettlementAction.ALREADY_SETTLED
    assert second.fulfilment is None
    assert fulfil.calls == [payment_id]  # not twice
    assert sorted(e.processing_status for e in events(db, payment_id)) == [
        "applied", "duplicate",
    ]


def test_unknown_query_changes_nothing_and_writes_no_event(db, pending):
    payment_id, purchase_id = pending
    fulfil = FakeFulfil()

    result = settle_from_query(db, payment_id=payment_id, query_result=UNKNOWN, fulfil=fulfil)

    assert result.action is SettlementAction.KEEP_PENDING
    assert reload(db, Payment, payment_id).status == "pending"
    assert reload(db, Purchase, purchase_id).status == "pending"
    assert fulfil.calls == []
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_failed_query_alone_never_settles(db, pending):
    payment_id, purchase_id = pending
    fulfil = FakeFulfil()

    result = settle_from_query(db, payment_id=payment_id, query_result=FAILED, fulfil=fulfil)

    assert result.action is SettlementAction.KEEP_PENDING
    assert reload(db, Payment, payment_id).status == "pending"
    assert reload(db, Purchase, purchase_id).status == "pending"
    assert fulfil.calls == []
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_unknown_payment_raises(db):
    with pytest.raises(LookupError):
        settle_from_query(db, payment_id=999_999_999, query_result=PAID, fulfil=FakeFulfil())


def test_failed_payment_is_never_flipped_to_paid(db, pending):
    payment_id, _ = pending
    payment = reload(db, Payment, payment_id)
    payment.status = "failed"
    db.commit()
    fulfil = FakeFulfil()

    result = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)

    assert result.action is SettlementAction.REJECT
    assert reload(db, Payment, payment_id).status == "failed"
    assert fulfil.calls == []
    [event] = events(db, payment_id)
    assert event.processing_status == "rejected"


def test_purchase_already_paid_is_rejected_for_staff_review(db, pending):
    payment_id, purchase_id = pending
    reload(db, Purchase, purchase_id).status = "paid"
    db.commit()
    fulfil = FakeFulfil()

    result = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)

    assert result.action is SettlementAction.REJECT
    assert reload(db, Payment, payment_id).status == "pending"
    assert fulfil.calls == []
    [event] = events(db, payment_id)
    assert event.processing_status == "rejected"
    assert "staff review" in event.error_message


def test_fulfilment_crash_does_not_undo_the_payment(db, pending):
    payment_id, _ = pending
    fulfil = FakeFulfil(error=RuntimeError("router exploded"))

    result = settle_from_query(db, payment_id=payment_id, query_result=PAID, fulfil=fulfil)

    assert result.action is SettlementAction.APPLY_SUCCESS
    assert result.fulfilment is FulfilmentOutcome.UNEXPECTED_ERROR
    assert reload(db, Payment, payment_id).status == "successful"
    