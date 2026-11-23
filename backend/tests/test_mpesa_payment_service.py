"""Tests for start_payment(), the database half of payment initiation.

They use the shared `db`, `user` and `package` fixtures, which roll back after
each test. NOTE: these are single-session tests. They prove the rules, but not
the row lock under a real race: that needs two connections, and comes with the
callback concurrency tests (WEZA-50).
"""
import logging

import pytest
from sqlalchemy import func, select

from app.models import Payment
from app.payments.payment_service_errors import (
    PaymentAlreadyPending,
    PurchaseNotFound,
    PurchaseNotPayable,
)
from app.services.mpesa_payment_service import StartedPayment, start_payment
from app.services.purchase_service import create_purchase

PHONE = "254712345678"


@pytest.fixture
def purchase(db, user, package):
    created, _ = create_purchase(db, user.id, package.id, "mpesa-service-test-1")
    return created


def payment_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Payment))


def test_creates_a_pending_payment_with_the_purchase_amount(db, purchase):
    started = start_payment(db, purchase.id, PHONE)

    payment = db.get(Payment, started.payment_id)
    assert started.purchase_id == purchase.id
    assert started.amount == 20  # the price of the `package` fixture
    assert payment.status == "pending"
    assert payment.amount == 20
    assert payment.phone_number == PHONE
    assert payment.initiated_at is not None
    assert payment.checkout_request_id is None  # Daraja has not answered yet


def test_amount_is_the_snapshot_not_the_current_package_price(db, purchase, package):
    package.price = 999
    db.commit()

    started = start_payment(db, purchase.id, PHONE)

    assert started.amount == 20
    assert db.get(Payment, started.payment_id).amount == 20


def test_unknown_purchase_is_not_found_and_nothing_is_recorded(db):
    with pytest.raises(PurchaseNotFound):
        start_payment(db, 999999, PHONE)

    assert payment_count(db) == 0


@pytest.mark.parametrize("status", ["paid", "failed", "expired"])
def test_purchase_that_is_not_pending_is_not_payable(db, purchase, status):
    purchase.status = status
    db.commit()

    with pytest.raises(PurchaseNotPayable):
        start_payment(db, purchase.id, PHONE)

    assert payment_count(db) == 0


def test_double_tap_returns_the_existing_payment_and_adds_none(db, purchase):
    first = start_payment(db, purchase.id, PHONE)

    with pytest.raises(PaymentAlreadyPending) as info:
        start_payment(db, purchase.id, PHONE)

    assert info.value.payment_id == first.payment_id
    assert payment_count(db) == 1


def test_a_new_payment_is_allowed_after_the_previous_one_failed(db, purchase):
    first = start_payment(db, purchase.id, PHONE)
    db.get(Payment, first.payment_id).status = "failed"
    db.commit()

    second = start_payment(db, purchase.id, PHONE)

    assert second.payment_id != first.payment_id
    assert payment_count(db) == 2


@pytest.mark.parametrize(
    "bad_phone",
    ["0712345678", "254212345678", "254712345678\n", None],
)
def test_unnormalised_phone_is_refused_before_touching_the_database(
    db, purchase, bad_phone
):
    with pytest.raises(ValueError):
        start_payment(db, purchase.id, bad_phone)

    assert payment_count(db) == 0


@pytest.mark.parametrize("bad_id", [0, -1, True, "1"])
def test_invalid_purchase_id_is_refused(db, bad_id):
    with pytest.raises(ValueError):
        start_payment(db, bad_id, PHONE)

    assert payment_count(db) == 0


def test_started_payment_repr_hides_the_phone_number():
    started = StartedPayment(
        payment_id=1, purchase_id=2, amount=20, phone_number=PHONE
    )

    assert PHONE not in repr(started)


def test_log_contains_the_ids_and_a_masked_phone_only(db, purchase, caplog):
    caplog.set_level(logging.INFO)

    started = start_payment(db, purchase.id, PHONE)

    assert f"payment_id={started.payment_id}" in caplog.text
    assert "254******678" in caplog.text
    assert PHONE not in caplog.text