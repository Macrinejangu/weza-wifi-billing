"""Tests for matching a parsed callback against the stored payment."""
import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from app.integrations.mpesa.callback_payload import StkCallback
from app.payments.callback_verification import (
    CallbackVerdict,
    ExpectedPayment,
    verify_callback,
)

CHECKOUT_ID = "ws_CO_191220191020363925"
MERCHANT_ID = "29115-34620561-1"
PHONE = "254708374149"
AMOUNT = 100

EXPECTED = ExpectedPayment(
    checkout_request_id=CHECKOUT_ID,
    merchant_request_id=MERCHANT_ID,
    amount=AMOUNT,
    phone_number=PHONE,
)


def make_success(**overrides) -> StkCallback:
    """A callback that matches EXPECTED exactly; overrides break one thing."""
    base = StkCallback(
        merchant_request_id=MERCHANT_ID,
        checkout_request_id=CHECKOUT_ID,
        result_code=0,
        result_desc="The service request is processed successfully.",
        amount=AMOUNT,
        mpesa_receipt_number="NLJ7RT61SV",
        phone_number=PHONE,
        transaction_date=datetime(
            2019, 12, 19, 10, 21, 15, tzinfo=timezone(timedelta(hours=3))
        ),
    )
    return dataclasses.replace(base, **overrides)


def make_failure(**overrides) -> StkCallback:
    """A cancelled-by-user callback for the same payment."""
    base = StkCallback(
        merchant_request_id=MERCHANT_ID,
        checkout_request_id=CHECKOUT_ID,
        result_code=1032,
        result_desc="Request cancelled by user",
        amount=None,
        mpesa_receipt_number=None,
        phone_number=None,
        transaction_date=None,
    )
    return dataclasses.replace(base, **overrides)


def test_matching_success_is_success_matched():
    assert verify_callback(make_success(), EXPECTED) is CallbackVerdict.SUCCESS_MATCHED


@pytest.mark.parametrize("code", [1, 1032, 2001, 9999])
def test_matching_failure_is_failure_matched(code):
    callback = make_failure(result_code=code)

    assert verify_callback(callback, EXPECTED) is CallbackVerdict.FAILURE_MATCHED


@pytest.mark.parametrize("make", [make_success, make_failure])
def test_other_checkout_id_is_rejected(make):
    callback = make(checkout_request_id="ws_CO_SOMEONE_ELSE")

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_CHECKOUT_ID_MISMATCH
    )


@pytest.mark.parametrize("make", [make_success, make_failure])
def test_other_merchant_id_is_rejected(make):
    callback = make(merchant_request_id="9999-OTHER-1")

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_MERCHANT_ID_MISMATCH
    )


@pytest.mark.parametrize("paid", [1, 99, 101, 10000])
def test_any_amount_difference_is_rejected(paid):
    # Includes underpayment and overpayment: we never guess intent.
    callback = make_success(amount=paid)

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_AMOUNT_MISMATCH
    )


@pytest.mark.parametrize("other_phone", ["254712345678", "254708374148"])
def test_other_phone_is_rejected(other_phone):
    callback = make_success(phone_number=other_phone)

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_PHONE_MISMATCH
    )


def test_identity_is_checked_before_amount():
    # Both the ID and the amount are wrong: the ID verdict must win, always.
    callback = make_success(checkout_request_id="ws_CO_SOMEONE_ELSE", amount=1)

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_CHECKOUT_ID_MISMATCH
    )


@pytest.mark.parametrize(
    "missing", ["amount", "mpesa_receipt_number", "phone_number"]
)
def test_success_missing_payment_details_is_rejected(missing):
    callback = make_success(**{missing: None})

    assert (
        verify_callback(callback, EXPECTED)
        is CallbackVerdict.REJECTED_INCOMPLETE_SUCCESS
    )


@pytest.mark.parametrize("bad_amount", [0, -1, True, 1.5, "100"])
def test_expected_payment_rejects_bad_amounts(bad_amount):
    with pytest.raises(ValueError):
        ExpectedPayment(
            checkout_request_id=CHECKOUT_ID,
            merchant_request_id=MERCHANT_ID,
            amount=bad_amount,
            phone_number=PHONE,
        )


@pytest.mark.parametrize(
    "empty_field", ["checkout_request_id", "merchant_request_id", "phone_number"]
)
def test_expected_payment_requires_non_empty_strings(empty_field):
    values = {
        "checkout_request_id": CHECKOUT_ID,
        "merchant_request_id": MERCHANT_ID,
        "amount": AMOUNT,
        "phone_number": PHONE,
    }
    values[empty_field] = ""

    with pytest.raises(ValueError):
        ExpectedPayment(**values)


def test_expected_payment_repr_does_not_contain_the_phone_number():
    assert PHONE not in repr(EXPECTED)


def test_verdict_values_are_the_agreed_set():
    assert {v.value for v in CallbackVerdict} == {
        "success_matched",
        "failure_matched",
        "rejected_checkout_id_mismatch",
        "rejected_merchant_id_mismatch",
        "rejected_incomplete_success",
        "rejected_amount_mismatch",
        "rejected_phone_mismatch",
    }