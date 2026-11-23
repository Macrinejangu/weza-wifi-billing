"""Tests for the callback secret-token check."""
import pytest

from app.payments.callback_security import is_valid_token_format, token_matches

CONFIGURED = "abcdefghijklmnopqrstuvwxyz012345"  # 32 URL-safe characters

def test_exact_token_matches():
    assert token_matches(CONFIGURED, CONFIGURED) is True

@pytest.mark.parametrize(
    "received",
    [
        CONFIGURED[:-1],  # one character short
        CONFIGURED + "x",  # one character long
        CONFIGURED.upper(),  # wrong case
        "",
        None,
        123,
        CONFIGURED + "\n",  # trailing newline must not match
        " " + CONFIGURED,
        "é" * 32,  # non-ASCII: must be False, not a TypeError
        CONFIGURED[:-1] + "\ud800",  # lone surrogate: must not raise
    ],
)
def test_wrong_token_is_rejected(received):
    assert token_matches(received, CONFIGURED) is False

@pytest.mark.parametrize(
    "bad_configured",
    [
        "",
        "short",
        "a" * 31,
        "a" * 129,
        "has space" + "a" * 30,
        "ü" * 32,
        None,
        5,
        "a" * 32 + "\n",
    ],
)
def test_misconfigured_token_rejects_even_an_identical_value(bad_configured):
    # Sending the same weak value must still fail: a weak or missing setting
    # must never leave the endpoint open.
    assert token_matches(bad_configured, bad_configured) is False

@pytest.mark.parametrize(
    "good",
    ["a" * 32, "a" * 128, "Ab3_-Ab3_-Ab3_-Ab3_-Ab3_-Ab3_-Ab3_-Ab"],
)
def test_strong_tokens_are_valid(good):
    assert is_valid_token_format(good) is True

@pytest.mark.parametrize(
    "bad",
    ["", None, "a" * 31, "a" * 129, "a" * 32 + "\n", "ü" * 32],
)
def test_weak_or_odd_tokens_are_not_valid(bad):
    assert is_valid_token_format(bad) is False
    