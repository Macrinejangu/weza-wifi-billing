"""Tests for the unresolved-case finder (WEZA-63).

The pure rule (classify_case) is tested exhaustively; the database tests prove
the query finds the right rows and leaves healthy ones out.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import ActivationAttempt, WiFiSession
from app.services.activation_recovery import (
    RecoveryAction,
    RecoveryReason,
    classify_case,
    find_unresolved_cases,
    get_case,
)

from test_payment_settlement import make_payment, make_purchase

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
LONG_AGO = NOW - timedelta(hours=1)
JUST_NOW = NOW - timedelta(seconds=30)


def classify(**overrides):
    values = dict(
        payment_status="successful", paid_at=LONG_AGO, initiated_at=LONG_AGO,
        session_status=None, activation_status=None, session_started_at=None,
        latest_error_code=None, has_device=True, require_device=False, now=NOW,
    )
    values.update(overrides)
    return classify_case(**values)


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({}, RecoveryReason.PAID_NO_SESSION),
        ({"paid_at": JUST_NOW}, None),
        ({"paid_at": None}, RecoveryReason.INCONSISTENT_STATE),
        ({"require_device": True, "has_device": False}, RecoveryReason.NEEDS_DEVICE),
        ({"require_device": False, "has_device": False}, RecoveryReason.PAID_NO_SESSION),
        ({"session_status": "ACTIVE", "activation_status": "succeeded"}, None),
        ({"session_status": "EXPIRED", "activation_status": "succeeded",
          "session_started_at": LONG_AGO}, None),
        ({"session_status": "EXPIRED", "activation_status": "succeeded"},
         RecoveryReason.INCONSISTENT_STATE),
        ({"session_status": "PAYMENT_CONFIRMED", "activation_status": "not_started"},
         RecoveryReason.NOT_STARTED),
        ({"session_status": "PAYMENT_CONFIRMED", "activation_status": "not_started",
          "paid_at": JUST_NOW}, None),
        ({"session_status": "FAILED", "activation_status": "failed"}, RecoveryReason.FAILED),
        ({"session_status": "FAILED", "activation_status": "failed",
          "require_device": True, "has_device": False}, RecoveryReason.NEEDS_DEVICE),
        ({"session_status": "ACTIVATING", "activation_status": "waiting",
          "latest_error_code": "RouterActivationUnconfirmed"}, RecoveryReason.UNCONFIRMED),
        ({"session_status": "ACTIVATING", "activation_status": "waiting"},
         RecoveryReason.INCONSISTENT_STATE),
        ({"session_status": "ACTIVE", "activation_status": "waiting"},
         RecoveryReason.INCONSISTENT_STATE),
        ({"payment_status": "failed"}, None),
        ({"payment_status": "expired"}, None),
        ({"payment_status": "pending", "initiated_at": LONG_AGO}, RecoveryReason.PENDING_STALE),
        ({"payment_status": "pending", "initiated_at": JUST_NOW}, None),
        ({"payment_status": "pending", "initiated_at": None}, None),
    ],
)
def test_classify_case(overrides, expected):
    assert classify(**overrides) == expected


def paid(db, user, package, key, *, age=timedelta(hours=1), device=False):
    purchase = make_purchase(db, user, package, key=key, status="paid")
    if device:
        purchase.device_mac_address = "AA:BB:CC:DD:EE:01"
        purchase.device_ip_address = "10.0.0.5"
    payment = make_payment(
        db, purchase, checkout=f"ws_CO_{key}", status="successful", receipt=f"RCPT-{key}"
    )
    payment.paid_at = NOW - age
    db.commit()
    return payment


def add_session(db, user, package, payment, status, activation_status, **fields):
    session = WiFiSession(
        user_id=user.id, package_id=package.id, payment_id=payment.id,
        status=status, activation_status=activation_status, **fields,
    )
    db.add(session)
    db.commit()
    return session


def by_payment(cases):
    return {case.payment_id: case for case in cases}


def test_paid_payment_without_a_session_is_listed(db, user, package):
    payment = paid(db, user, package, "no-session")

    case = by_payment(find_unresolved_cases(db, now=NOW))[payment.id]

    assert case.reason is RecoveryReason.PAID_NO_SESSION
    assert case.action is RecoveryAction.RETRY_ACTIVATION
    assert case.session_id is None
    assert case.age_seconds == 3600


def test_recently_paid_payment_is_left_alone(db, user, package):
    payment = paid(db, user, package, "fresh", age=timedelta(seconds=30))

    assert payment.id not in by_payment(find_unresolved_cases(db, now=NOW))


def test_healthy_sessions_are_not_listed(db, user, package):
    active = paid(db, user, package, "active")
    add_session(db, user, package, active, "ACTIVE", "succeeded",
                started_at=LONG_AGO, expires_at=NOW + timedelta(hours=1))
    expired = paid(db, user, package, "expired")
    add_session(db, user, package, expired, "EXPIRED", "succeeded",
                started_at=LONG_AGO, expires_at=NOW - timedelta(minutes=1))

    listed = by_payment(find_unresolved_cases(db, now=NOW))

    assert active.id not in listed and expired.id not in listed


def test_failed_session_is_listed_as_failed(db, user, package):
    payment = paid(db, user, package, "failed")
    session = add_session(db, user, package, payment, "FAILED", "failed",
                          failure_reason="router said no")

    case = by_payment(find_unresolved_cases(db, now=NOW))[payment.id]

    assert case.reason is RecoveryReason.FAILED
    assert case.session_id == session.id
    assert not hasattr(case, "failure_reason")  # raw router text is never exposed


def test_unconfirmed_session_is_listed_with_its_error_code(db, user, package):
    payment = paid(db, user, package, "unconfirmed")
    session = add_session(db, user, package, payment, "ACTIVATING", "waiting")
    db.add(ActivationAttempt(session_id=session.id, attempt_number=1,
                             error_code="RouterActivationUnconfirmed"))
    db.commit()

    case = by_payment(find_unresolved_cases(db, now=NOW))[payment.id]

    assert case.reason is RecoveryReason.UNCONFIRMED
    assert case.last_error_code == "RouterActivationUnconfirmed"


def test_latest_attempt_decides_the_marker(db, user, package):
    payment = paid(db, user, package, "latest")
    session = add_session(db, user, package, payment, "ACTIVATING", "waiting")
    db.add_all([
        ActivationAttempt(session_id=session.id, attempt_number=1,
                          status="failed", error_code="RuntimeError"),
        ActivationAttempt(session_id=session.id, attempt_number=2,
                          error_code="RouterActivationUnconfirmed"),
    ])
    db.commit()

    case = by_payment(find_unresolved_cases(db, now=NOW))[payment.id]

    assert case.reason is RecoveryReason.UNCONFIRMED


def test_activating_without_a_marker_is_inconsistent(db, user, package):
    payment = paid(db, user, package, "stuck")
    add_session(db, user, package, payment, "ACTIVATING", "waiting")

    case = by_payment(find_unresolved_cases(db, now=NOW))[payment.id]

    assert case.reason is RecoveryReason.INCONSISTENT_STATE
    assert case.action is RecoveryAction.STAFF_REVIEW


def test_missing_device_matters_only_when_required(db, user, package):
    payment = paid(db, user, package, "nodevice", device=False)

    relaxed = by_payment(find_unresolved_cases(db, now=NOW, require_device=False))
    strict = by_payment(find_unresolved_cases(db, now=NOW, require_device=True))

    assert relaxed[payment.id].reason is RecoveryReason.PAID_NO_SESSION
    assert strict[payment.id].reason is RecoveryReason.NEEDS_DEVICE
    assert strict[payment.id].action is RecoveryAction.STAFF_REVIEW


def test_stale_pending_payment_is_listed_and_fresh_one_is_not(db, user, package):
    stale_purchase = make_purchase(db, user, package, key="stale")
    stale = make_payment(db, stale_purchase, checkout="ws_CO_stale")
    stale.initiated_at = NOW - timedelta(hours=1)
    fresh_purchase = make_purchase(db, user, package, key="fresh-pending")
    fresh = make_payment(db, fresh_purchase, checkout="ws_CO_fresh")
    fresh.initiated_at = NOW - timedelta(minutes=1)
    db.commit()

    listed = by_payment(find_unresolved_cases(db, now=NOW))

    assert listed[stale.id].reason is RecoveryReason.PENDING_STALE
    assert listed[stale.id].action is RecoveryAction.CHECK_PAYMENT_STATUS
    assert fresh.id not in listed


def test_failed_payments_are_not_listed(db, user, package):
    purchase = make_purchase(db, user, package, key="failed-payment")
    payment = make_payment(db, purchase, checkout="ws_CO_failedpay", status="failed")

    assert payment.id not in by_payment(find_unresolved_cases(db, now=NOW))


def test_oldest_case_comes_first(db, user, package):
    first = paid(db, user, package, "order-1")
    second = paid(db, user, package, "order-2")

    ids = [c.payment_id for c in find_unresolved_cases(db, now=NOW)
           if c.payment_id in (first.id, second.id)]

    assert ids == [first.id, second.id]


def test_get_case_returns_one_case_or_none(db, user, package):
    broken = paid(db, user, package, "one-broken")
    healthy = paid(db, user, package, "one-healthy")
    add_session(db, user, package, healthy, "ACTIVE", "succeeded",
                started_at=LONG_AGO, expires_at=NOW + timedelta(hours=1))

    assert get_case(db, broken.id, now=NOW).reason is RecoveryReason.PAID_NO_SESSION
    assert get_case(db, healthy.id, now=NOW) is None
    assert get_case(db, 999_999_999, now=NOW) is None


@pytest.mark.parametrize("limit, offset", [(0, 0), (101, 0), (10, -1)])
def test_bad_paging_is_refused(db, limit, offset):
    with pytest.raises(ValueError):
        find_unresolved_cases(db, now=NOW, limit=limit, offset=offset)


def test_naive_time_is_refused(db):
    with pytest.raises(ValueError, match="timezone-aware"):
        find_unresolved_cases(db, now=datetime(2026, 11, 24, 12, 0))
        