from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
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
