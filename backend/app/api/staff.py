from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import Payment, WiFiSession

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


@router.get("/payments", response_model=list[PaymentRead])
def list_payments(status: str | None = None, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = db.query(Payment)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(Payment.id.desc()).limit(limit).offset(offset).all()


@router.get("/payments/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise LookupError("Payment not found")  # main.py turns this into a 404
    return payment


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(status: str | None = None, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = db.query(WiFiSession)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(WiFiSession.id.desc()).limit(limit).offset(offset).all()


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
