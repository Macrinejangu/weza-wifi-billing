"""Tests for interpreting the STK Push Query reply."""
import pytest

from app.integrations.mpesa.stk_query import (
    StkQueryOutcome,
    StkQueryResult,
    interpret_stk_query_response,
)
from app.payments.result_codes import FailureReason

CHECKOUT_ID = "ws_CO_191220191020363925"

def make_body(**overrides) -> dict:
    """A reply saying the payment succeeded; overrides break one thing."""
    body = {
        "ResponseCode": "0",
        "ResponseDescription": "The service request has been accepted successfully",
        "MerchantRequestID": "29115-34620561-1",
        "CheckoutRequestID": CHECKOUT_ID,
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    }
    body.update(overrides)
    return body

def test_result_code_zero_for_our_payment_is_paid():
    result = interpret_stk_query_response(make_body(), CHECKOUT_ID)

    assert result.outcome is StkQueryOutcome.PAID
    assert result.result_code == 0
    assert result.failure_reason is None
    assert result.result_desc == "The service request is processed successfully."

def test_result_code_sent_as_an_int_is_also_paid():
    result = interpret_stk_query_response(make_body(ResultCode=0), CHECKOUT_ID)

    assert result.outcome is StkQueryOutcome.PAID

@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("1", FailureReason.INSUFFICIENT_FUNDS),
        ("1032", FailureReason.CANCELLED),
        (1037, FailureReason.TIMED_OUT),
        (2001, FailureReason.WRONG_PIN),
        ("9999", FailureReason.UNKNOWN),
    ],
)
def test_non_zero_result_code_is_failed_with_a_reason(code, reason):
    result = interpret_stk_query_response(make_body(ResultCode=code), CHECKOUT_ID)

    assert result.outcome is StkQueryOutcome.FAILED
    assert result.result_code == int(code)
    assert result.failure_reason is reason

@pytest.mark.parametrize("bad_desc", [None, 5, "x" * 1025])
def test_result_desc_is_kept_only_when_it_is_a_short_string(bad_desc):
    result = interpret_stk_query_response(make_body(ResultDesc=bad_desc), CHECKOUT_ID)

    assert result.outcome is StkQueryOutcome.PAID
    assert result.result_desc is None

@pytest.mark.parametrize("bad_code", ["1", 1, None, "abc", True])
def test_unusable_response_code_is_unknown(bad_code):
    # The query itself was not processed, so its ResultCode means nothing.
    result = interpret_stk_query_response(make_body(ResponseCode=bad_code), CHECKOUT_ID)

    assert result.outcome is StkQueryOutcome.UNKNOWN

@pytest.mark.parametrize("other_id", ["ws_CO_OTHER", None, 123, ""])
def test_reply_about_another_payment_is_never_paid(other_id):
    # The body still says ResultCode 0: it must not settle OUR payment.
    result = interpret_stk_query_response(
        make_body(CheckoutRequestID=other_id), CHECKOUT_ID
    )

    assert result.outcome is StkQueryOutcome.UNKNOWN

@pytest.mark.parametrize("bad_result_code", [None, True, 1.0, "abc", ""])
def test_unusable_result_code_is_unknown(bad_result_code):
    result = interpret_stk_query_response(
        make_body(ResultCode=bad_result_code), CHECKOUT_ID
    )

    assert result.outcome is StkQueryOutcome.UNKNOWN


@pytest.mark.parametrize("missing", ["ResponseCode", "CheckoutRequestID", "ResultCode"])
def test_missing_fields_are_unknown(missing):
    body = make_body()
    del body[missing]

    assert interpret_stk_query_response(body, CHECKOUT_ID).outcome is StkQueryOutcome.UNKNOWN

@pytest.mark.parametrize("body", [None, [], "text", 5])
def test_body_that_is_not_an_object_is_unknown(body):
    assert interpret_stk_query_response(body, CHECKOUT_ID).outcome is StkQueryOutcome.UNKNOWN


@pytest.mark.parametrize("bad_expected", ["", None, 5])
def test_expected_checkout_id_must_be_a_non_empty_string(bad_expected):
    with pytest.raises(ValueError):
        interpret_stk_query_response(make_body(), bad_expected)


@pytest.mark.parametrize(
    ("outcome", "code", "reason"),
    [
        (StkQueryOutcome.PAID, 1, None),
        (StkQueryOutcome.PAID, 0, FailureReason.CANCELLED),
        (StkQueryOutcome.FAILED, 0, FailureReason.UNKNOWN),
        (StkQueryOutcome.FAILED, 1032, None),
        (StkQueryOutcome.UNKNOWN, 1032, None),
        (StkQueryOutcome.UNKNOWN, None, FailureReason.CANCELLED),
    ],
)
def test_result_rejects_inconsistent_combinations(outcome, code, reason):
    with pytest.raises(ValueError):
        StkQueryResult(outcome, result_code=code, failure_reason=reason)


def test_outcome_values_are_the_agreed_set():
    assert {o.value for o in StkQueryOutcome} == {"paid", "failed", "unknown"}