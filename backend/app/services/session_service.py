from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models import ActivationAttempt, Payment, WiFiSession
from app.services.access_auth import (
    activate_access_device,
    get_access_authenticator,
    MikroTikAuthenticator,
)
from app.services.router import RouterActivationUnconfirmed, activate_hotspot_device


def create_session(
    db: Session,
    payment_id: int,
    mac: str | None = None,
    ip: str | None = None,
) -> WiFiSession:
    """One session per payment, and only for a payment M-Pesa confirmed."""
    payment = db.get(Payment, payment_id, with_for_update=True)

    if payment is None:
        raise LookupError("Payment not found")

    if payment.status != "successful":
        raise ValueError("Payment has not been confirmed")

    purchase = payment.purchase
    if purchase.device_mac_address:
        if (mac is not None and mac != purchase.device_mac_address) or (
            ip is not None and ip != purchase.device_ip_address
        ):
            raise ValueError("Session device does not match the purchase")
        mac, ip = purchase.device_mac_address, purchase.device_ip_address

    session = db.query(WiFiSession).filter_by(payment_id=payment.id).first()

    if session is None:
        session = WiFiSession(
            user_id=payment.purchase.user_id,
            package_id=payment.purchase.package_id,
            payment_id=payment.id,
            device_mac_address=mac,
            device_ip_address=ip,
            status="PAYMENT_CONFIRMED",
        )
        db.add(session)

    db.commit()
    return session


def activate_session(
    db: Session,
    session_id: int,
    router: Callable[[int], dict] | None = None,
) -> WiFiSession:
    """
    Activate the purchased access service.

    The session timer starts only after the selected access provider
    confirms successful activation.
    """
    session = db.get(WiFiSession, session_id, with_for_update=True)

    if session is None:
        raise LookupError("Session not found")

    if session.activation_status == "succeeded":
        return session

    attempt = None
    if session.status == "ACTIVATING":
        attempt = max(session.attempts, key=lambda item: item.attempt_number, default=None)
        if attempt is None or attempt.error_code != RouterActivationUnconfirmed.__name__:
            raise ValueError("Cannot reconcile a session without an unconfirmed activation")
    elif session.status not in ("PAYMENT_CONFIRMED", "FAILED"):
        raise ValueError(f"Cannot activate a session that is {session.status}")

    purchase = session.payment.purchase
    reconciling = attempt is not None

    if attempt is None:
        attempt = ActivationAttempt(
            session_id=session.id,
            attempt_number=len(session.attempts) + 1,
        )
        session.status = "ACTIVATING"
        session.activation_status = "waiting"
        session.activation_requested_at = datetime.now(timezone.utc)
        session.failure_reason = None
        db.add(attempt)
        db.flush()

    try:
        if reconciling:
            if not isinstance(get_access_authenticator(), MikroTikAuthenticator):
                raise RouterActivationUnconfirmed("Reconciliation requires MikroTik mode")

            result = activate_hotspot_device(
                mac_address=session.device_mac_address,
                ip_address=session.device_ip_address,
                download_speed_mbps=purchase.download_speed_mbps,
                upload_speed_mbps=purchase.upload_speed_mbps,
                verify_only=True,
            )
        elif router is not None:
            # Preserve the existing test and custom-router callback contract.
            result = router(session.id)
        else:
            # Never send a recorded mock payment to a live MikroTik router.
            authenticator = get_access_authenticator()
            payment_origin = session.payment.raw_callback

            if (
                isinstance(authenticator, MikroTikAuthenticator)
                and isinstance(payment_origin, dict)
                and payment_origin.get("mock") is True
            ):
                raise RuntimeError(
                    "Mock payment cannot activate access on a live MikroTik router"
                )

            if isinstance(authenticator, MikroTikAuthenticator) and (
                not purchase.device_mac_address
                or session.device_mac_address != purchase.device_mac_address
                or session.device_ip_address != purchase.device_ip_address
            ):
                raise RuntimeError("Live activation requires a verified purchase device")

            result = activate_access_device(
                mac_address=session.device_mac_address,
                ip_address=session.device_ip_address,
                download_speed_mbps=purchase.download_speed_mbps,
                upload_speed_mbps=purchase.upload_speed_mbps,
            )

        if result.get("status") != "ACTIVE":
            raise RuntimeError("Router did not confirm activation")

    except Exception as error:
        if reconciling or isinstance(error, RouterActivationUnconfirmed):
            attempt.error_code = RouterActivationUnconfirmed.__name__
            attempt.error_message = str(error)[:255]
            db.commit()
            return session

        attempt.status = "failed"
        attempt.error_code = type(error).__name__
        attempt.error_message = str(error)[:255]

        session.status = "FAILED"
        session.activation_status = "failed"
        session.failure_reason = str(error)[:255]

    else:
        attempt.status = "succeeded"
        attempt.error_code = None
        attempt.error_message = None

        session.status = "ACTIVE"
        session.activation_status = "succeeded"
        session.started_at = datetime.now(timezone.utc)
        session.expires_at = session.started_at + timedelta(
            minutes=purchase.duration_minutes
        )

    attempt.completed_at = datetime.now(timezone.utc)

    db.commit()
    return session
