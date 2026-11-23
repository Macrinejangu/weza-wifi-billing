"""Builds the JSON body of an STK Push (M-Pesa Express) request.

Pure functions, no network. Every rule about what Daraja will accept lives here,
so a bad value fails before anything is sent to a customer's phone.

Field meanings are from Safaricom's M-Pesa Express request table:
  * TransactionType: "CustomerPayBillOnline" for PayBill numbers and
    "CustomerBuyGoodsOnline" for Till numbers.
  * PartyA: the phone number sending money (2547XXXXXXXX).
  * PartyB: the organisation receiving the funds.
  * PhoneNumber: the number that receives the USSD prompt.

Not yet verified: whether a till's BusinessShortCode is a separate store number
(one third-party source says so; Safaricom's table does not). Test in the
sandbox or confirm with Safaricom before any production use.
"""
import re
from app.config import ACCOUNT_PAYBILL, ACCOUNT_TILL, DarajaSettings
from app.payments.daraja_password import build_password

# Daraja needs a different TransactionType for each kind of business number.
_TRANSACTION_TYPES = {
    ACCOUNT_PAYBILL: "CustomerPayBillOnline",
    ACCOUNT_TILL: "CustomerBuyGoodsOnline",
}

MIN_AMOUNT_SHILLINGS = 1 # Daraja's documented minimum
MAX_ACCOUNT_REFERENCE_LENGTH =12
MAX_TRANSACTION_DESC_LENGTH=13

# [0-9], not \d: in Python, \d also matches digits from other scripts.
# The docs show 2547XXXXXXXX only. We also allow 2541, which must be tested in
# the sandbox before we rely on it.

_MSISDN = re.compile(r"254[17][0-9]{8}")
_SHORTCODE = re.compile(r"[0-9]{5,6}")  # "5 to 6 digits" per Safaricom
_DIGITS = re.compile(r"[0-9]+")

def build_stk_push_body(
        settings: DarajaSettings,
        *,
        amount: int,
        phone_number: str,
        account_reference: str,
        description: str,
        timestamp: str,
) -> dict[str, str | int]:
    """Build the JSON body for an STK Push request.

    `timestamp` is used for BOTH the Timestamp field and the Password, because
    Daraja rejects the request if they disagree. The caller generates it once.

    The amount must come from OUR database, never from the client. It must be
    a whole number of shillings. Values Daraja would reject, or that we would
    have to silently shorten, raise ValueError here instead.

    The returned dict contains the Password, which is base64 of the passkey and
    therefore a secret. Never log it.
    """
    transaction_type = _TRANSACTION_TYPES.get(settings.account_type)
    if transaction_type is None:
        raise ValueError("Unknown Daraja account type.")
    # Fail closed: never fall back to the shortcode as the receiving party.
    if not settings.party_b or _DIGITS.fullmatch(settings.party_b) is None:
        raise ValueError("party_b must be set and contain digits only.")
    if _SHORTCODE.fullmatch(settings.shortcode) is None:
        raise ValueError("shortcode must be 5 to 6 digits.")
    # bool first: True is an int in Python and would otherwise pass as 1.
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("amount must be a whole number of shillings.")
    if amount < MIN_AMOUNT_SHILLINGS:
        raise ValueError(f"amount must be at least {MIN_AMOUNT_SHILLINGS}.")
    if _MSISDN.fullmatch(phone_number) is None:
        raise ValueError("phone_number must be in 254XXXXXXXXX form.")
    if not 1 <= len(account_reference) <= MAX_ACCOUNT_REFERENCE_LENGTH:
        raise ValueError(f"account_reference must be 1 to {MAX_ACCOUNT_REFERENCE_LENGTH} characters.")
    if not 1 <= len(description) <= MAX_TRANSACTION_DESC_LENGTH:
        raise ValueError(f"description must be 1 to {MAX_TRANSACTION_DESC_LENGTH} characters.")

    return {
        "BusinessShortCode": settings.shortcode,
        "Password": build_password(settings.shortcode, settings.passkey, timestamp),
        "Timestamp": timestamp,
        "TransactionType": transaction_type,
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.party_b,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": description,
    }