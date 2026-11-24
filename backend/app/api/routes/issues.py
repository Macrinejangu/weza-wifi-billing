from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import ActivationAttempt, AdminAuditLog, Payment, Purchase, User, WiFiSession
from app.services.payment_fulfilment import fulfil_payment

router = APIRouter(prefix="/api/connection-issues", tags=["Staff"], dependencies=[Depends(current_staff)])

FAILURE_REASONS = {
    "RouterActivationError": "The router could not activate access for this session.",
    "TimeoutError": "The activation request timed out.",
    "ConnectionError": "The activation service could not establish a connection.",
}


class ConnectionIssueRead(BaseModel):
    session_id: int | None
    customer_id: int
    payment_id: int
    purchase_id: int
    payment_reference: str | None
    payment_status: str
    activation_status: str
    failure_reason: str
    updated_at: datetime


@router.get("", response_model=list[ConnectionIssueRead])
def list_connection_issues(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    latest_failure = (
        select(ActivationAttempt.error_code)
        .where(
            ActivationAttempt.session_id == WiFiSession.id,
            ActivationAttempt.status == "failed",
        )
        .order_by(ActivationAttempt.attempt_number.desc())
        .limit(1)
        .scalar_subquery()
    )
    updated_at = func.coalesce(WiFiSession.updated_at, Payment.updated_at)
    statement = (
        select(
            WiFiSession.id.label("session_id"),
            Purchase.user_id.label("customer_id"),
            Payment.id.label("payment_id"),
            Payment.purchase_id,
            Payment.mpesa_receipt_number,
            Payment.checkout_request_id,
            Payment.status.label("payment_status"),
            WiFiSession.activation_status,
            updated_at.label("updated_at"),
            latest_failure.label("error_code"),
        )
        .select_from(Payment)
        .join(Purchase, Purchase.id == Payment.purchase_id)
        .outerjoin(WiFiSession, WiFiSession.payment_id == Payment.id)
        .where(
            Payment.status == "successful",
            or_(WiFiSession.id.is_(None), WiFiSession.status.in_(("FAILED", "ACTIVATING", "PAYMENT_CONFIRMED"))),
        )
        .order_by(updated_at.desc(), Payment.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return [
        ConnectionIssueRead(
            session_id=row.session_id,
            customer_id=row.customer_id,
            payment_id=row.payment_id,
            purchase_id=row.purchase_id,
            payment_reference=row.mpesa_receipt_number or row.checkout_request_id,
            payment_status=row.payment_status,
            activation_status=row.activation_status or "not_started",
            failure_reason=FAILURE_REASONS.get(
                row.error_code,
                "Payment confirmed. Internet access has not been confirmed."
                if row.activation_status != "failed"
                else "Activation failed. A safe diagnostic reason is unavailable.",
            ),
            updated_at=row.updated_at,
        )
        for row in db.execute(statement)
    ]

class ActivationRetryRead(BaseModel):
    outcome: str


@router.post("/{payment_id}/retry", response_model=ActivationRetryRead)
def retry_paid_activation(
    payment_id: int,
    staff: User = Depends(current_staff),
    db: Session = Depends(get_db),
):
    payment = db.get(Payment, payment_id)
    if payment is None or payment.status != "successful" or payment.paid_at is None:
        raise HTTPException(404, "Confirmed payment not found")
    if payment.paid_at + timedelta(minutes=payment.purchase.duration_minutes) <= datetime.now(UTC):
        raise HTTPException(409, "This paid package has expired")

    db.add(AdminAuditLog(
        admin_id=staff.id,
        action="Retried paid activation",
        entity_type="payment",
        entity_id=payment.id,
    ))
    db.commit()
    return ActivationRetryRead(outcome=fulfil_payment(db, payment_id).outcome.value)
