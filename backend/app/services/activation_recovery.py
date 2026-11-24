"""Find paid customers who are not connected, and payments that never settled.

WEZA-63, piece 2: a read-only finder. It never changes a row and never calls
the router or Daraja. Each unresolved case gets one reason and one suggested
action, so staff see what is wrong and what to do about it.

Healthy cases are excluded in SQL (an ACTIVE session, or an EXPIRED session
that really had access), so the query stays cheap as history grows.

Only error CODES from activation attempts are exposed, never raw router text.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session

from app.models import ActivationAttempt, Payment, Purchase, WiFiSession
from app.services.router import RouterActivationUnconfirmed

# A payment settled this recently may still be mid-fulfilment: not a problem yet.
DEFAULT_GRACE = timedelta(minutes=5)
# A pending prompt older than this has probably lost its callback.
DEFAULT_PENDING_AFTER = timedelta(minutes=10)
MAX_LIMIT = 100


class RecoveryReason(StrEnum):
    PAID_NO_SESSION = "paid_no_session"
    NOT_STARTED = "not_started"
    FAILED = "failed"
    UNCONFIRMED = "unconfirmed"
    NEEDS_DEVICE = "needs_device"
    INCONSISTENT_STATE = "inconsistent_state"
    PENDING_STALE = "pending_stale"


class RecoveryAction(StrEnum):
    RETRY_ACTIVATION = "retry_activation"
    CHECK_PAYMENT_STATUS = "check_payment_status"
    STAFF_REVIEW = "staff_review"


_ACTION_FOR_REASON = {
    RecoveryReason.PAID_NO_SESSION: RecoveryAction.RETRY_ACTIVATION,
    RecoveryReason.NOT_STARTED: RecoveryAction.RETRY_ACTIVATION,
    RecoveryReason.FAILED: RecoveryAction.RETRY_ACTIVATION,
    RecoveryReason.UNCONFIRMED: RecoveryAction.RETRY_ACTIVATION,
    RecoveryReason.NEEDS_DEVICE: RecoveryAction.STAFF_REVIEW,
    RecoveryReason.INCONSISTENT_STATE: RecoveryAction.STAFF_REVIEW,
    RecoveryReason.PENDING_STALE: RecoveryAction.CHECK_PAYMENT_STATUS,
}


@dataclass(frozen=True)
class RecoveryCase:
    """One unresolved case, safe to show to staff."""

    payment_id: int
    purchase_id: int
    user_id: int
    session_id: int | None
    reason: RecoveryReason
    action: RecoveryAction
    payment_status: str
    session_status: str | None
    activation_status: str | None
    last_error_code: str | None
    paid_at: datetime | None
    waiting_since: datetime | None
    age_seconds: int


def classify_case(
    *,
    payment_status: str,
    paid_at: datetime | None,
    initiated_at: datetime | None,
    session_status: str | None,
    activation_status: str | None,
    session_started_at: datetime | None,
    latest_error_code: str | None,
    has_device: bool,
    require_device: bool,
    now: datetime,
    grace: timedelta = DEFAULT_GRACE,
    pending_after: timedelta = DEFAULT_PENDING_AFTER,
) -> RecoveryReason | None:
    """Pure rule: return the reason a case is unresolved, or None if it is fine."""
    if payment_status == "pending":
        if initiated_at is not None and now - initiated_at >= pending_after:
            return RecoveryReason.PENDING_STALE
        return None

    if payment_status != "successful":
        return None  # failed and expired payments are not paid cases

    if paid_at is None:
        return RecoveryReason.INCONSISTENT_STATE  # a verified payment always has paid_at

    needs_device = require_device and not has_device
    within_grace = now - paid_at < grace

    if session_status is None:
        if within_grace:
            return None
        return RecoveryReason.NEEDS_DEVICE if needs_device else RecoveryReason.PAID_NO_SESSION

    if activation_status == "succeeded":
        if session_status == "ACTIVE":
            return None
        if session_status == "EXPIRED" and session_started_at is not None:
            return None
        return RecoveryReason.INCONSISTENT_STATE

    if session_status == "ACTIVATING":
        if activation_status == "waiting" and latest_error_code == RouterActivationUnconfirmed.__name__:
            return RecoveryReason.UNCONFIRMED
        return RecoveryReason.INCONSISTENT_STATE

    if session_status == "PAYMENT_CONFIRMED" and activation_status == "not_started":
        if within_grace:
            return None
        return RecoveryReason.NEEDS_DEVICE if needs_device else RecoveryReason.NOT_STARTED

    if session_status == "FAILED" and activation_status == "failed":
        return RecoveryReason.NEEDS_DEVICE if needs_device else RecoveryReason.FAILED

    return RecoveryReason.INCONSISTENT_STATE


def find_unresolved_cases(
    db: Session,
    *,
    now: datetime | None = None,
    require_device: bool = False,
    grace: timedelta = DEFAULT_GRACE,
    pending_after: timedelta = DEFAULT_PENDING_AFTER,
    limit: int = 50,
    offset: int = 0,
) -> list[RecoveryCase]:
    """List unresolved cases, oldest payment first."""
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if offset < 0:
        raise ValueError("offset must not be negative")
    now = _aware(now)

    stale_pending = and_(
        Payment.status == "pending",
        _initiated_at() <= now - pending_after,
    )
    session_is_resolved = and_(
        WiFiSession.activation_status == "succeeded",
        or_(
            WiFiSession.status == "ACTIVE",
            and_(WiFiSession.status == "EXPIRED", WiFiSession.started_at.is_not(None)),
        ),
    )
    unresolved_paid = and_(
        Payment.status == "successful",
        or_(WiFiSession.id.is_(None), not_(session_is_resolved)),
    )
    return _load_cases(
        db, or_(stale_pending, unresolved_paid), now=now, require_device=require_device,
        grace=grace, pending_after=pending_after, limit=limit, offset=offset,
    )


def get_case(
    db: Session,
    payment_id: int,
    *,
    now: datetime | None = None,
    require_device: bool = False,
    grace: timedelta = DEFAULT_GRACE,
    pending_after: timedelta = DEFAULT_PENDING_AFTER,
) -> RecoveryCase | None:
    """The unresolved case for one payment, or None if it is resolved or unknown."""
    cases = _load_cases(
        db, Payment.id == payment_id, now=_aware(now), require_device=require_device,
        grace=grace, pending_after=pending_after, limit=1, offset=0,
    )
    return cases[0] if cases else None


def _aware(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now


def _initiated_at():
    return func.coalesce(Payment.initiated_at, Payment.created_at)


def _load_cases(
    db: Session, where, *, now: datetime, require_device: bool,
    grace: timedelta, pending_after: timedelta, limit: int, offset: int,
) -> list[RecoveryCase]:
    latest_error_code = (
        select(ActivationAttempt.error_code)
        .where(ActivationAttempt.session_id == WiFiSession.id)
        .order_by(ActivationAttempt.attempt_number.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            Payment.id.label("payment_id"),
            Payment.purchase_id.label("purchase_id"),
            Payment.status.label("payment_status"),
            Payment.paid_at.label("paid_at"),
            _initiated_at().label("initiated_at"),
            Purchase.user_id.label("user_id"),
            Purchase.device_mac_address.label("device_mac_address"),
            WiFiSession.id.label("session_id"),
            WiFiSession.status.label("session_status"),
            WiFiSession.activation_status.label("activation_status"),
            WiFiSession.started_at.label("session_started_at"),
            latest_error_code.label("latest_error_code"),
        )
        .join(Purchase, Purchase.id == Payment.purchase_id)
        .outerjoin(WiFiSession, WiFiSession.payment_id == Payment.id)
        .where(where)
        .order_by(Payment.id)
        .limit(limit)
        .offset(offset)
    ).mappings().all()

    cases: list[RecoveryCase] = []
    for row in rows:
        reason = classify_case(
            payment_status=row["payment_status"],
            paid_at=row["paid_at"],
            initiated_at=row["initiated_at"],
            session_status=row["session_status"],
            activation_status=row["activation_status"],
            session_started_at=row["session_started_at"],
            latest_error_code=row["latest_error_code"],
            has_device=bool(row["device_mac_address"]),
            require_device=require_device,
            now=now,
            grace=grace,
            pending_after=pending_after,
        )
        if reason is None:
            continue
        waiting_since = row["paid_at"] or row["initiated_at"]
        cases.append(RecoveryCase(
            payment_id=row["payment_id"],
            purchase_id=row["purchase_id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            reason=reason,
            action=_ACTION_FOR_REASON[reason],
            payment_status=row["payment_status"],
            session_status=row["session_status"],
            activation_status=row["activation_status"],
            last_error_code=row["latest_error_code"],
            paid_at=row["paid_at"],
            waiting_since=waiting_since,
            age_seconds=max(0, int((now - waiting_since).total_seconds())) if waiting_since else 0,
        ))
    return cases
