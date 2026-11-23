"""Tests for process_callback (WEZA-50). Daraja is a fake: no network."""

import pytest

from app.payments.result_codes import failure_reason_for
from app.integrations.mpesa.errors import DarajaTimeoutError, DarajaUnavailableError
from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import PaymentEvent
from app.services.callback_processing import process_callback
from app.services.payment_event_service import EventOutcome

from test_payment_settlement import (  # shared data helpers
    AMOUNT, CHECKOUT, PHONE, make_payment, make_purchase, new_event,
)

PAID = StkQueryResult(StkQueryOutcome.PAID, result_code=0, result_desc="ok")
FAILED = StkQueryResult(
    StkQueryOutcome.FAILED,
    result_code=1032,
    failure_reason=failure_reason_for(1032),
    result_desc="cancelled",
)
UNKNOWN = StkQueryResult(StkQueryOutcome.UNKNOWN)


class FakeDaraja:
    """Records every query. Returns a result or raises an error."""

    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def stk_query(self, checkout_request_id, timestamp=None):
        self.calls.append(checkout_request_id)
        if self.error is not None:
            raise self.error
        return self.result


def body(checkout=CHECKOUT, *, code=0, amount=AMOUNT, phone=PHONE, receipt="QGH1234ABC"):
    callback = {
        "MerchantRequestID": f"mr-{checkout}",
        "CheckoutRequestID": checkout,
        "ResultCode": code,
        "ResultDesc": "result text",
    }
    if code == 0:
        callback["CallbackMetadata"] = {"Item": [
            {"Name": "Amount", "Value": amount},
            {"Name": "MpesaReceiptNumber", "Value": receipt},
            {"Name": "TransactionDate", "Value": 20261123101500},
            {"Name": "PhoneNumber", "Value": int(phone)},
        ]}
    return {"Body": {"stkCallback": callback}}


def process(db, daraja, payload, event_id):
    return process_callback(
        db, daraja, event_id=event_id, payload=payload, raw_payload={"test": True}
    )


def event(db, event_id):
    db.expire_all()
    return db.get(PaymentEvent, event_id)


@pytest.fixture
def pending(db, user, package):
    purchase = make_purchase(db, user, package)
    return purchase, make_payment(db, purchase)


def test_confirmed_success_settles_payment_after_one_query(db, pending):
    purchase, payment = pending
    daraja = FakeDaraja(PAID)
    event_id = new_event(db)

    result = process(db, daraja, body(), event_id)

    assert result.outcome is EventOutcome.APPLIED
    assert daraja.calls == [CHECKOUT]
    assert payment.status == "successful"
    assert purchase.status == "paid"
    assert event(db, event_id).processing_status == "applied"


@pytest.mark.parametrize(
    "daraja",
    [
        FakeDaraja(UNKNOWN),
        FakeDaraja(FAILED),
        FakeDaraja(error=DarajaTimeoutError("timeout")),
        FakeDaraja(error=DarajaUnavailableError("down")),
        FakeDaraja(error=ValueError("bad id")),
        None,
    ],
    ids=["unknown", "contradicts", "timeout", "down", "value-error", "not-configured"],
)
def test_success_without_confirmation_leaves_payment_pending(db, pending, daraja):
    purchase, payment = pending
    event_id = new_event(db)

    result = process(db, daraja, body(), event_id)

    assert result.outcome is EventOutcome.REJECTED
    assert payment.status == "pending"
    assert payment.mpesa_receipt_number is None
    assert purchase.status == "pending"
    assert event(db, event_id).processing_status == "rejected"


def test_unexpected_error_in_the_query_is_not_swallowed(db, pending):
    # Only Daraja errors mean "no answer". Our own bugs must surface.
    daraja = FakeDaraja(error=AttributeError("bug"))
    with pytest.raises(AttributeError):
        process(db, daraja, body(), new_event(db))


def test_confirmed_failure_marks_payment_failed(db, pending):
    purchase, payment = pending
    daraja = FakeDaraja(FAILED)

    result = process(db, daraja, body(code=1032), new_event(db))

    assert result.outcome is EventOutcome.APPLIED
    assert payment.status == "failed"
    assert purchase.status == "pending"


def test_forged_failure_is_ignored_when_the_query_says_paid(db, pending):
    _, payment = pending

    result = process(db, FakeDaraja(PAID), body(code=1032), new_event(db))

    assert result.outcome is EventOutcome.REJECTED
    assert payment.status == "pending"


@pytest.mark.parametrize("garbage", [None, [], "text", 5, {}, {"Body": {}}, {"Body": {"stkCallback": []}}])
def test_malformed_payload_is_rejected_and_never_queried(db, pending, garbage):
    _, payment = pending
    daraja = FakeDaraja(PAID)
    event_id = new_event(db)

    result = process(db, daraja, garbage, event_id)

    assert result.outcome is EventOutcome.REJECTED
    assert daraja.calls == []
    assert payment.status == "pending"
    assert event(db, event_id).processing_status == "rejected"


def test_unknown_checkout_id_is_unmatched_and_never_queried(db, pending):
    daraja = FakeDaraja(PAID)
    event_id = new_event(db)

    result = process(db, daraja, body(checkout="ws_CO_nobody"), event_id)

    assert result.outcome is EventOutcome.UNMATCHED
    assert result.payment_id is None
    assert daraja.calls == []
    assert event(db, event_id).processing_status == "unmatched"


@pytest.mark.parametrize("override", [{"amount": AMOUNT + 1}, {"phone": "254799999999"}])
def test_amount_or_phone_mismatch_is_rejected_without_a_query(db, pending, override):
    _, payment = pending
    daraja = FakeDaraja(PAID)  # even a PAID answer must not rescue it

    result = process(db, daraja, body(**override), new_event(db))

    assert result.outcome is EventOutcome.REJECTED
    assert daraja.calls == []
    assert payment.status == "pending"


def test_payment_without_merchant_request_id_cannot_be_verified(db, pending):
    _, payment = pending
    payment.merchant_request_id = None
    db.commit()
    daraja = FakeDaraja(PAID)
    event_id = new_event(db)

    result = process(db, daraja, body(), event_id)

    assert result.outcome is EventOutcome.REJECTED
    assert daraja.calls == []
    assert payment.status == "pending"
    assert "cannot be verified" in event(db, event_id).error_message


def test_duplicate_callback_is_a_no_op_and_costs_no_second_query(db, pending):
    _, payment = pending
    daraja = FakeDaraja(PAID)
    process(db, daraja, body(), new_event(db))
    paid_at = payment.paid_at
    second = new_event(db)

    result = process(db, daraja, body(), second)

    assert result.outcome is EventOutcome.DUPLICATE
    assert daraja.calls == [CHECKOUT]  # only the first delivery queried
    assert payment.paid_at == paid_at
    assert event(db, second).processing_status == "duplicate"