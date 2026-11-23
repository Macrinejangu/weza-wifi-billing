"""HTTP route that starts an M-Pesa payment (WEZA-49).

The route is deliberately thin. PaymentRequest validates the input, the
service holds every payment rule, and the amount always comes from our own
database. The route only:
  1. hands the request to initiate_payment(), and
  2. translates every outcome into a stable HTTP status and error body.

Every error body has the same shape so the portal can rely on it:
    {"detail": "<customer-safe text>", "code": "<machine code>", "payment_id": 7}
"payment_id" appears only when a payment row exists. The text always comes
from our own fixed messages, never from Daraja, the database or an exception.

KNOWN GAP: there is no customer login yet, so anyone who guesses a purchase id
could trigger an M-Pesa prompt for it. Add an ownership check when customer
authentication exists.
"""
import logging
import os
from functools import lru_cache

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ROOT_ENV, daraja_settings
from app.db.session import get_db
from app.integrations.mpesa.client import DarajaClient
from app.payments.payment_service_errors import (
    OutcomeUnknown,
    PaymentAlreadyPending,
    PaymentServiceError,
    ProviderNotReached,
    ProviderRejected,
    PurchaseNotFound,
    PurchaseNotPayable,
)
from app.payments.statuses import PaymentStatus
from app.schemas.payment import PaymentInitiated, PaymentRequest
from app.services.mpesa_payment_service import initiate_payment

logger = logging.getLogger(__name__)


def require_sandbox_payments_enabled() -> None:
    load_dotenv(ROOT_ENV)
    if os.getenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(
    prefix="/api/payments",
    tags=["M-Pesa payments"],
    dependencies=[Depends(require_sandbox_payments_enabled)],
)

PROMPT_MESSAGE = "Check your phone and enter your M-Pesa PIN to complete the payment."

# HTTP status for each service error. OutcomeUnknown is 504 when Daraja timed
# out (see _http_status). An error class missing from this table gets 500:
# an unplanned error is never reported as the customer's mistake.
_STATUS_BY_CODE = {
    PurchaseNotFound.code: 404,
    PurchaseNotPayable.code: 409,
    PaymentAlreadyPending.code: 409,
    ProviderRejected.code: 502,
    ProviderNotReached.code: 503,
    OutcomeUnknown.code: 502,
}


@lru_cache(maxsize=1)
def _build_daraja_client() -> DarajaClient:
    """Build the one Daraja client for this process.

    It must be shared: its token cache lives inside it, and every new token
    request invalidates the previous token. lru_cache does not cache a raised
    exception, so a fixed configuration is picked up on the next request.
    """
    return DarajaClient(daraja_settings(), httpx.Client())


def get_daraja_client() -> DarajaClient | None:
    """FastAPI dependency. Returns None when Daraja is not configured.

    None (instead of raising) lets the route answer with our standard error
    body. Tests replace this dependency with a fake client.
    """
    try:
        return _build_daraja_client()
    except RuntimeError as error:
        # config.py messages name the missing variables, never their values.
        logger.error("Daraja is not configured: %s", error)
        return None


def _http_status(error: PaymentServiceError) -> int:
    if isinstance(error, OutcomeUnknown) and error.timed_out:
        return 504
    return _STATUS_BY_CODE.get(error.code, 500)


def _error_response(
    status: int, code: str, message: str, payment_id: int | None = None
) -> JSONResponse:
    body: dict = {"detail": message, "code": code}
    if payment_id is not None:
        body["payment_id"] = payment_id
    return JSONResponse(body, status_code=status)


@router.post(
    "",
    response_model=PaymentInitiated,
    status_code=201,
    responses={
        404: {"description": "Purchase not found"},
        409: {"description": "Purchase not payable, or a payment is already pending"},
        502: {"description": "Daraja refused, or the outcome is unknown"},
        503: {"description": "Payments not configured, or Daraja or the database is down"},
        504: {"description": "Daraja timed out; the payment stays pending"},
    },
)
def start_mpesa_payment(
    data: PaymentRequest,
    db: Session = Depends(get_db),
    daraja: DarajaClient | None = Depends(get_daraja_client),
):
    """Ask Daraja to prompt the customer to pay for a purchase.

    A plain `def`, not `async def`: the Daraja and database calls are
    blocking, so FastAPI runs this in a worker thread and other requests are
    not held up.
    """
    if daraja is None:
        # Checked BEFORE the service runs, so nothing is recorded.
        return _error_response(
            503, "payments_not_configured", "Payments are not available right now."
        )

    try:
        result = initiate_payment(db, daraja, data.purchase_id, data.phone_number)
    except PaymentServiceError as error:
        return _error_response(
            _http_status(error), error.code, error.message, error.payment_id
        )
    except OperationalError as error:
        # Log only the type: SQLAlchemy messages include the SQL parameters,
        # which can contain a phone number.
        logger.error("database unavailable starting a payment: %s", type(error).__name__)
        return _error_response(
            503, "service_unavailable", "Payments are temporarily unavailable."
        )
    except SQLAlchemyError as error:
        logger.error("database error starting a payment: %s", type(error).__name__)
        return _error_response(500, "internal_error", "Something went wrong.")
    except ValueError:
        # Our own bug (a malformed argument reached the service). main.py would
        # turn a ValueError into a 400 carrying its text, so catch it here.
        logger.exception("invalid argument while starting a payment")
        return _error_response(500, "internal_error", "Something went wrong.")

    return PaymentInitiated(
        payment_id=result.payment_id,
        purchase_id=result.purchase_id,
        amount=result.amount,
        status=PaymentStatus.PENDING.value,
        message=PROMPT_MESSAGE,
    )