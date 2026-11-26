import logging
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_customer
from app.api.mock_mode import require_mock_mode
from app.core.security import create_device_reference, read_device_reference
from app.db.session import get_db
from app.models import Payment, Purchase, User, WiFiSession
from app.schemas.billing import (
    CheckoutIn, CustomerCheckoutIn, CustomerConnectionRead, CustomerMockPaymentRead,
    CustomerPaymentRead, CustomerPurchaseIn,
    DeviceReferenceOut, MockPaymentIn, PaymentOut, PurchaseIn, PurchaseOut,
)
from app.services.device_identity import (
    checkout_device_verification_enabled, resolve_hotspot_device, validate_client_ip,
)
from app.services.mock_payment import process_mock_payment
from app.services.payment_fulfilment import fulfil_payment
from app.services.payment_service import create_payment
from app.services.mpesa_payment_service import ensure_no_overlapping_payment
from app.payments.payment_service_errors import AccessAlreadyReserved
from app.services.purchase_service import create_purchase
from app.services.session_service import connection_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Purchases and Payments"])
customer_router = APIRouter(prefix="/api/customer", tags=["Customer checkout"])


def direct_client_ip(request: Request) -> str:
    # Deploy this mode with proxy-header processing disabled in the ASGI server.
    if request.client is None or any(
        name in request.headers for name in ("forwarded", "x-forwarded-for", "x-real-ip")
    ):
        raise ValueError("Checkout requires a direct hotspot connection")
    return validate_client_ip(request.client.host)


def verified_device_mac(client_ip: str) -> str:
    try:
        return resolve_hotspot_device(client_ip)
    except ValueError:
        raise
    except Exception:
        logger.exception("Hotspot device verification failed")
        raise HTTPException(503, "Hotspot device verification is unavailable") from None


@router.post("/checkout/device-reference", response_model=DeviceReferenceOut)
def issue_device_reference(
    data: CheckoutIn, request: Request, response: Response,
    idempotency_key: str = Header(min_length=8, max_length=100),
):
    if not checkout_device_verification_enabled():
        raise HTTPException(404, "Not found")

    client_ip = direct_client_ip(request)
    mac = verified_device_mac(client_ip)
    response.headers["Cache-Control"] = "no-store"
    return DeviceReferenceOut(device_reference=create_device_reference({
        "user": data.user_id, "package": data.package_id, "key": idempotency_key,
        "ip": client_ip, "mac": mac,
    }))


@router.post("/purchases", response_model=PurchaseOut, status_code=201)
def new_purchase(
    data: PurchaseIn, request: Request, response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str = Header(min_length=8, max_length=100),
):
    device_mac = device_ip = None
    if checkout_device_verification_enabled():
        if not data.device_reference:
            raise ValueError("A verified device reference is required")

        device_ip = direct_client_ip(request)
        claims = read_device_reference(data.device_reference)
        if (claims["user"], claims["package"], claims["key"], claims["ip"]) != (
            data.user_id, data.package_id, idempotency_key, device_ip,
        ):
            raise ValueError("Device reference does not match the checkout")

        device_mac = verified_device_mac(device_ip)
        if claims["mac"] != device_mac:
            raise ValueError("Device reference no longer matches the hotspot device")
    elif data.device_reference:
        raise ValueError("Device verification is unavailable")

    purchase, created = create_purchase(
        db, data.user_id, data.package_id, idempotency_key,
        device_mac=device_mac, device_ip=device_ip,
    )
    response.status_code = 201 if created else 200  # repeated key: same purchase back
    return purchase


@customer_router.post("/checkout/device-reference", response_model=DeviceReferenceOut)
def issue_customer_device_reference(
    data: CustomerCheckoutIn, request: Request, response: Response,
    customer: User = Depends(current_customer),
    idempotency_key: str = Header(min_length=8, max_length=100),
):
    return issue_device_reference(
        CheckoutIn(user_id=customer.id, package_id=data.package_id),
        request, response, idempotency_key,
    )


@customer_router.post("/purchases", response_model=PurchaseOut, status_code=201)
def new_customer_purchase(
    data: CustomerPurchaseIn, request: Request, response: Response,
    customer: User = Depends(current_customer),
    db: Session = Depends(get_db),
    idempotency_key: str = Header(min_length=8, max_length=100),
):
    return new_purchase(
        PurchaseIn(user_id=customer.id, **data.model_dump()),
        request, response, db, idempotency_key,
    )


