"""Interpret Daraja's STK Push Query reply.

The status query asks Safaricom directly what happened to a payment. It is
how we recover a payment whose callback never arrived or was rejected, and
how a matching success callback is confirmed before access is granted.

The outcome has THREE values, never a boolean, because "I could not tell" is
a real answer and must never be confused with "failed":
    PAID     Safaricom reports ResultCode 0 for OUR CheckoutRequestID.
    FAILED   Safaricom reports a non-zero ResultCode for it (final).
    UNKNOWN  anything else: odd shapes, errors, a still-processing reply, a
             reply about a different payment. Keep the payment pending.

The reply carries no amount, phone or receipt number, so PAID proves that
the payment happened but not how much. The caller must not treat it as
permission to skip the amount and phone checks when it has a callback.

This module is pure: no network and no database.
"""
from dataclasses import dataclass
from enum import StrEnum

from app.payments.result_codes import (
    SUCCESS_RESULT_CODE,
    FailureReason,
    failure_reason_for,
    is_success,
    parse_result_code,
)

# Daraja documents 1024 as the maximum length of ResultDesc.
_MAX_RESULT_DESC_LENGTH = 1024

class StkQueryOutcome(StrEnum):
    """What the status query told us about a payment."""
    PAID = "paid"
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class StkQueryResult:
    """The interpreted outcome of one status query.

    The combinations are checked on creation so an impossible result, such
    as PAID with a failure reason, can never exist.
    """
    outcome: StkQueryOutcome
    result_code: int | None = None
    failure_reason: FailureReason | None = None
    # Kept for the audit trail only. Customer messages use failure_reason,
    # never this raw text.
    result_desc: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is StkQueryOutcome.PAID:
            valid = self.result_code == SUCCESS_RESULT_CODE and self.failure_reason is None
        elif self.outcome is StkQueryOutcome.FAILED:
            valid =(
                self.result_code is not None
                and self.result_code != SUCCESS_RESULT_CODE
                and self.failure_reason is not None
            )
        else:
            valid = self.result_code is None and self.failure_reason is None
        if not valid:
            raise ValueError("inconsistent STK query result")


_UNKNOWN = StkQueryResult(StkQueryOutcome.UNKNOWN)


def interpret_stk_query_response(
        body: object, expected_checkout_request_id: str
) -> StkQueryResult:
    """Turn a decoded query reply (HTTP 200) into an StkQueryResult.

    Never raises for bad Daraja data: that is UNKNOWN. It raises ValueError
    only if OUR caller passes an empty expected ID, which is our own bug.
    """
    if not isinstance(expected_checkout_request_id, str) or not expected_checkout_request_id:
        raise ValueError("expected_checkout_request_id must be a non-empty string")

    if not isinstance(body, dict):
        return _UNKNOWN

    # ResponseCode says whether Daraja processed the QUERY itself. Only 0 or
    # "0" counts; the result of the payment is a separate field below.
    if not is_success(body.get("ResponseCode")):
        return _UNKNOWN

    # A reply about another payment must never settle this one.
    if body.get("CheckoutRequestID") != expected_checkout_request_id:
        return _UNKNOWN

    code = parse_result_code(body.get("ResultCode"))
    if code is None:
        return _UNKNOWN

    raw_desc = body.get("ResultDesc")
    desc = (
        raw_desc
        if isinstance(raw_desc, str) and len(raw_desc) <= _MAX_RESULT_DESC_LENGTH
        else None
    )

    if code == SUCCESS_RESULT_CODE:
        return StkQueryResult(StkQueryOutcome.PAID, result_code=code, result_desc=desc)
    return StkQueryResult(
        StkQueryOutcome.FAILED,
        result_code=code,
        failure_reason=failure_reason_for(code),
        result_desc=desc,
    )