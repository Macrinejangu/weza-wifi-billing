"""Tests for the payment and activation status vocabularies.

These values are stored in the database and shown to staff, so any change
to them must be deliberate and fail a test.
"""
import pytest

from app.payments.statuses import ActivationStatus, PaymentStatus


def test_payment_status_values_are_exactly_the_agreed_set():
    assert {s.value for s in PaymentStatus} == {
        "pending",
        "successful",
        "failed",
        "expired",
    }


def test_activation_status_values_are_exactly_the_agreed_set():
    assert {s.value for s in ActivationStatus} == {
        "not_started",
        "waiting",
        "succeeded",
        "failed",
    }


def test_expired_is_distinct_from_failed():
    # "expired" means unknown outcome; "failed" means Safaricom said no.
    assert PaymentStatus.EXPIRED != PaymentStatus.FAILED
    assert PaymentStatus.EXPIRED == "expired"


def test_payment_status_parses_database_strings_and_rejects_unknown():
    assert PaymentStatus("expired") is PaymentStatus.EXPIRED
    with pytest.raises(ValueError):
        PaymentStatus("paid")