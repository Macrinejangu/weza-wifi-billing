"""Audit trail for incoming M-Pesa callbacks and status queries (WEZA-50).

Every message from Safaricom, valid or not, gets one payment_events row
BEFORE we try to understand it. The row is committed on its own so it
survives even if verification or settlement crashes afterwards: the audit
record must never depend on the work it is auditing.

Duplicates get their own rows on purpose (the table has no unique rule), so
staff can see exactly how many times a callback arrived.
"""
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.models import PaymentEvent

# Column limits in payment_events.
MAX_CHECKOUT_ID_CHARS = 100
INT32_MAX = 2**31 - 1
INT32_MIN = -(2**31)


class EventSource(StrEnum):
    """Where the message came from. Matches ck_events_source."""

    CALLBACK = "callback"
    QUERY = "query"


class EventOutcome(StrEnum):
    """What we did with the message. Matches ck_events_processing_status.

    Every row starts as RECEIVED and is moved to a final outcome later.
    """

    RECEIVED = "received"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    UNMATCHED = "unmatched"


def safe_checkout_request_id(value: Any) -> str | None:
    """Return the id only if it fits its column; otherwise None.

    Callbacks are not signed, so this value comes from an untrusted sender.
    An oversized or odd value stored as-is would make the INSERT fail. None
    is stored instead; the full body is still kept in the payload column.
    """
    if not isinstance(value, str):
        return None
    # isprintable() is False for NUL, control characters and lone surrogates,
    # all of which PostgreSQL text columns can reject.
    if not value.strip() or not value.isprintable():
        return None
    if len(value) > MAX_CHECKOUT_ID_CHARS:
        return None
    return value


def safe_result_code(value: Any) -> int | None:
    """Return the code only if it is a real integer that fits the column.

    A bool is excluded: Python treats True as 1, which would record a
    meaningless result code. Numbers sent as strings are not converted here;
    the callback parser decides what a result code means.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if not INT32_MIN <= value <= INT32_MAX:
        return None
    return value


def record_received_event(
    db: Session,
    *,
    source: EventSource,
    payload: dict[str, Any],
    checkout_request_id: Any = None,
    result_code: Any = None,
) -> int:
    """Save and COMMIT a 'received' event row. Returns its id.

    payload must already be JSONB-safe (see build_event_payload). The commit
    happens here, not in the caller, so the audit row is permanent before any
    later step can fail. Database errors are not caught: if we cannot record
    the message, the caller must not pretend it was handled.
    """
    event = PaymentEvent(
        source=source.value,
        payload=payload,
        checkout_request_id=safe_checkout_request_id(checkout_request_id),
        result_code=safe_result_code(result_code),
        processing_status=EventOutcome.RECEIVED.value,
    )
    db.add(event)
    db.flush()  # assigns event.id without expiring the object first
    event_id = event.id
    db.commit()
    return event_id