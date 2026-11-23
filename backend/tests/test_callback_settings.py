"""Tests for callback_security_policy() (WEZA-50).

The real .env is neutralised so a developer's local secrets can never change
a test result, and every relevant variable is cleared before each test.
"""

import pytest

from app import config
from app.config import callback_security_policy
from app.payments.callback_security import CallbackDecision

TOKEN = "Abc123_-" * 5  # 40 URL-safe characters
URL = f"https://example.test/api/payments/mpesa/callback/{TOKEN}"

_VARIABLES = (
    "DARAJA_CALLBACK_TOKEN",
    "DARAJA_CALLBACK_URL",
    "CALLBACK_IP_CHECK_ENABLED",
    "CALLBACK_TRUSTED_PROXIES",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    # Without this, load_dotenv would re-read the developer's real .env.
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    for name in _VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DARAJA_CALLBACK_TOKEN", TOKEN)
    monkeypatch.setenv("DARAJA_CALLBACK_URL", URL)


def check(policy, *, token, peer="203.0.113.9"):
    return policy.check(peer=peer, forwarded_for=None, received_token=token)


def test_valid_settings_build_a_policy_with_the_ip_gate_off_by_default():
    policy = callback_security_policy()

    assert policy.ip_policy.enabled is False
    assert check(policy, token=TOKEN) is CallbackDecision.ALLOWED


def test_wrong_token_is_rejected_by_the_built_policy():
    policy = callback_security_policy()

    assert check(policy, token="x" * 40) is CallbackDecision.REJECTED_TOKEN


def test_missing_token_refuses_to_start(monkeypatch):
    monkeypatch.delenv("DARAJA_CALLBACK_TOKEN")

    with pytest.raises(RuntimeError, match="DARAJA_CALLBACK_TOKEN"):
        callback_security_policy()


def test_blank_token_refuses_to_start(monkeypatch):
    monkeypatch.setenv("DARAJA_CALLBACK_TOKEN", "   ")

    with pytest.raises(RuntimeError, match="DARAJA_CALLBACK_TOKEN"):
        callback_security_policy()


@pytest.mark.parametrize(
    "weak",
    ["change-me", "a" * 31, "a" * 129, "has space inside " + "a" * 30, "é" * 40],
)
def test_weak_or_malformed_token_refuses_to_start(monkeypatch, weak):
    monkeypatch.setenv("DARAJA_CALLBACK_TOKEN", weak)

    with pytest.raises(RuntimeError, match="32 to 128"):
        callback_security_policy()


def test_url_not_ending_with_the_token_refuses_to_start(monkeypatch):
    monkeypatch.setenv("DARAJA_CALLBACK_URL", "https://example.test/api/payments/mpesa/callback/other")

    with pytest.raises(RuntimeError) as error:
        callback_security_policy()

    assert "must end with" in str(error.value)
    assert TOKEN not in str(error.value)  # the secret never appears in errors


def test_token_must_be_a_whole_path_segment(monkeypatch):
    # Ends with the token's characters but not as its own segment.
    monkeypatch.setenv("DARAJA_CALLBACK_URL", f"https://example.test/prefix{TOKEN}")

    with pytest.raises(RuntimeError, match="must end with"):
        callback_security_policy()


def test_trailing_slash_on_the_url_is_accepted(monkeypatch):
    monkeypatch.setenv("DARAJA_CALLBACK_URL", URL + "/")

    assert check(callback_security_policy(), token=TOKEN) is CallbackDecision.ALLOWED


def test_enabled_ip_gate_rejects_an_address_outside_the_allowlist(monkeypatch):
    monkeypatch.setenv("CALLBACK_IP_CHECK_ENABLED", "true")
    policy = callback_security_policy()

    assert policy.ip_policy.enabled is True
    assert check(policy, token=TOKEN, peer="203.0.113.9") is CallbackDecision.REJECTED_IP
    allowed = str(next(iter(policy.ip_policy.allowed_ips)))
    assert check(policy, token=TOKEN, peer=allowed) is CallbackDecision.ALLOWED


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("TRUE", True), (" true ", True), ("false", False), ("", False), (" ", False)],
)
def test_ip_flag_accepts_only_true_or_false(monkeypatch, raw, expected):
    monkeypatch.setenv("CALLBACK_IP_CHECK_ENABLED", raw)

    assert callback_security_policy().ip_policy.enabled is expected


@pytest.mark.parametrize("raw", ["yes", "1", "ture", "on"])
def test_ip_flag_typo_is_an_error_not_a_silent_off(monkeypatch, raw):
    monkeypatch.setenv("CALLBACK_IP_CHECK_ENABLED", raw)

    with pytest.raises(RuntimeError, match="CALLBACK_IP_CHECK_ENABLED"):
        callback_security_policy()


def test_trusted_proxies_are_parsed_from_a_comma_list(monkeypatch):
    monkeypatch.setenv("CALLBACK_TRUSTED_PROXIES", "10.0.0.1, 10.0.0.2 ,")

    assert len(callback_security_policy().ip_policy.trusted_proxies) == 2


def test_invalid_proxy_address_refuses_to_start(monkeypatch):
    monkeypatch.setenv("CALLBACK_TRUSTED_PROXIES", "10.0.0.1,not-an-ip")

    with pytest.raises(RuntimeError, match="Invalid callback security settings"):
        callback_security_policy()