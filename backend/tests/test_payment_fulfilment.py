"""Unit tests for fulfil_payment that need no database or router.

create_session and activate_session belong to WEZA-54 and are replaced with
fakes here, so these tests prove only OUR logic: outcome classification,
error containment, and always ending the transaction. Database-backed tests
live in test_payment_fulfilment_db.py, and the real race is in
test_fulfilment_concurrency.py.
"""
from types import SimpleNamespace

import pytest

from app.services import payment_fulfilment
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment

PAYMENT_ID = 42
SESSION_ID = 7


class FakeDb:
    """Counts rollbacks and records expired objects.

    fulfil_payment must always end its transaction, and must expire the
    session object before activation reads it.
    """

    def __init__(self) -> None:
        self.rollbacks = 0
        self.expired: list = []

    def rollback(self) -> None:
        self.rollbacks += 1

    def expire(self, instance) -> None:
        self.expired.append(instance)


def make_session(status: str, activation_status: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=SESSION_ID, status=status, activation_status=activation_status
    )


def patch_services(monkeypatch, create, activate) -> None:
    monkeypatch.setattr(
        payment_fulfilment, "create_session", lambda db, payment_id, *, verified_checkout: create(db, payment_id)
    )
    monkeypatch.setattr(payment_fulfilment, "activate_session", activate)


@pytest.mark.parametrize(
    ("status", "activation_status", "expected"),
    [
        ("ACTIVE", "succeeded", FulfilmentOutcome.ACTIVATED),
        ("FAILED", "failed", FulfilmentOutcome.ACTIVATION_FAILED),
        # Router gave no clear answer: still ACTIVATING, activation "waiting".
        ("ACTIVATING", "waiting", FulfilmentOutcome.ACTIVATION_UNCONFIRMED),
        # A state activate_session should never return: fail closed.
        ("PAYMENT_CONFIRMED", "waiting", FulfilmentOutcome.UNEXPECTED_ERROR),
    ],
)
def test_outcome_is_read_from_the_returned_session(
    monkeypatch, status, activation_status, expected
):
    db = FakeDb()
    patch_services(
        monkeypatch,
        create=lambda db, payment_id: make_session("PAYMENT_CONFIRMED", "not_started"),
        activate=lambda db, session_id, router=None: make_session(
            status, activation_status
        ),
    )

    result = fulfil_payment(db, PAYMENT_ID)

    assert result.outcome is expected
    assert result.payment_id == PAYMENT_ID
    assert result.session_id == SESSION_ID
    assert db.rollbacks == 1


@pytest.mark.parametrize("error", [LookupError("gone"), ValueError("not confirmed")])
def test_precondition_errors_mean_not_attempted_and_skip_the_router(
    monkeypatch, error
):
    db = FakeDb()
    activate_calls = []

    def create(db, payment_id):
        raise error

    def activate(db, session_id, router=None):
        activate_calls.append(session_id)

    patch_services(monkeypatch, create, activate)

    result = fulfil_payment(db, PAYMENT_ID)

    assert result.outcome is FulfilmentOutcome.NOT_ATTEMPTED
    assert result.session_id is None
    # No session means no activation attempt: the router is never reached.
    assert activate_calls == []
    assert db.rollbacks == 1


def test_unexpected_error_is_contained_and_keeps_the_session_id(monkeypatch):
    db = FakeDb()

    def activate(db, session_id, router=None):
        raise RuntimeError("boom")

    patch_services(
        monkeypatch,
        create=lambda db, payment_id: make_session("PAYMENT_CONFIRMED", "not_started"),
        activate=activate,
    )

    # Must return a value, never raise: the callback reply cannot change.
    result = fulfil_payment(db, PAYMENT_ID)

    assert result.outcome is FulfilmentOutcome.UNEXPECTED_ERROR
    assert result.session_id == SESSION_ID
    assert db.rollbacks == 1


def test_router_callable_reaches_activate_session(monkeypatch):
    db = FakeDb()
    seen = {}

    def activate(db, session_id, router=None):
        seen["router"] = router
        seen["session_id"] = session_id
        return make_session("ACTIVE", "succeeded")

    patch_services(
        monkeypatch,
        create=lambda db, payment_id: make_session("PAYMENT_CONFIRMED", "not_started"),
        activate=activate,
    )

    def fake_router(session_id: int) -> dict:
        return {"status": "ACTIVE"}

    fulfil_payment(db, PAYMENT_ID, router=fake_router)

    assert seen["router"] is fake_router
    assert seen["session_id"] == SESSION_ID


def test_session_is_expired_before_activation_reads_it(monkeypatch):
    """A stale cached session would hide the winner's result in a race."""
    db = FakeDb()
    created = make_session("PAYMENT_CONFIRMED", "not_started")
    seen = {}

    def activate(db_arg, session_id, router=None):
        # Snapshot what had been expired at the moment activation started.
        seen["expired_before_activation"] = list(db.expired)
        return make_session("ACTIVE", "succeeded")

    patch_services(monkeypatch, create=lambda db, payment_id: created, activate=activate)

    fulfil_payment(db, PAYMENT_ID)

    assert seen["expired_before_activation"] == [created]


def test_failures_are_logged_with_the_payment_id_but_no_traceback_to_callers(
    monkeypatch, caplog
):
    db = FakeDb()

    def create(db, payment_id):
        raise ValueError("Payment has not been confirmed")

    patch_services(monkeypatch, create, lambda *a, **k: None)

    with caplog.at_level("ERROR"):
        fulfil_payment(db, PAYMENT_ID)

    assert f"payment_id={PAYMENT_ID}" in caplog.text
    