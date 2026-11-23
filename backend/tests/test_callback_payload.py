"""Tests for the field parsers and the envelope parser used on Daraja callbacks."""
import copy
import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from app.integrations.mpesa.callback_payload import (
    MalformedCallbackError,
    StkCallback,
    parse_amount,
    parse_phone,
    parse_receipt,
    parse_stk_callback,
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
    with pytest.raises(MalformedCallbackError):
        parse_phone(raw)


def test_parse_phone_error_does_not_leak_the_number():
    # Exception messages end up in logs, and full phone numbers must never be
    # logged. This proves the error text never contains the rejected value.
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


# ---------- The callback envelope ----------

# The two official Daraja sample payloads, kept as data and deep-copied by
# each test so one test can never change another test's input.
SUCCESS_SAMPLE = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-34620561-1",
            "CheckoutRequestID": "ws_CO_191220191020363925",
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 1.0},
                    {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                    {"Name": "TransactionDate", "Value": 20191219102115},
                    {"Name": "PhoneNumber", "Value": 254708374149},
                ]
            },
        }
    }
}

FAILURE_SAMPLE = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "f1e2-4b95-a71d-b30d3cdbb7a7942864",
            "CheckoutRequestID": "ws_CO_21072024125243250722943992",
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user",
        }
    }
}

def success_payload() -> dict:
    return copy.deepcopy(SUCCESS_SAMPLE)

def failure_payload() -> dict:
    return copy.deepcopy(FAILURE_SAMPLE)

def inner(payload: dict) -> dict:
    """Shortcut to the stkCallback object so tests can edit it in place."""
    return payload["Body"]["stkCallback"]

def test_official_success_sample_is_parsed_completely():
    callback = parse_stk_callback(success_payload())

    assert callback.merchant_request_id == "29115-34620561-1"
    assert callback.checkout_request_id == "ws_CO_191220191020363925"
    assert callback.result_code == 0
    assert callback.is_success is True
    assert callback.amount == 1
    assert callback.mpesa_receipt_number == "NLJ7RT61SV"
    assert callback.phone_number == "254708374149"
    assert callback.transaction_date == EXPECTED_DATE

def test_official_failure_sample_is_parsed_with_no_payment_details():
    callback = parse_stk_callback(failure_payload())

    assert callback.checkout_request_id == "ws_CO_21072024125243250722943992"
    assert callback.result_code == 1032
    assert callback.result_desc == "Request cancelled by user"
    assert callback.is_success is False
    assert callback.amount is None
    assert callback.mpesa_receipt_number is None
    assert callback.phone_number is None
    assert callback.transaction_date is None

def test_failure_with_garbage_metadata_is_still_a_clean_failure():
    payload = failure_payload()
    inner(payload)["CallbackMetadata"] = "garbage"

    callback = parse_stk_callback(payload)

    assert callback.is_success is False
    assert callback.amount is None

def test_success_ignores_unknown_items_and_items_without_a_value():
    payload = success_payload()
    inner(payload)["CallbackMetadata"]["Item"] += [
        {"Name": "Balance"},  # no Value at all
        {"Name": "SomethingNew", "Value": "x"},
    ]

    callback =parse_stk_callback(payload)

    assert callback.is_success is True
    assert callback.amount == 1

def test_result_code_sent_as_a_string_is_accepted():
    payload = success_payload()
    inner(payload)["ResultCode"] = "0"

    assert parse_stk_callback(payload).is_success is True


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "text",
        {},
        {"Body": None},
        {"Body": {}},
        {"Body": {"stkCallback": []}},
    ],
)
def test_wrong_envelope_shape_is_rejected(payload):
    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("MerchantRequestID", ""),
        ("MerchantRequestID", 123),
        ("MerchantRequestID", "a b"),
        ("MerchantRequestID", "x" * 101),
        ("CheckoutRequestID", None),
        ("CheckoutRequestID", "ws_CO_1\n"),  # trailing newline must not pass
        ("ResultCode", True),
        ("ResultCode", "abc"),
        ("ResultCode", 1.0),
        ("ResultCode", None),
        ("ResultDesc", None),
        ("ResultDesc", 5),
        ("ResultDesc", "x" * 1025),
    ],
)
def test_bad_top_level_values_are_rejected(field_name, bad_value):
    payload = failure_payload()
    inner(payload)[field_name] = bad_value

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


@pytest.mark.parametrize(
    "field_name",
    ["MerchantRequestID", "CheckoutRequestID", "ResultCode", "ResultDesc"],
)
def test_missing_top_level_fields_are_rejected(field_name):
    payload = failure_payload()
    del inner(payload)[field_name]

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


def test_success_without_metadata_is_rejected():
    payload = success_payload()
    del inner(payload)["CallbackMetadata"]

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


@pytest.mark.parametrize(
    "missing_name",
    ["Amount", "MpesaReceiptNumber", "PhoneNumber", "TransactionDate"],
)
def test_success_missing_a_required_item_is_rejected(missing_name):
    payload = success_payload()
    metadata = inner(payload)["CallbackMetadata"]
    metadata["Item"] = [i for i in metadata["Item"] if i["Name"] != missing_name]

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


def test_success_with_a_duplicate_item_is_rejected():
    payload = success_payload()
    inner(payload)["CallbackMetadata"]["Item"].append({"Name": "Amount", "Value": 1.0})

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


def test_success_with_a_bad_item_value_is_rejected():
    payload = success_payload()
    inner(payload)["CallbackMetadata"]["Item"][0]["Value"] = 1.5  # not whole shillings

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


@pytest.mark.parametrize(
    "bad_metadata",
    [
        None,
        [],
        {"Item": None},
        {"Item": {}},
        {"Item": ["x"]},
        {"Item": [{"Value": 1}]},  # no Name
        {"Item": [{"Name": 5, "Value": 1}]},  # Name is not a string
        {"Item": [{"Name": f"N{i}", "Value": i} for i in range(21)]},  # too many
    ],
)
def test_success_with_bad_metadata_shape_is_rejected(bad_metadata):
    payload = success_payload()
    inner(payload)["CallbackMetadata"] = bad_metadata

    with pytest.raises(MalformedCallbackError):
        parse_stk_callback(payload)


def test_error_messages_do_not_leak_rejected_values():
    bad_phone = success_payload()
    inner(bad_phone)["CallbackMetadata"]["Item"][3]["Value"] = 254208374149
    with pytest.raises(MalformedCallbackError) as phone_error:
        parse_stk_callback(bad_phone)
    assert "254208374149" not in str(phone_error.value)

    bad_id = failure_payload()
    inner(bad_id)["CheckoutRequestID"] = "bad id 254708374149"
    with pytest.raises(MalformedCallbackError) as id_error:
        parse_stk_callback(bad_id)
    assert "254708374149" not in str(id_error.value)


def test_repr_does_not_contain_the_phone_number():
    callback = parse_stk_callback(success_payload())

    assert "254708374149" not in repr(callback)


def test_parsed_callback_is_immutable():
    callback = parse_stk_callback(success_payload())

    with pytest.raises(dataclasses.FrozenInstanceError):
        callback.amount = 999