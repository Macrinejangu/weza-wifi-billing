"""Turn a verified payment into network access, without ever undoing the payment.

Flow position: this runs AFTER settle_payment has committed a verified
success. It is the only place that connects the payment track to the
activation track (see app/payments/statuses.py).

Safety rules enforced here:
* The caller must have committed the settlement first. Router calls must
  never run inside the settlement transaction or while a payment row is
  locked, because a slow router would block other callbacks.
* This function never raises. M-Pesa retries callbacks that fail, and a
  fulfilment problem must not make the payment look unpaid. The outcome is
  returned as a value and recorded on the session and attempt rows, where
  staff retry (WEZA-63) can find it.
* It never changes the payment status. Payment success is final here.
* One session per payment and one in-flight attempt per session are enforced
  by the database (UNIQUE sessions.payment_id and the partial unique index
  uq_one_started_attempt), not by checks in this module.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models import WiFiSession
from app.payments.statuses import ActivationStatus
from app.services.session_service import activate_session, create_session

logger = logging.getLogger(__name__)

# session_service stores session.status as plain strings and has no enum.
# Kept private here so we do not repeat a magic string in several places.
_SESSION_ACTIVATING = "ACTIVATING"


class FulfilmentOutcome(StrEnum):
    """What happened when we tried to give a paid customer access."""

    ACTIVATED = "activated"  # Router confirmed access; the timer has started
    ACTIVATION_FAILED = "activation_failed"  # Recorded as failed; staff can retry
    ACTIVATION_UNCONFIRMED = "activation_unconfirmed"  # Router may have applied it
    NOT_ATTEMPTED = "not_attempted"  # A precondition failed; no router call made
    UNEXPECTED_ERROR = "unexpected_error"  # Our own bug or a database error


@dataclass(frozen=True)
class FulfilmentResult:
    """Outcome plus identifiers, so callers and logs never need the ORM objects."""

    payment_id: int
    session_id: int | None
    outcome: FulfilmentOutcome


def _classify(session: WiFiSession) -> FulfilmentOutcome:
    """Read the outcome from the session that activate_session returned."""
    if session.activation_status == ActivationStatus.SUCCEEDED:
        return FulfilmentOutcome.ACTIVATED
    if session.activation_status == ActivationStatus.FAILED:
        return FulfilmentOutcome.ACTIVATION_FAILED
    # activate_session only returns while ACTIVATING on its "router did not
    # answer clearly" path. Fail closed: no access is assumed, and the attempt
    # row is marked unconfirmed so it can be reconciled later.
    if session.status == _SESSION_ACTIVATING:
        return FulfilmentOutcome.ACTIVATION_UNCONFIRMED
    return FulfilmentOutcome.UNEXPECTED_ERROR


def fulfil_payment(
    db: Session,
    payment_id: int,
    router: Callable[[int], dict] | None = None,
) -> FulfilmentResult:
    """Create the session for a successful payment and request activation.

    Safe to call repeatedly for the same payment: create_session returns the
    existing session, and activate_session returns early once it has
    succeeded, so a repeat makes no second router call.

    `router` is passed straight through so tests can fake the network.
    """
    session_id: int | None = None
    try:
        session = create_session(db, payment_id)
        session_id = session.id
        session = activate_session(db, session_id, router=router)
        outcome = _classify(session)
    except (LookupError, ValueError) as error:
        # session_service signals "payment missing/unconfirmed" and "session in
        # the wrong state" with these built-ins. We only get here after a
        # verified, committed success, so this is never normal: log at ERROR.
        # Caveat: KeyError is a LookupError, so a real bug can land here too.
        logger.error(
            "fulfilment precondition failed payment_id=%s error_type=%s error=%s",
            payment_id,
            type(error).__name__,
            error,
        )
        outcome = FulfilmentOutcome.NOT_ATTEMPTED
    except Exception:
        # Deliberate last-resort boundary: whatever happens, the callback
        # reply must not change. The traceback goes to the logs only.
        logger.exception(
            "fulfilment crashed payment_id=%s session_id=%s", payment_id, session_id
        )
        outcome = FulfilmentOutcome.UNEXPECTED_ERROR
    finally:
        # Ends any open transaction. activate_session's early return (already
        # succeeded) commits nothing, so it would otherwise keep the session
        # row locked. After a normal commit this is a harmless no-op.
        db.rollback()

    log = logger.info if outcome is FulfilmentOutcome.ACTIVATED else logger.warning
    log(
        "fulfilment finished payment_id=%s session_id=%s outcome=%s",
        payment_id,
        session_id,
        outcome.value,
    )
    return FulfilmentResult(payment_id, session_id, outcome)