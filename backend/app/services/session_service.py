from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActivationAttempt, Payment, Subscription, WiFiSession
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
    *,
    verified_checkout: bool = False,
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

    subscription = None
    if verified_checkout:
        if payment.paid_at is None:
            raise ValueError("Verified payment timestamp is required")
        subscription = db.query(Subscription).filter_by(payment_id=payment_id).one_or_none()
        if subscription is None:
            subscription = Subscription(
                user_id=purchase.user_id,
                package_id=purchase.package_id,
                payment_id=payment_id,
                start_date=payment.paid_at,
                end_date=payment.paid_at + timedelta(minutes=purchase.duration_minutes),
                status="active",
            )
            db.add(subscription)

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

    if subscription is not None:
        session.subscription = subscription
    db.commit()
    return session


def activate_session(
    db: Session,
    session_id: int,
    router: Callable[[int], dict] | None = None,
) -> WiFiSession:
    """
    Activate the purchased access service.

    The provider confirms access separately from the subscription timer.
    Legacy sessions without subscriptions keep their activation-based timer.
    """
    session = db.get(WiFiSession, session_id, with_for_update=True, populate_existing=True)

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
    subscription = session.subscription
    if subscription is not None and subscription.end_date <= datetime.now(timezone.utc):
        # An unconfirmed router call may still have granted access. Leave it
        # for the expiry process to revoke before marking the session ended.
        if not reconciling and session.router_grant_id is None:
            session.status = "EXPIRED"
            subscription.status = "expired"
            db.commit()
        return session

    if attempt is None and router is None:
        try:
            authenticator = get_access_authenticator()
        except RuntimeError:
            # Activation reports configuration errors through the normal attempt.
            authenticator = None
        if isinstance(authenticator, MikroTikAuthenticator):
            origin = session.payment.raw_callback or {}
            if not origin.get("mock") and purchase.device_mac_address and session.router_grant_id is None:
                session.router_grant_id = uuid4().hex
                db.commit()
                return activate_session(db, session_id)

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

            if session.router_grant_id is None or not session.device_mac_address:
                raise RouterActivationUnconfirmed("This session has no recorded hotspot grant")
            lock_hotspot_device(db, session.device_mac_address)
            result = activate_hotspot_device(
                mac_address=session.device_mac_address,
                ip_address=session.device_ip_address,
                download_speed_mbps=purchase.download_speed_mbps,
                upload_speed_mbps=purchase.upload_speed_mbps,
                verify_only=True,
                grant_id=session.router_grant_id,
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

            access = {
                "mac_address": session.device_mac_address,
                "ip_address": session.device_ip_address,
                "download_speed_mbps": purchase.download_speed_mbps,
                "upload_speed_mbps": purchase.upload_speed_mbps,
            }
            if isinstance(authenticator, MikroTikAuthenticator):
                lock_hotspot_device(db, session.device_mac_address)
                result = activate_hotspot_device(**access, grant_id=session.router_grant_id)
            else:
                result = activate_access_device(**access)

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
        session.router_identity = result.get("router_identity")
        session.router_session_id = result.get("router_session_id")
        session.router_server_name = result.get("server")
        if subscription is not None:
            session.started_at = subscription.start_date
            session.expires_at = subscription.end_date
        else:
            session.started_at = datetime.now(timezone.utc)
            session.expires_at = session.started_at + timedelta(minutes=purchase.duration_minutes)

    attempt.completed_at = datetime.now(timezone.utc)

    db.commit()
    return session


def lock_hotspot_device(db: Session, mac: str) -> None:
    # Activation and expiry must never change the same device concurrently.
    db.execute(select(func.pg_advisory_xact_lock(func.hashtext(f"weza-hotspot:{mac}"))))
