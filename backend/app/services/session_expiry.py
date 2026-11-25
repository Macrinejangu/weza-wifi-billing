import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Subscription, WiFiSession
from app.services.access_auth import MikroTikAuthenticator, get_access_authenticator
from app.services.router import expire_hotspot_grant
from app.services.session_service import lock_hotspot_device

logger = logging.getLogger(__name__)


def expire_due_sessions(db: Session, *, limit: int = 50, now: datetime | None = None) -> int:
    """End elapsed grants. Leave unconfirmed router changes eligible for retry."""
    now = now or datetime.now(UTC)
    if limit < 1 or now.tzinfo is None:
        raise ValueError("Expiry needs a positive limit and a timezone-aware clock")
    deadline = func.coalesce(Subscription.end_date, WiFiSession.expires_at)
    considered = []
    expired = 0
    for _ in range(limit):
        session = db.scalar(
            select(WiFiSession)
            .outerjoin(Subscription, Subscription.id == WiFiSession.subscription_id)
            .where(
                deadline <= now,
                WiFiSession.ended_at.is_(None),
                WiFiSession.status.in_(("ACTIVE", "ACTIVATING", "PAYMENT_CONFIRMED", "FAILED")),
                WiFiSession.id.not_in(considered),
            )
            .order_by(deadline, WiFiSession.id)
            .limit(1)
            .with_for_update(of=WiFiSession, skip_locked=True)
        )
        if session is None:
            db.rollback()
            break

        session_id = session.id
        considered.append(session_id)
        session.disconnection_requested_at = now
        try:
            if session.router_grant_id:
                if not isinstance(get_access_authenticator(), MikroTikAuthenticator):
                    raise RuntimeError("The expiry worker needs the test router configuration")
                lock_hotspot_device(db, session.device_mac_address)
                expire_hotspot_grant(
                    session.device_mac_address,
                    session.router_grant_id,
                    router_identity=session.router_identity,
                    router_server_name=session.router_server_name,
                )
            elif session.device_mac_address and not (session.payment.raw_callback or {}).get("mock"):
                raise RuntimeError("Older router session needs manual expiry review")
        except Exception as error:
            session.disconnection_status = "failed"
            session.disconnection_error = type(error).__name__
            logger.warning("Expiry pending for session %s: %s", session_id, type(error).__name__)
        else:
            session.disconnection_status = "succeeded"
            session.disconnection_error = None
            session.disconnected_at = now
            session.status = "EXPIRED"
            session.ended_at = now
            if session.subscription is not None:
                session.subscription.status = "expired"
            expired += 1
        db.commit()
    return expired
