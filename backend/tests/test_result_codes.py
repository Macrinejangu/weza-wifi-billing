"""Tests for ResultCode parsing and failure-reason mapping."""
import pytest

from app.payments.result_codes import(
    FailureReason,
    failure_reason_for,
    is_success,
    parse_result_code,
)

@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0,0), (1032, 1032), ("0", 0), ("1032", 1032), (2001, 2001)],
)
def test_parse_accepts_clean_integers_and_digit_strings(raw, expected):
    assert parse_result_code(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [True, False, None, 1.0, "", " 0", "-1", "abc", "1.0", "٣", []],
)
def test_parse_rejects_everything_else(raw):
    assert parse_result_code(raw) is None

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, True),
        ("0", True),
        (1032, False),
        ("1032", False),
        (None, False),
        ("abc", False),
        (False, False),
        (0.0, False),
    ],
)
def test_is_success_is_true_only_for_exact_zero(raw, expected):
    assert is_success(raw) is expected

@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (1, FailureReason.INSUFFICIENT_FUNDS),
        (1032, FailureReason.CANCELLED),
        (1037, FailureReason.TIMED_OUT),
        (2001, FailureReason.WRONG_PIN),
    ],
)
def test_known_codes_map_to_their_reason(code, expected):
    assert failure_reason_for(code) is expected

@pytest.mark.parametrize("code", [17, 26, 1001, 9999])
def test_unrecognised_codes_map_to_unknown(code):
    assert failure_reason_for(code) is FailureReason.UNKNOWN

def test_zero_is_refused_as_a_failure():
    with pytest.raises(ValueError):
        failure_reason_for(0)

def test_failure_reason_values_are_the_agreed_set():
    assert {r.value for r in FailureReason} == {
        "insufficient_funds",
        "wrong_pin",
        "cancelled",
        "timed_out",
        "phone_busy",
        "system_error",
        "unknown",
    }