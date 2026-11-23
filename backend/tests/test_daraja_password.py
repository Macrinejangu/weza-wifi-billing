"""Tests for the Daraja timestamp and password builder.

They pin down the rules that cause hard-to-debug "wrong credentials" errors:
Nairobi time, a 14-digit ASCII format, correct date rollover, and the exact
shortcode + passkey + timestamp ordering inside the password.
"""
import base64
from datetime import datetime, timezone

import pytest
from app.payments.daraja_password import build_password, daraja_timestamp


def test_timestamp_is_converted_to_nairobi_time():
    # 09:00 UTC is 12:00 in Nairobi (UTC+3)
    utc_moment = datetime(2026, 11, 17, 9, 0, 0, tzinfo=timezone.utc)

    assert daraja_timestamp(utc_moment) == "20261117120000"


def test_timestamp_rolls_over_to_the_next_day():
    # 22:30 UTC on the 17th is 01:30 on the 18th in Nairobi.
    utc_moment = datetime(2026, 11, 17, 22, 30, 5, tzinfo=timezone.utc)

    assert daraja_timestamp(utc_moment) == "20261118013005"


def test_naive_datetime_is_rejected():
    # A datetime with no timezone could be read as the wrong zone, so refuse it.
    with pytest.raises(ValueError):
        daraja_timestamp(datetime(2026, 11, 17, 9, 0, 0))


def test_default_timestamp_has_fourteen_digits():
    stamp=daraja_timestamp()
    assert len(stamp) == 14
    assert stamp.isdigit()


def test_password_is_base64_of_shortcode_passkey_timestamp():
    password=build_password("174379", "test-passkey", "20261117120000")

    # Decoding proves both the encoding and the order of the three parts.
    decoded=base64.b64decode(password).decode("utf-8")
    assert decoded == "174379test-passkey20261117120000"


@pytest.mark.parametrize(
    "shortcode, passkey, timestamp",
    [
        ("", "test-passkey", "20261117120000"),         # missing shortcode
        ("174379", "", "20261117120000"),               # missing passkey
        ("174379", "test-passkey", "2026-11-17"),       # wrong format
        ("174379", "test-passkey", "2026111712000"),    # 13 digits
        ("174379", "test-passkey", "20261117120000x"),  # trailing character
        # 14 Arabic-Indic digits: valid for \d in Python, but Daraja needs 0-9.
        (
            "174379",
            "test-passkey",
            "\u0662\u0660\u0662\u0666\u0661\u0661\u0661\u0667"
            "\u0661\u0662\u0660\u0660\u0660\u0660",
        ),
    ],
)
def test_password_rejects_bad_inputs(shortcode, passkey, timestamp):
    with pytest.raises(ValueError):
        build_password(shortcode, passkey, timestamp)