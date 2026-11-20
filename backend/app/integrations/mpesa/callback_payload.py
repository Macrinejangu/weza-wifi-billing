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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.payments.result_codes import SUCCESS_RESULT_CODE, parse_result_code

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

def _int_or_str_as_text(raw: object, field_name: str) -> str:
    """Return raw as text if it is an int or a str; reject everything else.

    bool is rejected explicitly because bool is a subclass of int in Python.
    Floats are rejected so 254708374149.0 is never quietly accepted.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int,str)):
        raise MalformedCallbackError(f"{field_name} must be an integer or a string")
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


# ---------- The callback envelope ----------

# IDs in the official samples use letters, digits, "_" and "-". The 100-char
# bound stops absurdly long strings reaching our database queries.
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,100}")
# The Daraja docs give 1024 as the maximum length of ResultDesc.
_MAX_RESULT_DESC_LENGTH = 1024
# A real success carries 4 to 5 items. This cap stops a huge array being
# walked just to be rejected.
_MAX_METADATA_ITEMS = 20

@dataclass(frozen=True)
class StkCallback:
    """A validated STK Push callback.

    The four payment fields are None on a failure, because Daraja sends
    CallbackMetadata only on success. On a success all four are set.

    frozen=True makes the object immutable, so nothing can change a verified
    value between parsing and comparing it with our stored payment.
    """

    merchant_request_id: str
    checkout_request_id: str
    result_code: int
    result_desc: str
    amount: int | None
    mpesa_receipt_number: str | None
    # repr=False keeps the payer's number out of logs and tracebacks, which
    # print repr(self) when this object is logged by mistake.
    phone_number: str | None = field(repr=False)
    transaction_date: datetime | None

    @property
    def is_success(self) -> bool:
        """True only for ResultCode 0. This says nothing about the amount or
        phone matching; step 4's verification does that."""
        return self.result_code == SUCCESS_RESULT_CODE

    

def _require_object(value: object, what:str) -> dict:
    """Return value if it is a JSON object (a dict), else raise."""
    if not isinstance(value, dict):
        raise MalformedCallbackError(f"{what} must be a JSON object")
    return value

def _parse_request_id(raw: object, field_name: str) -> str:
    """Return a Daraja request ID, or raise."""
    if not isinstance(raw, str) or not _REQUEST_ID.fullmatch(raw):
        raise MalformedCallbackError(f"{field_name} is not a valid request ID")
    return raw

def _metadata_values(stk_callback: dict) -> dict[str, object]:
    """Flatten CallbackMetadata.Item into {Name: Value}, or raise.

    Daraja sends a list of {"Name": ..., "Value": ...} objects. Some items,
    such as Balance, can arrive without a Value, so a missing Value becomes
    None here and only matters if we actually require that item.
    """
    metadata = _require_object(
        stk_callback.get("CallbackMetadata"), "CallbackMetadata"
    )
    items = metadata.get("Item")
    if not isinstance(items, list) or len(items) > _MAX_METADATA_ITEMS:
        raise MalformedCallbackError("CallbackMetadata.Item is not a usable list")

    values: dict[str,object] = {}
    for item in items:
        item = _require_object(item, "CallbackMetadata item")
        name = item.get("Name")
        if not isinstance(name, str):
            raise MalformedCallbackError("A metadata item has no valid Name")
        if name in values:
            # Two values for one name: we cannot know which one is true.
            raise MalformedCallbackError("A metadata item appears twice")
        values[name] = item.get("Value")
    return values

def parse_stk_callback(payload: object) -> StkCallback:
    """Validate a raw callback body and return an StkCallback, or raise.

    `payload` is the decoded JSON exactly as received. Any problem raises
    MalformedCallbackError and the caller must treat the callback as
    unverified. A valid result is still NOT proof of payment: it must also
    match a payment we created.
    """
    root = _require_object(payload, "The callback body")
    body = _require_object(root.get("Body"), "Body")
    stk_callback = _require_object(body.get("stkCallback"), "stkCallback")

    merchant_request_id = _parse_request_id(stk_callback.get("MerchantRequestID"), "MerchantRequestID")
    checkout_request_id = _parse_request_id(stk_callback.get("CheckoutRequestID"), "CheckoutRequestID")

    result_code = parse_result_code(stk_callback.get("ResultCode"))
    if result_code is None:
        raise MalformedCallbackError("ResultCode is not a clean integer")

    result_desc = stk_callback.get("ResultDesc")
    if not isinstance(result_desc, str) or len(result_desc) > _MAX_RESULT_DESC_LENGTH:
        raise MalformedCallbackError("ResultDesc is missing or too long")

    if result_code != SUCCESS_RESULT_CODE:
        # A failure carries no payment details. We deliberately do not read
        # CallbackMetadata at all, so junk there cannot turn a clear failure
        # into a rejected callback.
        return StkCallback(
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
            result_code=result_code,
            result_desc=result_desc,
            amount=None,
            mpesa_receipt_number=None,
            phone_number=None,
            transaction_date=None,
        )
    # A success without all four details cannot be verified, so it is
    # rejected. A genuine payment behind such a callback is recovered later
    # by the STK status query
    values = _metadata_values(stk_callback)
    return StkCallback(
        merchant_request_id=merchant_request_id,
        checkout_request_id=checkout_request_id,
        result_code=result_code,
        result_desc=result_desc,
        amount=parse_amount(values.get("Amount")),
        mpesa_receipt_number=parse_receipt(values.get("MpesaReceiptNumber")),
        phone_number=parse_phone(values.get("PhoneNumber")),
        transaction_date=parse_transaction_date(values.get("TransactionDate")),
    )