from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.session import WiFiSession
from app.models.payment import Payment
from app.models.package import Package
from app.services.mock_router import activate_wifi_session


def activate_paid_session(db: Session, session_id: int):
    session = db.query(WiFiSession).filter(
        WiFiSession.id == session_id
    ).first()

    if session is None:
        raise ValueError("Session not found")

    if session.status != "PENDING_PAYMENT":
        raise ValueError("Session is not awaiting payment")

    payment = db.query(Payment).filter(
        Payment.id == session.payment_id
    ).first()

    if payment is None or payment.status != "completed":
        raise ValueError("Payment has not been confirmed")

    package = db.query(Package).filter(
        Package.id == session.package_id
    ).first()

    if package is None or package.duration_minutes <= 0:
        raise ValueError("Invalid package duration")

    session.status = "ACTIVATING"
    db.commit()

    try:
        result = activate_wifi_session(session.id)

        if result["status"] != "ACTIVE":
            raise RuntimeError("Wi-Fi activation failed")

        now = datetime.now(timezone.utc)

        session.started_at = now
        session.expires_at = now + timedelta(
            minutes=package.duration_minutes
        )
        session.status = "ACTIVE"

        db.commit()
        db.refresh(session)

        return session

    except Exception:
        db.rollback()
        session = db.query(WiFiSession).filter(
            WiFiSession.id == session_id
        ).first()

        if session:
            session.status = "FAILED"
            db.commit()

        raise
    