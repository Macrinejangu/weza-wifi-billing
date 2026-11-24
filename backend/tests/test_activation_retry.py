"""Tests for the safe staff retry (WEZA-63)."""

import httpx
import pytest

from app.integrations.mpesa.client import DarajaClient
from app.models import ActivationAttempt, AdminAuditLog, WiFiSession
from app.services.activation_recovery import RecoveryReason
from app.services.activation_retry import AUDIT_ACTION, RetryRefused, retry_activation
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment
from app.services.router import RouterActivationUnconfirmed

from test_payment_fulfilment_db import FakeRouter, make_paid


def audit_rows(db, payment):
    db.expire_all()
    return (
        db.query(AdminAuditLog)
        .filter_by(entity_type="payment", entity_id=payment.id)
        .all()
    )


def test_payment_without_a_session_is_retried_and_activated(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter()

    result = retry_activation(db, payment.id, staff_id=user.id, router=router)

    session = db.get(WiFiSession, result.session_id)
    assert result.outcome is FulfilmentOutcome.ACTIVATED
    assert result.reason_before is RecoveryReason.PAID_NO_SESSION
    assert (session.status, session.activation_status) == ("ACTIVE", "succeeded")
    assert router.calls == [session.id]


def test_failed_session_retry_starts_a_new_attempt_and_the_clock_at_confirmation(
    db, user, package
):
    payment = make_paid(db, user, package)
    fulfil_payment(db, payment.id, router=FakeRouter(result={"status": "ERROR"}))
    router = FakeRouter()

    result = retry_activation(db, payment.id, staff_id=user.id, router=router)

    session = db.get(WiFiSession, result.session_id)
    assert result.reason_before is RecoveryReason.FAILED
    assert result.outcome is FulfilmentOutcome.ACTIVATED
    assert db.query(ActivationAttempt).filter_by(session_id=session.id).count() == 2
    # Time starts when the router confirmed, never earlier than the payment.
    assert session.subscription.status == "active"
    assert session.subscription.start_date == session.started_at
    assert session.started_at >= payment.paid_at


def test_unconfirmed_retry_reconciles_and_never_calls_the_router_again(
    db, user, package
):
    payment = make_paid(db, user, package)
    first_router = FakeRouter(error=RouterActivationUnconfirmed("timed out"))
    fulfil_payment(db, payment.id, router=first_router)
    second_router = FakeRouter()

    result = retry_activation(db, payment.id, staff_id=user.id, router=second_router)

    session = db.get(WiFiSession, result.session_id)
    assert result.reason_before is RecoveryReason.UNCONFIRMED
    assert second_router.calls == []  # reconcile is verify-only, not a new router call
    assert db.query(ActivationAttempt).filter_by(session_id=session.id).count() == 1
    assert session.started_at is None  # no time given until the router confirms


def test_retry_is_audited_before_and_completed_after(db, user, package):
    payment = make_paid(db, user, package)

    result = retry_activation(db, payment.id, staff_id=user.id, router=FakeRouter())

    rows = audit_rows(db, payment)
    assert [row.id for row in rows] == [result.audit_id]
    row = rows[0]
    assert row.action == AUDIT_ACTION
    assert row.admin_id == user.id
    assert row.old_values["reason"] == "paid_no_session"
    assert row.new_values == {"outcome": "activated", "session_id": result.session_id}


def test_a_failed_retry_is_audited_with_its_outcome(db, user, package):
    payment = make_paid(db, user, package)

    result = retry_activation(
        db, payment.id, staff_id=user.id, router=FakeRouter(result={"status": "ERROR"})
    )

    assert result.outcome is FulfilmentOutcome.ACTIVATION_FAILED
    assert audit_rows(db, payment)[0].new_values["outcome"] == "activation_failed"


def test_retrying_twice_makes_one_router_call(db, user, package):
    payment = make_paid(db, user, package)
    router = FakeRouter()
    retry_activation(db, payment.id, staff_id=user.id, router=router)

    with pytest.raises(RetryRefused) as refused:
        retry_activation(db, payment.id, staff_id=user.id, router=router)

    assert refused.value.code == "nothing_to_retry"
    assert len(router.calls) == 1
    assert len(audit_rows(db, payment)) == 1  # a refused retry leaves no audit row


@pytest.mark.parametrize("successful", [False])
def test_unconfirmed_payment_is_refused(db, user, package, successful):
    payment = make_paid(db, user, package, successful=successful)
    router = FakeRouter()

    with pytest.raises(RetryRefused) as refused:
        retry_activation(db, payment.id, staff_id=user.id, router=router)

    assert refused.value.code == "payment_not_confirmed"
    assert router.calls == []
    assert audit_rows(db, payment) == []


def test_missing_payment_raises_lookup_error(db, user):
    with pytest.raises(LookupError):
        retry_activation(db, 999_999_999, staff_id=user.id)


def test_missing_device_in_live_mode_is_refused_without_calling_the_router(
    db, user, package
):
    payment = make_paid(db, user, package)  # purchase has no verified device
    router = FakeRouter()

    with pytest.raises(RetryRefused) as refused:
        retry_activation(
            db, payment.id, staff_id=user.id, router=router, require_device=True
        )

    assert refused.value.code == "needs_staff_review"
    assert router.calls == []
    assert audit_rows(db, payment) == []


def test_inconsistent_session_is_refused(db, user, package):
    payment = make_paid(db, user, package)
    db.add(WiFiSession(
        user_id=user.id, package_id=package.id, payment_id=payment.id,
        status="ACTIVATING", activation_status="waiting",
    ))
    db.commit()
    router = FakeRouter()

    with pytest.raises(RetryRefused) as refused:
        retry_activation(db, payment.id, staff_id=user.id, router=router)

    assert refused.value.code == "needs_staff_review"
    assert router.calls == []


def test_retry_never_contacts_daraja(db, user, package, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A retry must never contact Daraja")

    monkeypatch.setattr(DarajaClient, "stk_push", forbidden)
    monkeypatch.setattr(DarajaClient, "stk_query", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    payment = make_paid(db, user, package)

    result = retry_activation(db, payment.id, staff_id=user.id, router=FakeRouter())

    assert result.outcome is FulfilmentOutcome.ACTIVATED
    