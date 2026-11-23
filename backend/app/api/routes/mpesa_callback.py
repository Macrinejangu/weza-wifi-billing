"""Public endpoint that receives M-Pesa (Daraja) payment callbacks (WEZA-50).

Daraja callbacks are NOT signed, so this endpoint is guarded by:
  1. an optional source-IP check,
  2. a secret token inside the URL path,
  3. a body size limit, and
  4. matching the message against a payment WE created, plus confirming
     success with the STK status query (see callback_processing.py).

Rules this route follows:
* A wrong IP and a wrong token get the SAME plain 404, so a stranger cannot
  tell which gate stopped them.
* Every accepted message is stored as an audit row BEFORE it is processed.
* Safaricom gets a 200 for anything we stored, even if we rejected it: it
  cannot act on our reasons, and a failure code would only trigger retries.
  A 5xx means "we could not record or process this".
* The token is never logged. uvicorn's access log does print request paths,
  so the token can appear there. Known limitation, see docs.
* ValueError and LookupError are caught HERE: main.py would otherwise turn
  them into 400/404 responses carrying our internal wording.
"""

import json
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.routes.payments import get_daraja_client
from app.config import callback_security_policy
from app.db.session import get_db
from app.integrations.mpesa.client import DarajaClient
from app.payments.callback_security import CallbackDecision, CallbackSecurityPolicy
from app.payments.event_payload import build_event_payload
from app.services.callback_processing import process_callback
from app.services.payment_event_service import EventSource, record_received_event



logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments/mpesa", tags=["M-Pesa callback"])

# A real STK callback is under 2 KB. 64 KB leaves room for growth and still
# stops anyone from making us read or store a huge body.
MAX_BODY_BYTES = 64 * 1024

# UNVERIFIED: the reply Safaricom expects has not been confirmed from the
# official Daraja documentation yet. Confirm before relying on it (see docs).
ACCEPTED_REPLY = {"ResultCode": 0, "ResultDesc": "Accepted"}


@lru_cache(maxsize=1)
def _build_security_policy() -> CallbackSecurityPolicy:
    """Build the gates once per process. lru_cache does not cache a raised
    exception, so fixing the configuration works on the next request."""
    return callback_security_policy()


def get_callback_policy() -> CallbackSecurityPolicy | None:
    """FastAPI dependency. None means the endpoint is not configured.
    Tests replace this dependency."""
    try:
        return _build_security_policy()
    except RuntimeError as error:
        # config.py messages name the setting, never the token's value.
        logger.error("callback endpoint is not configured: %s", error)
        return None


def _not_found() -> Response:
    # Plain, identical body for every rejection: reveals nothing.
    return Response(status_code=404)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"detail": message, "code": code}, status_code=status)


async def _read_limited_body(request: Request) -> bytes | None:
    """Return the body, or None if it is larger than MAX_BODY_BYTES.

    Content-Length is only a hint a client can lie about, so the bytes
    actually received are counted as well.
    """
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_BODY_BYTES:
                return None
        except ValueError:
            return None  # a malformed length header is refused, not guessed
    received = bytearray()
    async for chunk in request.stream():
        received.extend(chunk)
        if len(received) > MAX_BODY_BYTES:
            return None
    return bytes(received)


@router.post("/callback/{token}", include_in_schema=False)
async def receive_mpesa_callback(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    policy: CallbackSecurityPolicy | None = Depends(get_callback_policy),
    daraja: DarajaClient | None = Depends(get_daraja_client),
):
    """Receive one Daraja STK callback.

    include_in_schema=False keeps the secret path out of /docs.

    The route is async only to read the request stream. The blocking
    database and Daraja work runs in a worker thread via run_in_threadpool,
    so it does not freeze the event loop.
    """
    if policy is None:
        return _not_found()

    peer = request.client.host if request.client else None
    decision = policy.check(
        peer=peer,
        forwarded_for=request.headers.get("x-forwarded-for"),
        received_token=token,
    )
    if decision is not CallbackDecision.ALLOWED:
        # Log which gate stopped it, but never the token or the header value.
        logger.warning("callback rejected: gate=%s", decision.value)
        return _not_found()

    raw_body = await _read_limited_body(request)
    if raw_body is None:
        logger.warning("callback rejected: body too large or bad length header")
        return _error(413, "payload_too_large", "Request body is too large.")    

    return await run_in_threadpool(_handle_callback, db, daraja, raw_body)


def _handle_callback(
    db: Session, daraja: DarajaClient | None, raw_body: bytes
) -> Response:
    """Blocking part of the route: store, process, reply."""
    raw_payload = build_event_payload(raw_body)
    try:
        payload = json.loads(raw_body)
    except (ValueError, RecursionError):
        payload = None  # process_callback rejects and records it

    try:
        event_id = record_received_event(
            db,
            source=EventSource.CALLBACK,
            payload=raw_payload,
            checkout_request_id=_checkout_id_hint(payload),
            result_code=_result_code_hint(payload),
        )
    except SQLAlchemyError as error:
        db.rollback()
        # Type only: SQLAlchemy messages can include SQL parameters.
        logger.error("could not record callback: %s", type(error).__name__)
        return _error(503, "service_unavailable", "Callback could not be recorded.")

    try:
        outcome = process_callback(
            db, daraja, event_id=event_id, payload=payload, raw_payload=raw_payload
        )
    except Exception as error:  # noqa: BLE001 - deliberate: last line of defence
        # Includes ValueError/LookupError from the service layer, which
        # main.py would otherwise expose as 400/404 with internal wording.
        # The audit event stays 'received', which honestly means "unprocessed".
        db.rollback()
        logger.error(
            "callback processing failed: event_id=%s error=%s",
            event_id, type(error).__name__,
        )
        return _error(500, "internal_error", "Something went wrong.")

    logger.info(
        "callback handled: event_id=%s outcome=%s", event_id, outcome.outcome.value
    )
    return JSONResponse(ACCEPTED_REPLY, status_code=200)


def _checkout_id_hint(payload: object) -> object:
    """Best-effort checkout id for the audit row. Never raises: the value is
    untrusted, and record_received_event validates it again."""
    try:
        return payload["Body"]["stkCallback"]["CheckoutRequestID"]
    except (KeyError, TypeError, IndexError):
        return None


def _result_code_hint(payload: object) -> object:
    try:
        return payload["Body"]["stkCallback"]["ResultCode"]
    except (KeyError, TypeError, IndexError):
        return None