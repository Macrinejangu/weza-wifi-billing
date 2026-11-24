from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import WiFiSession
from app.services.access_auth import (
    MikroTikAuthenticator,
    get_access_authenticator,
)


def expire_due_sessions(
    db: Session,
    now: datetime | None = None,
    limit: int = 100,
) -> dict:
    """
    Disconnect due sessions and expire only after confirmed disconnection.

    Failed disconnections remain ACTIVE and can be retried by a later cycle.
    Row locks prevent concurrent workers from processing the same sessions.
    """
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    current_time = now or datetime.now(timezone.utc)

    if current_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    summary = {
        "processed": 0,
        "expired": 0,
        "failed": 0,
    }

    due_sessions = (
        db.query(WiFiSession)
        .filter(
            WiFiSession.status == "ACTIVE",
            WiFiSession.expires_at.isnot(None),
            WiFiSession.expires_at <= current_time,
            WiFiSession.disconnection_status.in_(
                ("not_started", "failed")
            ),
        )
        .order_by(WiFiSession.expires_at.asc(), WiFiSession.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
        .all()
    )

    if not due_sessions:
        return summary

    for session in due_sessions:
        summary["processed"] += 1

        session.disconnection_status = "waiting"
        session.disconnection_requested_at = current_time
        session.disconnection_error = None

        try:
            authenticator = get_access_authenticator()

            payment_origin = (
                session.payment.raw_callback
                if session.payment is not None
                else None
            )

            if (
                isinstance(authenticator, MikroTikAuthenticator)
                and isinstance(payment_origin, dict)
                and payment_origin.get("mock") is True
            ):
                raise RuntimeError(
                    "Mock payment cannot trigger disconnection "
                    "on a live MikroTik router"
                )

            result = authenticator.disconnect_device(
                session_id=session.id,
                mac_address=session.device_mac_address,
                server_name=session.router_server_name,
                router_identity=session.router_identity,
                router_session_id=session.router_session_id,
            )

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Access provider returned an invalid disconnection result"
                )

            if result.get("status") != "DISCONNECTED":
                raise RuntimeError(
                    "Access provider did not confirm disconnection"
                )

        except Exception as error:
            session.disconnection_status = "failed"
            session.disconnection_error = str(error)[:255]
            summary["failed"] += 1

        else:
            session.disconnection_status = "succeeded"
            session.disconnected_at = current_time
            session.disconnection_error = None

            session.status = "EXPIRED"
            session.ended_at = current_time

            summary["expired"] += 1

    # Keep the row locks until the router outcomes and database changes
    # are committed together. If the transaction rolls back after a
    # successful router disconnect, the next attempt is safe because
    # the MikroTik disconnection operation is idempotent.
    db.commit()

    return summary
