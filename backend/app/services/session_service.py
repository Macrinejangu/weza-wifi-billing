from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models import ActivationAttempt, Payment, WiFiSession
from app.services.mock_router import activate_wifi_session


def create_session(db: Session, payment_id: int, mac: str | None = None, ip: str | None = None) -> WiFiSession:
    """One session per payment, and only for a payment M-Pesa confirmed."""
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise LookupError("Payment not found")
    if payment.status != "successful":
        raise ValueError("Payment has not been confirmed")
    session = db.query(WiFiSession).filter_by(payment_id=payment.id).first()
    if session is None:
        session = WiFiSession(
            user_id=payment.purchase.user_id, package_id=payment.purchase.package_id, payment_id=payment.id,
            device_mac_address=mac, device_ip_address=ip, status="PAYMENT_CONFIRMED",
        )
        db.add(session)
        db.commit()
    return session


def activate_session(db: Session, session_id: int, router: Callable[[int], dict] = activate_wifi_session) -> WiFiSession:
    """Ask the router to switch access on. The timer starts only if the router confirms."""
    session = db.get(WiFiSession, session_id)
    if session is None:
        raise LookupError("Session not found")
    if session.activation_status == "succeeded":
        return session  # already active
    if session.status not in ("PAYMENT_CONFIRMED", "FAILED"):
        raise ValueError(f"Cannot activate a session that is {session.status}")

    now = datetime.now(timezone.utc)
    attempt = ActivationAttempt(session_id=session.id, attempt_number=len(session.attempts) + 1)
    session.status, session.activation_status = "ACTIVATING", "waiting"
    session.activation_requested_at, session.failure_reason = now, None
    db.add(attempt)
    db.commit()

    try:
        if router(session.id).get("status") != "ACTIVE":
            raise RuntimeError("Router did not confirm activation")
    except Exception as error:  # the customer's paid time is untouched: no timer was started
        attempt.status, attempt.error_code, attempt.error_message = "failed", type(error).__name__, str(error)[:255]
        session.status, session.activation_status, session.failure_reason = "FAILED", "failed", str(error)[:255]
    else:
        attempt.status = "succeeded"
        session.status, session.activation_status = "ACTIVE", "succeeded"
        session.started_at = now
        session.expires_at = now + timedelta(minutes=session.payment.purchase.duration_minutes)
    attempt.completed_at = now
    db.commit()
    return session