@customer_router.get("/payments/{payment_id}", response_model=CustomerPaymentRead, response_model_exclude_defaults=True)
def get_customer_payment(
    payment_id: int, response: Response,
    customer: User = Depends(current_customer),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(Payment, Purchase.package_name)
        .join(Purchase, Payment.purchase_id == Purchase.id)
        .where(Payment.id == payment_id, Purchase.user_id == customer.id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Payment not found")

    payment, package_name = row
    response.headers["Cache-Control"] = "no-store"
    return CustomerPaymentRead(
        id=payment.id,
        purchase_id=payment.purchase_id,
        status=payment.status,
        amount=payment.amount,
        package_name=package_name,
        simulated=(payment.raw_callback or {}).get("mock") is True,
        mpesa_receipt_number=(
            payment.mpesa_receipt_number if payment.status == "successful" else None
        ),
    )


@customer_router.get("/connection", response_model=CustomerConnectionRead | None)
def get_customer_connection(
    response: Response,
    payment_id: int | None = Query(default=None, ge=1, le=2147483647),
    customer: User = Depends(current_customer),
    db: Session = Depends(get_db),
):
    statement = (
        select(Payment, Purchase, WiFiSession)
        .join(Purchase, Purchase.id == Payment.purchase_id)
        .outerjoin(WiFiSession, WiFiSession.payment_id == Payment.id)
        .where(Purchase.user_id == customer.id)
    )
    if payment_id is None:
        statement = statement.where(Payment.status == "successful").order_by(
            Payment.paid_at.desc().nulls_last(), Payment.id.desc(),
        ).limit(1)
    else:
        statement = statement.where(Payment.id == payment_id)

    response.headers["Cache-Control"] = "no-store"
    result = db.execute(statement).one_or_none()
    if result is None:
        if payment_id is None:
            return None
        raise HTTPException(404, "Payment not found")

    payment, purchase, session = result
    now = datetime.now(UTC)
    paid = payment.status == "successful"
    started = payment.paid_at if paid else None
    expires = started + timedelta(minutes=purchase.duration_minutes) if started is not None else None
    if paid and session is not None and session.subscription is not None:
        started = session.subscription.start_date
        expires = session.subscription.end_date
    return CustomerConnectionRead(
        payment_id=payment.id,
        payment_status=payment.status,
        access_status=connection_status(paid, session, expires, now),
        package_name=purchase.package_name,
        mpesa_receipt_number=payment.mpesa_receipt_number if paid else None,
        started_at=started,
        expires_at=expires,
        server_now=now,
        simulated=(payment.raw_callback or {}).get("mock") is True,
    )


@customer_router.post(
    "/payments/mock", response_model=CustomerMockPaymentRead, dependencies=[Depends(require_mock_mode)]
)
def mock_customer_payment(
    data: MockPaymentIn,
    customer: User = Depends(current_customer),
    db: Session = Depends(get_db),
):
    if (
        os.getenv("ROUTER_MODE", "").strip().lower() != "mock"
        or os.getenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false").lower() == "true"
    ):
        raise HTTPException(404, "Not found")
    purchase = db.scalar(
        select(Purchase).where(Purchase.id == data.purchase_id, Purchase.user_id == customer.id)
        .with_for_update()
    )
    if purchase is None:
        raise HTTPException(404, "Purchase not found")

    payment = db.scalar(select(Payment).where(
        Payment.purchase_id == purchase.id, Payment.status == "successful",
    ))
    if payment is None:
        try:
            ensure_no_overlapping_payment(db, purchase)
        except AccessAlreadyReserved as error:
            raise HTTPException(409, error.message) from None
        payment = create_payment(db, purchase.id, data.phone_number, commit=False)
        payment = process_mock_payment(db, payment.id, data.successful)
    elif (payment.raw_callback or {}).get("mock") is not True:
        raise HTTPException(409, "Purchase already paid")

    result = CustomerMockPaymentRead(
        payment_id=payment.id, purchase_id=purchase.id, status=payment.status,
    )
    if payment.status == "successful":
        fulfil_payment(db, payment.id)
    return result


@router.post("/payments/mock", response_model=PaymentOut)
def mock_payment(data: MockPaymentIn, db: Session = Depends(get_db)):
    """Development only: returns 404 unless ENABLE_MOCK_PAYMENTS=true."""
    payment = create_payment(db, data.purchase_id, data.phone_number, commit=False)
    return process_mock_payment(db, payment.id, data.successful)
