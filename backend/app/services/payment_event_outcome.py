"""Record what we decided to do with a stored payment event (WEZA-50).

record_received_event() writes the audit row and commits it immediately.
This module completes that row once the decision is made. It deliberately
does NOT commit: the outcome must be saved in the same transaction as the
payment change it describes, so the two can never disagree after a crash.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import PaymentEvent
from app.services.payment_event_service import EventOutcome

# payment_events.error_message is String(255).
MAX_ERROR_MESSAGE_CHARS = 255


def mark_event_outcome(
    db: Session,
    *,
    event_id: int,
    outcome: EventOutcome,
    payment_id: int | None = None,
    note: str | None = None,
) -> None:
    """Move a 'received' event to its final outcome. The caller commits.

    note must be OUR OWN short explanation (for staff), never raw Daraja
    text. It is truncated to fit the column.

    Raises:
        ValueError: outcome is RECEIVED, or the event already has a final
            outcome. Rewriting an audit record would hide what happened.
        LookupError: no event with this id exists.
    """
    if outcome is EventOutcome.RECEIVED:
        raise ValueError("RECEIVED is the starting state, not an outcome.")

    event = db.get(PaymentEvent, event_id)
    if event is None:
        raise LookupError(f"payment event {event_id} does not exist")
    if event.processing_status != EventOutcome.RECEIVED.value:
        raise ValueError(
            f"payment event {event_id} already has outcome "
            f"{event.processing_status!r}"
        )

    event.processing_status = outcome.value
    event.payment_id = payment_id
    event.error_message = note[:MAX_ERROR_MESSAGE_CHARS] if note else None
    event.processed_at = datetime.now(UTC)
    db.flush()  # surfaces constraint errors now, inside the caller's transaction