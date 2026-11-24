"""Tests that process_callback starts fulfilment only when it should (WEZA-51).

fulfil is a fake that records calls. The point here is WHEN fulfilment
starts, not what it does (see test_payment_fulfilment*.py). Rule: only a
freshly applied success starts it. Duplicates, failures, unmatched or
unverified callbacks never do, and a crashing fulfilment must not change
the callback result or the payment.
"""

import pytest

from app.models import Payment
from app.services.callback_processing import process_callback
from app.services.payment_event_service import EventOutcome
from app.services.payment_fulfilment import FulfilmentOutcome, FulfilmentResult

from test_callback_processing import FAILED, PAID, FakeDaraja, body
from test_payment_settlement import CHECKOUT, make_payment, make_purchase, new_event


class FakeFulfil:
    def __init__(self, outcome=FulfilmentOutcome.ACTIVATED, error=None):
        self.outcome, self.error, self.calls = outcome, error, []

    def __call__(self, db, payment_id):
        self.calls.append(payment_id)
        if self.error is not None:
            raise self.error
        return FulfilmentResult(
            payment_id=payment_id, session_id=None, outcome=self.outcome
        )


@pytest.fixture
def payment(db, user, package):
    return make_payment(db, make_purchase(db, user, package))


def run(db, daraja, payload, fulfil):
    return process_callback(
        db, daraja,
        event_id=new_event(db), payload=payload, raw_payload={"test": True},
        fulfil=fulfil,
    )


def test_fresh_success_starts_fulfilment_once_for_that_payment(db, payment):
    pid = payment.id
    fulfil = FakeFulfil(outcome=FulfilmentOutcome.ACTIVATION_FAILED)

    result = run(db, FakeDaraja(PAID), body(), fulfil)

    assert result.outcome is EventOutcome.APPLIED
    assert fulfil.calls == [pid]
    assert result.fulfilment is FulfilmentOutcome.ACTIVATION_FAILED


def test_duplicate_callback_does_not_start_fulfilment_again(db, payment):
    pid = payment.id
    fulfil = FakeFulfil()

    first = run(db, FakeDaraja(PAID), body(), fulfil)
    second = run(db, FakeDaraja(PAID), body(), fulfil)

    assert first.outcome is EventOutcome.APPLIED
    assert second.outcome is EventOutcome.DUPLICATE
    assert second.fulfilment is None
    assert fulfil.calls == [pid]


def test_failed_payment_callback_never_starts_fulfilment(db, payment):
    fulfil = FakeFulfil()

    result = run(db, FakeDaraja(FAILED), body(code=1032), fulfil)

    assert fulfil.calls == []
    assert result.fulfilment is None


def test_unmatched_callback_never_starts_fulfilment(db, payment):
    fulfil = FakeFulfil()

    result = run(db, FakeDaraja(PAID), body("ws_CO_unknown"), fulfil)

    assert result.outcome is EventOutcome.UNMATCHED
    assert fulfil.calls == []


def test_amount_mismatch_never_starts_fulfilment_and_stays_pending(db, payment):
    pid = payment.id
    fulfil = FakeFulfil()

    result = run(db, FakeDaraja(PAID), body(amount=1), fulfil)

    assert result.outcome is EventOutcome.REJECTED
    assert fulfil.calls == []
    db.expire_all()
    assert db.get(Payment, pid).status == "pending"


def test_crashing_fulfilment_changes_neither_reply_nor_payment(db, payment):
    pid = payment.id
    fulfil = FakeFulfil(error=RuntimeError("db connection died"))

    result = run(db, FakeDaraja(PAID), body(), fulfil)

    assert result.outcome is EventOutcome.APPLIED
    assert result.fulfilment is FulfilmentOutcome.UNEXPECTED_ERROR
    db.expire_all()
    assert db.get(Payment, pid).status == "successful"
    