"""Compare a parsed Daraja callback with the payment WE created.

Daraja callbacks are NOT signed, so a well-formed callback is not proof of
anything. The strongest check available is to match it against the pending
payment we stored when we sent the STK Push: the two request IDs, the amount
and the payer's phone must all agree. Anything that does not agree is
rejected, which means NOT PAID and NO ACCESS (fail closed).

This module is pure: no database and no network. The callback route loads
the stored payment, builds an ExpectedPayment from it and calls
verify_callback(). The amount in ExpectedPayment must come from OUR database,
never from the client or from the callback itself.

A SUCCESS_MATCHED verdict means only "this callback matches our payment".
It is not yet permission to grant access: the route still confirms success
with the STK status query first. Payment status and activation status are
separate tracks (see statuses.py).
"""
from dataclasses import dataclass, field
from enum import StrEnum

from app.integrations.mpesa.callback_payload import StkCallback

class CallbackVerdict(StrEnum):
    """Result of comparing a callback with the stored payment."""

    SUCCESS_MATCHED = "success_matched"  # success, and everything agrees
    FAILURE_MATCHED = "failure_matched"  # Safaricom reported failure, IDs agree
    REJECTED_CHECKOUT_ID_MISMATCH = "rejected_checkout_id_mismatch"
    REJECTED_MERCHANT_ID_MISMATCH = "rejected_merchant_id_mismatch"
    REJECTED_INCOMPLETE_SUCCESS = "rejected_incomplete_success"
    REJECTED_AMOUNT_MISMATCH = "rejected_amount_mismatch"
    REJECTED_PHONE_MISMATCH = "rejected_phone_mismatch"

@dataclass(frozen=True)
class ExpectedPayment:
    """What we stored about a payment when we sent its STK Push.

    These values are trusted because they come from our own database.
    Invalid values here are OUR bug, not bad external input, so they raise
    ValueError loudly instead of returning a verdict.
    """
    checkout_request_id: str
    merchant_request_id: str
    amount: int  # whole shillings, never a float
    # repr=False keeps the phone number out of logs and tracebacks.
    phone_number: str = field(repr=False)

    def __post_init__(self) -> None:
        # bool is a subclass of int, so it must be excluded explicitly.
        if (
            isinstance(self.amount, bool)
            or not isinstance(self.amount, int)
            or self.amount < 1
        ):
            raise ValueError("amount must be a whole number of shillings, at least 1")
        for name in ("checkout_request_id", "merchant_request_id", "phone_number"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")


def verify_callback(callback: StkCallback, expected: ExpectedPayment) -> CallbackVerdict:
    """Return how the callback relates to the payment we created.

    Checks run in a fixed order and the first problem wins, so the same bad
    input always gives the same verdict (easier to log, test and support).
    """
    # 1. Identity first. A callback for a different payment is rejected
    #    before we even look at its result, so a fake "failure" cannot
    #    touch someone else's payment.
    if callback.checkout_request_id != expected.checkout_request_id:
        return CallbackVerdict.REJECTED_CHECKOUT_ID_MISMATCH
    if callback.merchant_request_id != expected.merchant_request_id:
        return CallbackVerdict.REJECTED_MERCHANT_ID_MISMATCH

    # 2. A failure carries no amount or phone (Daraja sends them only on
    #    success), so matching IDs is all we can check.
    if not callback.is_success:
        return CallbackVerdict.FAILURE_MATCHED

    # 3. A success must carry its payment details. The parser already
    #    guarantees this; checking again means this function stays safe even
    #    if it is ever called with an object built some other way.
    if (
        callback.amount is None
        or callback.mpesa_receipt_number is None
        or callback.phone_number is None 
    ):
        return CallbackVerdict.REJECTED_INCOMPLETE_SUCCESS

    # 4. Money and payer must match what we stored. Any difference, even an
    #    overpayment, is rejected: we never guess what the customer meant.
    if callback.amount != expected.amount:
        return CallbackVerdict.REJECTED_AMOUNT_MISMATCH
    if callback.phone_number != expected.phone_number:
        return CallbackVerdict.REJECTED_PHONE_MISMATCH

    return CallbackVerdict.SUCCESS_MATCHED