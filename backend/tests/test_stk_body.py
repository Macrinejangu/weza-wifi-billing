"""Tests for the STK Push request body builder.

No network and no real credentials. Settings are built by hand with distinctive
fake values. The builder must fail closed: anything Daraja might reject, or that
would aim money at the wrong party, raises ValueError before a request is made.
"""
import dataclasses
import pytest

from app.config import ACCOUNT_PAYBILL, ACCOUNT_TILL, DarajaSettings
from app.integrations.mpesa.stk_body import build_stk_push_body
from app.payments.daraja_password import build_password

TIMESTAMP = "20261118120000"
PHONE = "254708374149"

PAYBILL = DarajaSettings(
    environment="sandbox",
    consumer_key="KEY-123",
    consumer_secret="SECRET-456",
    shortcode="174379",
    passkey="PASSKEY-789",
    callback_url="https://example.test/callback",
    account_type=ACCOUNT_PAYBILL,
    party_b="174379",
)

# A till pays a different receiving number (PartyB) than the BusinessShortCode.
TILL = dataclasses.replace(PAYBILL, account_type=ACCOUNT_TILL, party_b="123456")

def build(settings=PAYBILL, **overrides):
    """Build a body from valid defaults, changing only what a test overrides."""
    values = {
        "amount": 10,
        "phone_number": PHONE,
        "account_reference": "WEZA-1",
        "description": "Wifi",
        "timestamp": TIMESTAMP,
    }
    values.update(overrides)
    return build_stk_push_body(settings, **values)

def test_paybill_body_has_the_expected_fields():
    body = build(PAYBILL)

    assert body["TransactionType"] == "CustomerPayBillOnline"
    assert body["BusinessShortCode"] == "174379"
    assert body["PartyB"] == "174379"
    assert body["Amount"] == 10
    assert body["Timestamp"] == TIMESTAMP
    assert body["CallBackURL"] == "https://example.test/callback"
    assert body["AccountReference"] == "WEZA-1"
    assert body["TransactionDesc"] == "Wifi"

def test_till_body_uses_buy_goods_and_its_own_party_b():
    body = build(TILL)

    assert body["TransactionType"] == "CustomerBuyGoodsOnline"
    # The money goes to PartyB, not to the shortcode.
    assert body["PartyB"] == "123456"
    assert body["BusinessShortCode"] == "174379"

def test_body_contains_exactly_the_documented_fields():
    assert set(build()) == {
        "BusinessShortCode",
        "Password",
        "Timestamp",
        "TransactionType",
        "Amount",
        "PartyA",
        "PartyB",
        "PhoneNumber",
        "CallBackURL",
        "AccountReference",
        "TransactionDesc",
    }

def test_password_is_built_from_the_same_timestamp():
    body = build()

    # Daraja rejects the request if Timestamp and Password disagree.
    assert body["Password"] == build_password("174379","PASSKEY-789", TIMESTAMP)

def test_phone_number_is_used_for_party_a_and_the_prompt():
    body = build()

    assert body["PartyA"] == PHONE
    assert body["PhoneNumber"] == PHONE

def test_minimum_amount_is_accepted():
    assert build(amount=1)["Amount"] == 1

@pytest.mark.parametrize(
    "amount",
    [0, -1, 1.5, "10", None, True],
)
def test_invalid_amounts_are_rejected(amount):
    with pytest.raises(ValueError, match="amount"):
        build(amount=amount)


@pytest.mark.parametrize(
    "phone",
    [
        "0712345678",                  # local form: the schema must convert it first
        "+254712345678",               # leading plus
        "25471234567",                 # one digit short
        "254212345678",                # 2 is not a mobile prefix
        "2547" + "\u0661" * 8,         # non-ASCII digits
        "",                            # empty
    ],
)
def test_invalid_phone_numbers_are_rejected(phone):
    with pytest.raises(ValueError, match="phone_number"):
        build(phone_number=phone)


def test_2541_numbers_are_accepted():
     # Allowed, but NOT yet verified against the sandbox: the docs show 2547 only.
     assert build(phone_number="254112345678")["PartyA"] == "254112345678"

@pytest.mark.parametrize("reference", ["A","A"*12])
def test_account_reference_within_limit_is_accepted(reference):
    assert build(account_reference=reference)["AccountReference"] == reference


@pytest.mark.parametrize("reference", ["", "A"*13])
def test_account_reference_outside_limit_is_rejected_not_truncated(reference):
    with pytest.raises(ValueError, match="account_reference"):
        build(account_reference=reference)

@pytest.mark.parametrize("description", ["A", "A" * 13])
def test_description_within_limit_is_accepted(description):
    assert build(description=description)["TransactionDesc"] == description

@pytest.mark.parametrize("description", ["", "A" * 14])
def test_description_outside_limit_is_rejected_not_truncated(description):
    with pytest.raises(ValueError, match="description"):
        build(description=description)


@pytest.mark.parametrize(
    "party_b",
    [
        None,                      # missing
        "",                        # empty
        "12ab",                    # letters
        "\u0661\u0662\u0663\u0664\u0665\u0666",  # non-ASCII digits
    ],
)
def test_missing_or_malformed_party_b_is_rejected(party_b):
    settings = dataclasses.replace(PAYBILL, party_b=party_b)

    with pytest.raises(ValueError, match="party_b"):
        build(settings)


def test_unknown_account_type_is_rejected():
    settings = dataclasses.replace(PAYBILL, account_type="shop")

    with pytest.raises(ValueError, match="account type"):
        build(settings)


@pytest.mark.parametrize("shortcode", ["1234", "1234567", "12345a"])
def test_shortcode_must_be_five_or_six_digits(shortcode):
    settings = dataclasses.replace(PAYBILL, shortcode=shortcode)

    with pytest.raises(ValueError, match="shortcode"):
        build(settings)

def test_bad_timestamp_is_rejected():
    with pytest.raises(ValueError, match="timestamp"):
        build(timestamp="2026-11-18")