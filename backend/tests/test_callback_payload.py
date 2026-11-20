"""Tests for the field parsers used on Daraja callback data."""
from datetime import datetime, timedelta, timezone

import pytest

from app.integrations.mpesa.callback_payload import (
    MalformedCallbackError,
    parse_amount,
    parse_phone,
    parse_receipt,
    parse_transaction_date,
)

NAIROBI = timezone(timedelta(hours=3))

def test_malformed_callback_error_is_a_value_error():
    assert issubclass(MalformedCallbackError, ValueError)


# ---------- Amount ----------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1, 1),
        (1.0, 1),  # the official sample sends a float
        (10500.00, 10500),
        ("1", 1),
        ("1.0", 1),
        ("10500.00", 10500),
        ("250000", 250000),
    ],
)
def test_parse_amount_accepts_whole_shillings(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        True,
        False,
        None,
        0,
        0.0,
        "0",
        -1,
        "-1",
        1.5,
        "1.50",
        "",
        " 1",
        "1e3",
        "abc",
        "١",  # an Arabic-Indic digit, not an ASCII digit
        [],
        {},
        float("nan"),
        float("inf"),
        1e16,
        "1234567890",  # ten whole digits, above our bound
        "1.12345",  # five decimals, above our bound
    ],
)
def test_parse_amount_rejects_everything_else(raw):
    with pytest.raises(MalformedCallbackError):
        parse_amount(raw)



# ---------- Phone ----------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (254708374149, "254708374149"),  # the official sample is an int
        ("254708374149", "254708374149"),
        (254112345678, "254112345678"),
        ("254712345678", "254712345678"),
    ],
)
def test_parse_phone_accepts_254_mobile_numbers(raw, expected):
    assert parse_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        True,
        None,
        254708374149.0,  # a float is never accepted
        "0708374149",
        "+254708374149",
        "254708374149 ",
        "25470837414",  # eleven digits
        "2547083741490",  # thirteen digits
        254208374149,  # fourth character is 2, not 1 or 7
        "٢٥٤٧٠٨٣٧٤١٤٩",  # Arabic-Indic digits
        [],
        "",
    ],
)
def test_parse_phone_rejects_everything_else(raw):
    with pytest.raises(MalformedCallbackError) as info:
        parse_phone("254208374149")
    assert "254208374149" not in str(info.value)



# ---------- Receipt ----------

@pytest.mark.parametrize(
    "raw",
    ["NLJ7RT61SV", "SG722NMVXQ", "abcdef", "A" * 20],
)
def test_parse_receipt_accepts_alphanumeric_receipts(raw):
    assert parse_receipt(raw) == raw


@pytest.mark.parametrize(
    "raw",
    [
        None,
        123456789,
        "",
        "SHORT",  # five characters
        "A" * 21,
        "NLJ7 RT61SV",
        "NLJ7RT61SV\n",  # trailing newline must not slip through
        "NLJ7RT61S!",
    ],
)
def test_parse_receipt_rejects_everything_else(raw):
    with pytest.raises(MalformedCallbackError):
        parse_receipt(raw)



# ---------- Transaction date ----------

EXPECTED_DATE = datetime(2019, 12, 19, 10, 21, 15, tzinfo=NAIROBI)


@pytest.mark.parametrize("raw", [20191219102115, "20191219102115"])
def test_parse_transaction_date_accepts_int_and_string(raw):
    assert parse_transaction_date(raw) == EXPECTED_DATE

def test_parse_transaction_date_is_timezone_aware_nairobi():
    parsed = parse_transaction_date(20191219102115)
    assert parsed.utcoffset() == timedelta(hours=3)
    # 10:21 in Nairobi is 07:21 UTC: the offset labels the time, not shifts it.
    assert parsed.astimezone(timezone.utc).hour == 7


@pytest.mark.parametrize(
    "raw",
    [
        True,
        None,
        2019121910211,  # thirteen digits
        201912191021155,  # fifteen digits
        "20191319102115",  # month 13
        "20191219252115",  # hour 25
        "2019-12-19 10:21",
        20191219102115.0,  # a float is never accepted
        "",
        "20190230102115",  # 30 February
    ],
)
def test_parse_transaction_date_rejects_everything_else(raw):
    with pytest.raises(MalformedCallbackError):
        parse_transaction_date(raw)