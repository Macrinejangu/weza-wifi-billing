"""Staff routes for paid customers who are not connected (WEZA-63).

All routes need a staff login and are NOT behind mock mode, so they work with
real payments. Nothing here contacts Daraja: the finder only reads, and a retry
only asks the router again (see app/services/activation_retry.py).

Responses never carry raw router text, phone numbers or exception wording.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import User
from app.services.access_auth import MikroTikAuthenticator, get_access_authenticator
from app.services.activation_recovery import find_unresolved_cases, get_case
from app.services.activation_retry import RetryRefused, retry_activation

logger = logging.getLogger(__name__)

# Every route in this file needs a staff login.
router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"],
    dependencies=[Depends(current_staff)],
)


class RecoveryCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: int
    purchase_id: int
    user_id: int
    session_id: int | None
    reason: str
    action: str
    payment_status: str
    session_status: str | None
    activation_status: str | None
    last_error_code: str | None
    paid_at: datetime | None
    waiting_since: datetime | None
    age_seconds: int


class RetryOut(BaseModel):
    payment_id: int
    session_id: int | None
    outcome: str
    reason_before: str
    audit_id: int


def get_require_device() -> bool:
    """A live router needs a verified device on the purchase.

    Fails closed: if the router mode is not configured, a device is required.
    Tests replace this dependency.
    """
    try:
        return isinstance(get_access_authenticator(), MikroTikAuthenticator)
    except RuntimeError:
        return True


@router.get("/cases", response_model=list[RecoveryCaseOut])
def list_cases(
    response: Response,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    require_device: bool = Depends(get_require_device),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    cases = find_unresolved_cases(
        db, require_device=require_device, limit=limit, offset=offset
    )
    return [RecoveryCaseOut.model_validate(case) for case in cases]


@router.get("/cases/{payment_id}", response_model=RecoveryCaseOut)
def read_case(
    response: Response,
    payment_id: int = Path(ge=1),
    require_device: bool = Depends(get_require_device),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    case = get_case(db, payment_id, require_device=require_device)
    if case is None:
        raise HTTPException(404, "No unresolved case for this payment")
    return RecoveryCaseOut.model_validate(case)


@router.post(
    "/cases/{payment_id}/retry",
    response_model=RetryOut,
    responses={
        404: {"description": "Payment not found"},
        409: {"description": "Retry refused: nothing to retry, payment not confirmed, or needs staff review"},
        503: {"description": "Database unavailable"},
    },
)
def retry_case(
    response: Response,
    payment_id: int = Path(ge=1),
    staff: User = Depends(current_staff),
    require_device: bool = Depends(get_require_device),
    db: Session = Depends(get_db),
):
    """Retry network activation for one paid customer. Never contacts Daraja.

    A retry that ran returns 200 with its outcome (even activation_failed).
    LookupError (unknown payment) becomes a 404 in main.py.
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        result = retry_activation(
            db, payment_id, staff_id=staff.id, require_device=require_device
        )
    except RetryRefused as refused:
        return JSONResponse(
            {"detail": refused.message, "code": refused.code}, status_code=409
        )
    except OperationalError as error:
        # Type only: SQLAlchemy messages include SQL parameters.
        logger.error("database unavailable during retry: %s", type(error).__name__)
        return JSONResponse(
            {"detail": "Recovery is temporarily unavailable.", "code": "service_unavailable"},
            status_code=503,
        )
    return RetryOut(
        payment_id=result.payment_id,
        session_id=result.session_id,
        outcome=result.outcome.value,
        reason_before=result.reason_before.value,
        audit_id=result.audit_id,
    )
