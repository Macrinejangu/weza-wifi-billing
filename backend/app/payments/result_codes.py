"""Map Daraja STK ResultCodes to Weza's own failure reasons.

Customers and staff see FailureReason values, never raw Daraja text, so
wording can change without touching stored data.

Fail-closed rules:
  * Only an exact integer 0 (or the string "0") means success.
  * Anything unparseable is NOT success.
  * Any unrecognised non-zero code maps to UNKNOWN and is still a failure.

Verification status (official Daraja docs):
  * VERIFIED: 0 = success, 1032 = cancelled by user. The docs say any other
    code means error or failure.
  * UNVERIFIED (third-party sources, to confirm in the sandbox): 1, 1037, 2001.
    A wrong mapping only changes the message shown, never the money state.
"""

from enum import StrEnum

class FailureReason(StrEnum):
    """Why a payment failed, in our own vocabulary."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    WRONG_PIN = "wrong_pin"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PHONE_BUSY = "phone_busy"  # from request-level errors, not a ResultCode
    SYSTEM_ERROR = "system_error"  # from request-level errors, not a ResultCode
    UNKNOWN = "unknown"

SUCCESS_RESULT_CODE = 0

_REASON_BY_CODE: dict[int, FailureReason] = {
    1: FailureReason.INSUFFICIENT_FUNDS,  # unverified
    1032: FailureReason.CANCELLED,  # verified in official docs
    1037: FailureReason.TIMED_OUT,  # unverified
    2001: FailureReason.WRONG_PIN,  # unverified
}

def parse_result_code(raw: object) -> int | None:
    """Return the ResultCode as an int, or None if it is not a clean integer.

    Daraja documents ResultCode as numeric in callbacks but as a string in
    other tables, so both are accepted. bool is rejected explicitly because
    True would otherwise pass as the integer 1. Floats and padded or signed
    strings are rejected rather than guessed at.
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isascii() and raw.isdigit():
        return int(raw)
    return None

def is_success(raw: object) -> bool:
    """True only when the code is exactly 0. Unparseable input is False."""
    return parse_result_code(raw) == SUCCESS_RESULT_CODE

def failure_reason_for(code: int) -> FailureReason:
    """Map a non-zero ResultCode to a FailureReason (UNKNOWN if unrecognised).

    Raises ValueError for 0 so a success can never be recorded as a failure
    by mistake.
    """
    if code == SUCCESS_RESULT_CODE:
        raise ValueError("ResultCode 0 is a success, not a failure")
    return _REASON_BY_CODE.get(code, FailureReason.UNKNOWN)