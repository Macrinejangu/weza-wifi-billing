"""Tests for the payment service's typed errors."""
import pytest

from app.payments.payment_service_errors import (
    OutcomeUnknown,
    PaymentAlreadyPending,
    PaymentServiceError,
    ProviderNotReached,
    ProviderRejected,
    PurchaseNotFound,
    PurchaseNotPayable,
)

ALL_ERRORS = [
    PurchaseNotFound,
    PurchaseNotPayable,
    PaymentAlreadyPending,
    ProviderRejected,
    ProviderNotReached,
    OutcomeUnknown,
]

# Every error that can be built with only a payment_id.
SIMPLE_ERRORS = [
    PurchaseNotFound,
    PurchaseNotPayable,
    ProviderRejected,
    ProviderNotReached,
    OutcomeUnknown,
]


def test_codes_are_unique_and_the_agreed_set():
    codes = [error.code for error in ALL_ERRORS]

    assert len(codes) == len(set(codes))
    assert set(codes) == {
        "purchase_not_found",
        "purchase_not_payable",
        "payment_already_pending",
        "provider_rejected",
        "provider_not_reached",
        "outcome_unknown",
    }


@pytest.mark.parametrize("error_class", ALL_ERRORS)
def test_errors_are_service_errors_but_not_value_or_lookup_errors(error_class):
    # main.py would turn ValueError and LookupError into a generic 400 or 404.
    assert issubclass(error_class, PaymentServiceError)
    assert not issubclass(error_class, (ValueError, LookupError))


@pytest.mark.parametrize("error_class", SIMPLE_ERRORS)
def test_message_is_fixed_and_payment_id_is_kept(error_class):
    error = error_class(payment_id=7)

    assert str(error) == error_class.message
    assert error.payment_id == 7


def test_payment_id_defaults_to_none():
    assert PurchaseNotFound().payment_id is None


def test_payment_already_pending_requires_a_payment_id():
    with pytest.raises(TypeError):
        PaymentAlreadyPending()


def test_payment_already_pending_carries_its_payment_id():
    error = PaymentAlreadyPending(payment_id=42)

    assert error.payment_id == 42
    assert str(error) == PaymentAlreadyPending.message


def test_caller_text_cannot_become_the_message():
    with pytest.raises(TypeError):
        PurchaseNotFound("secret detail")


def test_outcome_unknown_defaults_to_not_timed_out():
    assert OutcomeUnknown().timed_out is False


def test_outcome_unknown_remembers_a_timeout():
    assert OutcomeUnknown(timed_out=True).timed_out is True


def test_unknown_outcome_message_never_says_the_payment_failed():
    assert "fail" not in OutcomeUnknown.message.lower()