from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import ActivationAttempt, Payment, WiFiSession

router = APIRouter(prefix="/api/connection-issues", tags=["Staff"], dependencies=[Depends(current_staff)])

FAILURE_REASONS = {
    "RouterActivationError": "The router could not activate access for this session.",
    "TimeoutError": "The activation request timed out.",
    "ConnectionError": "The activation service could not establish a connection.",
}


class ConnectionIssueRead(BaseModel):
    session_id: int
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
    statement = (
        select(
            WiFiSession.id.label("session_id"),
            WiFiSession.user_id.label("customer_id"),
            Payment.id.label("payment_id"),
            Payment.purchase_id,
            Payment.mpesa_receipt_number,
            Payment.checkout_request_id,
            Payment.status.label("payment_status"),
            WiFiSession.activation_status,
            WiFiSession.updated_at,
            latest_failure.label("error_code"),
        )
        .join(Payment, Payment.id == WiFiSession.payment_id)
        .where(
            Payment.status == "successful",
            WiFiSession.status == "FAILED",
            WiFiSession.activation_status == "failed",
        )
        .order_by(WiFiSession.updated_at.desc(), WiFiSession.id.desc())
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
            activation_status=row.activation_status,
            failure_reason=FAILURE_REASONS.get(
                row.error_code, "Activation failed. A safe diagnostic reason is unavailable.",
            ),
            updated_at=row.updated_at,
        )
        for row in db.execute(statement)
    ]
