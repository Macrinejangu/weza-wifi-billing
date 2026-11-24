"""Database tests for fulfil_payment (WEZA-51).

A real (rolled-back) database holds the purchase, payment and session rows.
The router is a fake callable, so the network is never touched. These tests
prove the rows end up in the right state for each router answer, and that
payment status and activation status stay separate: a router problem must
never change a payment that M-Pesa confirmed.
"""

import pytest

from app.models import ActivationAttempt, Payment, WiFiSession
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment
from app.services.router import RouterActivationUnconfirmed

from test_payment_settlement import make_payment, make_purchase


class FakeRouter:
    """Callable with the router contract used by activate_session:
    router(session_id) -> {"status": ...}. Records every call."""

    def __init__(self, result=None, error=None):
        self.result = {"status": "ACTIVE"} if result is None else result
        self.error = error
        self.calls = []

    def __call__(self, session_id):
        self.calls.append(session_id)
        if self.error is not None:
            raise self.error
        return self.result


def make_paid(db, user, package, *, successful=True):
    purchase = make_purchase(db, user, package, status="paid" if successful else "pending")
    return make_payment(
        db,
        purchase,
        status="successful" if successful else "pending",
        receipt="QGH1234ABC" if successful else None,
    )


def session_count(db):
    return db.query(WiFiSession).count()


def test_router_confirms_activation(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter()

    result = fulfil_payment(db, payment.id, router=router)

    session = db.get(WiFiSession, result.session_id)
    assert result.outcome is FulfilmentOutcome.ACTIVATED
    assert (session.status, session.activation_status) == ("ACTIVE", "succeeded")
    # The clock starts only now, when the router confirmed.
    assert session.started_at is not None and session.expires_at is not None
    assert db.get(Payment, payment.id).status == "successful"
    assert router.calls == [session.id]


def test_router_failure_is_recorded_and_payment_stays_successful(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter(result={"status": "ERROR"})

    result = fulfil_payment(db, payment.id, router=router)

    session = db.get(WiFiSession, result.session_id)
    assert result.outcome is FulfilmentOutcome.ACTIVATION_FAILED
    assert (session.status, session.activation_status) == ("FAILED", "failed")
    assert session.failure_reason
    assert session.started_at is None  # no time is given for failed access
    assert db.get(Payment, payment.id).status == "successful"


def test_unconfirmed_router_answer_leaves_activation_waiting(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter(error=RouterActivationUnconfirmed("timed out"))

    result = fulfil_payment(db, payment.id, router=router)

    session = db.get(WiFiSession, result.session_id)
    attempt = db.query(ActivationAttempt).filter_by(session_id=session.id).one()
    assert result.outcome is FulfilmentOutcome.ACTIVATION_UNCONFIRMED
    assert (session.status, session.activation_status) == ("ACTIVATING", "waiting")
    assert session.started_at is None
    # The ONLY marker of "unconfirmed" is this error code on the attempt.
    assert attempt.error_code == "RouterActivationUnconfirmed"
    assert db.get(Payment, payment.id).status == "successful"


def test_fulfilling_twice_makes_one_session_and_one_router_call(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter()

    first = fulfil_payment(db, payment.id, router=router)
    second = fulfil_payment(db, payment.id, router=router)

    assert first.outcome is FulfilmentOutcome.ACTIVATED
    assert second.outcome is FulfilmentOutcome.ACTIVATED
    assert second.session_id == first.session_id
    assert session_count(db) == 1
    assert len(router.calls) == 1


@pytest.mark.parametrize("successful", [False])
def test_unconfirmed_payment_gets_no_session_and_no_router_call(
    db, user, package, successful
):
    payment = make_paid(db, user, package, successful=successful)
    router = FakeRouter()

    result = fulfil_payment(db, payment.id, router=router)

    assert result.outcome is FulfilmentOutcome.NOT_ATTEMPTED
    assert result.session_id is None
    assert session_count(db) == 0
    assert router.calls == []
    