from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import current_staff, require_admin
from app.db.session import get_db
from app.models import AdminAuditLog, Payment, Purchase, Subscription, User, WiFiSession
from app.services.access_auth import MikroTikAuthenticator, MockAuthenticator, get_access_authenticator
from app.services.router import expire_hotspot_grant
from app.services.session_service import connection_status, lock_hotspot_device

# Every route in this file needs a staff login.
router = APIRouter(prefix="/api", tags=["Staff"], dependencies=[Depends(current_staff)])


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    purchase_id: int
    amount: int
    phone_number: str
    status: str
    checkout_request_id: str | None
    mpesa_receipt_number: str | None
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime
    access_status: str = "unconfirmed"
    session_id: int | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    package_id: int
    payment_id: int
    status: str
    activation_status: str
    failure_reason: str | None
    started_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


def payment_with_access():
    return (
        select(Payment, Purchase.duration_minutes, WiFiSession, Subscription.end_date)
        .join(Purchase, Purchase.id == Payment.purchase_id)
        .outerjoin(WiFiSession, WiFiSession.payment_id == Payment.id)
        .outerjoin(Subscription, Subscription.id == WiFiSession.subscription_id)
    )


def read_payment_access(
    payment: Payment, duration: int, session: WiFiSession | None,
    subscription_end: datetime | None, *, now: datetime,
) -> PaymentRead:
    expires_at = subscription_end or (session.expires_at if session else None)
    if expires_at is None and payment.paid_at is not None:
        expires_at = payment.paid_at + timedelta(minutes=duration)
    access_status = connection_status(payment.status == "successful", session, expires_at, now)
    if (session is not None and access_status not in ("unconfirmed", "expired")
            and (session.ended_at is not None or session.status == "CANCELLED")):
        access_status = "ended"
    return PaymentRead.model_validate(payment).model_copy(update={
        "access_status": access_status,
        "session_id": session.id if session else None,
    })


@router.get("/payments", response_model=list[PaymentRead])
def list_payments(status: str | None = None, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = payment_with_access()
    if status:
        query = query.where(Payment.status == status)
    rows = db.execute(query.order_by(Payment.id.desc()).limit(limit).offset(offset))
    now = datetime.now(UTC)
    return [read_payment_access(*row, now=now) for row in rows]


@router.get("/payments/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    row = db.execute(payment_with_access().where(Payment.id == payment_id)).one_or_none()
    if row is None:
        raise LookupError("Payment not found")  # main.py turns this into a 404
    return read_payment_access(*row, now=datetime.now(UTC))


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(status: str | None = None, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = db.query(WiFiSession)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(WiFiSession.id.desc()).limit(limit).offset(offset).all()


@router.post("/sessions/{session_id}/disconnect")
def disconnect_session(
    session_id: int, staff: User = Depends(require_admin), db: Session = Depends(get_db),
):
    session = db.get(WiFiSession, session_id, with_for_update=True)
    if session is None:
        raise HTTPException(404, "Session not found")
    if (
        session.status != "ACTIVE" or session.ended_at is not None
        or not session.expires_at or session.expires_at <= datetime.now(UTC)
        or (session.subscription and session.subscription.end_date <= datetime.now(UTC))
    ):
        raise HTTPException(409, "Only an active paid session can be disconnected.")
    try:
        authenticator = get_access_authenticator()
        simulated = isinstance(authenticator, MockAuthenticator)
        if isinstance(authenticator, MikroTikAuthenticator) and session.router_grant_id and session.device_mac_address:
            lock_hotspot_device(db, session.device_mac_address)
            expire_hotspot_grant(
                session.device_mac_address, session.router_grant_id,
                router_identity=session.router_identity, router_server_name=session.router_server_name,
                keep_access=True,
            )
        elif not (simulated and (session.payment.raw_callback or {}).get("mock")):
            raise HTTPException(409, "This session has no verified router grant for a safe disconnect.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "The router could not complete the disconnect. Check the connection before retrying.") from None

    db.add(AdminAuditLog(
        admin_id=staff.id, action="Simulated disconnect" if simulated else "Disconnected device",
        entity_type="session", entity_id=session.id,
    ))
    db.commit()
    return {"simulated": simulated}


class OverviewRead(BaseModel):
    sandbox_settled_today_kes: int
    sandbox_settled_today_count: int
    active_session_records: int
    pending_payments: int
    failed_activations: int


NAIROBI = ZoneInfo("Africa/Nairobi")


def read_overview(db: Session, now: datetime) -> OverviewRead:
    local_day = now.astimezone(NAIROBI).date()
    day_start = datetime.combine(local_day, time.min, tzinfo=NAIROBI)
    day_end = day_start + timedelta(days=1)
    # Main only accepts real provider responses in Daraja sandbox mode.
    settled_today = select(Payment.amount).where(
        Payment.payment_method == "mpesa",
        Payment.status == "successful",
        Payment.checkout_request_id.is_not(None),
        Payment.merchant_request_id.is_not(None),
        Payment.mpesa_receipt_number.is_not(None),
        Payment.raw_callback["Body"]["stkCallback"].as_string().is_not(None),
        func.coalesce(Payment.raw_callback["mock"].as_string(), "") != "true",
        Payment.paid_at >= day_start,
        Payment.paid_at < day_end,
    ).subquery()

    active_sessions = select(func.count(WiFiSession.id)).where(
        WiFiSession.status == "ACTIVE",
        WiFiSession.activation_status == "succeeded",
        WiFiSession.started_at <= now,
        WiFiSession.expires_at > now,
        WiFiSession.ended_at.is_(None),
    ).scalar_subquery()
    pending_payments = select(func.count(Payment.id)).where(
        Payment.status == "pending",
    ).scalar_subquery()
    failed_activations = select(func.count(WiFiSession.id)).where(
        WiFiSession.status == "FAILED",
        WiFiSession.activation_status == "failed",
    ).scalar_subquery()
    summary = db.execute(select(
        select(func.coalesce(func.sum(settled_today.c.amount), 0)).scalar_subquery().label("sandbox_settled_today_kes"),
        select(func.count()).select_from(settled_today).scalar_subquery().label("sandbox_settled_today_count"),
        active_sessions.label("active_session_records"),
        pending_payments.label("pending_payments"),
        failed_activations.label("failed_activations"),
    )).mappings().one()
    return OverviewRead(**summary)


@router.get("/overview", response_model=OverviewRead)
def get_overview(db: Session = Depends(get_db)):
    return read_overview(db, datetime.now(UTC))
