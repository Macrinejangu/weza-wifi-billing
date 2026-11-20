"""Field-level parsers for the values inside a Daraja STK Push callback.

Daraja callbacks are NOT signed, so everything in one is untrusted input from
the internet. Each parser here turns one raw JSON value into a clean Python
value, or raises MalformedCallbackError. We never guess, never "fix" odd input
and never fall back to a default: a callback we cannot read is treated as
unverified, which means NOT PAID and NO ACCESS. The STK status query is how a
genuine payment behind a rejected callback is still recovered.

Shapes in the official Daraja success sample:
    Amount             1.0              (a float, even for whole shillings)
    MpesaReceiptNumber "NLJ7RT61SV"     (a string)
    TransactionDate    20191219102115   (an integer, YYYYMMDDHHmmss)
    PhoneNumber        254708374149     (an integer)

Error messages deliberately never include the raw value, so a phone number
cannot leak into logs through an exception message.
"""
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

class MalformedCallbackError(ValueError):
    """A callback field is missing, has the wrong type or has a bad value.

    The caller must treat the whole callback as unverified: not paid, no
    access. It subclasses ValueError so it is a normal "bad input" error.
    """


# [0-9] is used instead of \d on purpose: in Python, \d also matches digits from other scripts (for example Arabic-Indic digits), 
# and int() would happily convert them. We accept ASCII digits only.
# Up to 9 whole digits and up to 4 decimals; M-Pesa's limits are far lower.
_AMOUNT_TEXT = re.compile(r"[0-9]{1,9}(\.[0-9]{1,4})?")
# Same shape our own STK Push builder enforces for outgoing numbers.
_PHONE = re.compile(r"254[17][0-9]{8}")
# Length 6 to 20 is OUR loose guess (official samples are 10 characters).
# Tighten it after the sandbox experiments.
_RECEIPT = re.compile(r"[A-Za-z0-9]{6,20}")
_TRANSACTION_DATE = re.compile(r"[0-9]{14}")

# Daraja timestamps are Nairobi local time, a fixed UTC+3 offset 
_NAIROBI = timezone(timedelta(hours=3))

def _int_or_str_as_text(raw: object, field: str) -> str:
    """Return raw as text if it is an int or a str; reject everything else.

    bool is rejected explicitly because bool is a subclass of int in Python.
    Floats are rejected so 254708374149.0 is never quietly accepted.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int,str)):
        raise MalformedCallbackError(f"{field} must be an integer or a string")
    return str(raw)


def parse_amount(raw: object) -> int:
    """Return the paid amount as whole shillings, or raise.

    Daraja sends Amount as a float (1.0), and docs elsewhere show decimals, so
    int, float and str are accepted. We convert through the TEXT of the value
    and Decimal, never through float arithmetic, so no binary rounding noise
    can creep in. Money in this system is whole shillings: any fractional
    amount, zero or negative is rejected.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int,float,str)):
        raise MalformedCallbackError("Amount must be a number or a string")
    text = str(raw)
    if not _AMOUNT_TEXT.fullmatch(text):
        raise MalformedCallbackError("Amount is not a plain positive number")
    value = Decimal(text)
    if value != value.to_integral_value():
        raise MalformedCallbackError("Amount is not a whole number of shillings")
    shillings = int(value)
    if shillings < 1:
        raise MalformedCallbackError("Amount must be at least 1 shilling")
    return shillings


def parse_phone(raw: object) -> str:
    """Return the payer's number as '254XXXXXXXXX' text, or raise."""
    text= _int_or_str_as_text(raw, "PhoneNumber")
    if not _PHONE.fullmatch(text):
        raise MalformedCallbackError("PhoneNumber is not a 254 mobile number")
    return text

def parse_receipt(raw: object) -> str:
    """Return the M-Pesa receipt number, or raise."""
    if not isinstance(raw, str) or not _RECEIPT.fullmatch(raw):
        raise MalformedCallbackError("MpesaReceiptNumber is not a valid receipt")
    return raw

def parse_transaction_date(raw: object) -> datetime:
    """Return the transaction time as a timezone-aware datetime, or raise."""
    text= _int_or_str_as_text(raw, "TransactionDate")
    if not _TRANSACTION_DATE.fullmatch(text):
        raise MalformedCallbackError("TransactionDate must be 14 digits (YYYYMMDDHHmmss)")
    try:
        naive = datetime.strptime(text, "%Y%m%d%H%M%S")
    except ValueError:
        raise MalformedCallbackError("TransactionDate is not a real date and time") from None
    return naive.replace(tzinfo=_NAIROBI)