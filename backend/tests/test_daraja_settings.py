"""Tests for daraja_settings().

These tests never read the real .env file or the developer's shell: a fixture
removes every DARAJA_* variable and sets a known baseline. The fake credentials
are distinctive so we can assert they never appear in repr().
"""

import dataclasses

import pytest

from app import config
from app.config import ACCOUNT_PAYBILL, ACCOUNT_TILL, daraja_settings

DARAJA_VARIABLES = [
    "DARAJA_ENV",
    "DARAJA_CONSUMER_KEY",
    "DARAJA_CONSUMER_SECRET",
    "DARAJA_SHORTCODE",
    "DARAJA_PASSKEY",
    "DARAJA_CALLBACK_URL",
    "DARAJA_ACCOUNT_TYPE",
    "DARAJA_PARTY_B",
]

REQUIRED_VARIABLES = [
    "DARAJA_CONSUMER_KEY",
    "DARAJA_CONSUMER_SECRET",
    "DARAJA_SHORTCODE",
    "DARAJA_PASSKEY",
    "DARAJA_CALLBACK_URL",
]


@pytest.fixture(autouse=True)
def clean_daraja_env(monkeypatch):
    """Give every test a valid, known sandbox paybill environment."""
    # Without this, load_dotenv would re-read the developer's real .env and
    # undo the deletions below.
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    for name in DARAJA_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("DARAJA_CONSUMER_KEY", "KEY-123")
    monkeypatch.setenv("DARAJA_CONSUMER_SECRET", "SECRET-456")
    monkeypatch.setenv("DARAJA_SHORTCODE", "174379")
    monkeypatch.setenv("DARAJA_PASSKEY", "PASSKEY-789")
    monkeypatch.setenv("DARAJA_CALLBACK_URL", "https://example.test/callback")


def test_valid_paybill_settings():
    settings = daraja_settings()

    assert settings.environment == "sandbox"
    assert settings.shortcode == "174379"
    assert settings.callback_url == "https://example.test/callback"
    assert settings.account_type == ACCOUNT_PAYBILL
    # For a paybill the money goes to the shortcode itself.
    assert settings.party_b == "174379"


def test_environment_defaults_to_sandbox():
    # DARAJA_ENV is not set by the fixture.
    assert daraja_settings().environment == "sandbox"


@pytest.mark.parametrize("value", ["production", ""])
def test_non_sandbox_environment_is_rejected(monkeypatch, value):
    monkeypatch.setenv("DARAJA_ENV", value)

    with pytest.raises(RuntimeError, match="sandbox"):
        daraja_settings()


@pytest.mark.parametrize("name", REQUIRED_VARIABLES)
def test_each_missing_variable_is_reported_by_name(monkeypatch, name):
    monkeypatch.delenv(name)

    with pytest.raises(RuntimeError, match=name):
        daraja_settings()


def test_all_missing_variables_are_listed_together(monkeypatch):
    for name in REQUIRED_VARIABLES:
        monkeypatch.delenv(name)

    with pytest.raises(RuntimeError) as info:
        daraja_settings()

    # One run should tell the developer everything that is missing.
    for name in REQUIRED_VARIABLES:
        assert name in str(info.value)


def test_empty_value_counts_as_missing(monkeypatch):
    monkeypatch.setenv("DARAJA_CONSUMER_KEY", "")

    with pytest.raises(RuntimeError, match="DARAJA_CONSUMER_KEY"):
        daraja_settings()


def test_http_callback_url_is_rejected(monkeypatch):
    monkeypatch.setenv("DARAJA_CALLBACK_URL", "http://example.test/callback")

    with pytest.raises(RuntimeError, match="https"):
        daraja_settings()


def test_account_type_is_trimmed_and_case_insensitive(monkeypatch):
    monkeypatch.setenv("DARAJA_ACCOUNT_TYPE", " Till ")
    monkeypatch.setenv("DARAJA_PARTY_B", "123456")

    assert daraja_settings().account_type == ACCOUNT_TILL


@pytest.mark.parametrize("value", ["shop", "", "paybill,till"])
def test_unknown_account_type_is_rejected(monkeypatch, value):
    monkeypatch.setenv("DARAJA_ACCOUNT_TYPE", value)

    with pytest.raises(RuntimeError, match="DARAJA_ACCOUNT_TYPE"):
        daraja_settings()


def test_till_uses_its_own_party_b_not_the_shortcode(monkeypatch):
    monkeypatch.setenv("DARAJA_ACCOUNT_TYPE", "till")
    monkeypatch.setenv("DARAJA_PARTY_B", "123456")

    settings = daraja_settings()

    # Regression: a misplaced else once overwrote this with the shortcode.
    assert settings.party_b == "123456"
    assert settings.shortcode == "174379"


@pytest.mark.parametrize("value", [None, "   "])
def test_till_without_party_b_is_rejected(monkeypatch, value):
    monkeypatch.setenv("DARAJA_ACCOUNT_TYPE", "till")
    if value is not None:
        monkeypatch.setenv("DARAJA_PARTY_B", value)

    with pytest.raises(RuntimeError, match="DARAJA_PARTY_B"):
        daraja_settings()


@pytest.mark.parametrize(
    "value",
    [
        "12ab",                              # letters
        "12 34",                             # inner space
        "\u0661\u0662\u0663\u0664",          # Arabic-Indic digits
    ],
)
def test_till_party_b_must_be_ascii_digits(monkeypatch, value):
    monkeypatch.setenv("DARAJA_ACCOUNT_TYPE", "till")
    monkeypatch.setenv("DARAJA_PARTY_B", value)

    with pytest.raises(RuntimeError, match="digits"):
        daraja_settings()


def test_paybill_ignores_a_stray_party_b(monkeypatch):
    # A leftover DARAJA_PARTY_B must not redirect a paybill's money.
    monkeypatch.setenv("DARAJA_PARTY_B", "999999")

    assert daraja_settings().party_b == "174379"


def test_secrets_are_hidden_from_repr():
    text = repr(daraja_settings())

    assert "KEY-123" not in text
    assert "SECRET-456" not in text
    assert "PASSKEY-789" not in text


def test_settings_cannot_be_changed_after_creation():
    settings = daraja_settings()

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(settings, "shortcode", "000000")