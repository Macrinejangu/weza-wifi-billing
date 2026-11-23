import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_customer
from app.core.security import create_device_reference, read_device_reference
from app.db.session import get_db
from app.models import Payment, Purchase, User
from app.schemas.billing import (
    CheckoutIn, CustomerCheckoutIn, CustomerPaymentRead, CustomerPurchaseIn,
    DeviceReferenceOut, MockPaymentIn, PaymentOut, PurchaseIn, PurchaseOut,
)
from app.services.device_identity import (
    checkout_device_verification_enabled, resolve_hotspot_device, validate_client_ip,
)
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase

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


@customer_router.get("/payments/{payment_id}", response_model=CustomerPaymentRead)
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
        mpesa_receipt_number=(
            payment.mpesa_receipt_number if payment.status == "successful" else None
        ),
    )


@router.post("/payments/mock", response_model=PaymentOut)
def mock_payment(data: MockPaymentIn, db: Session = Depends(get_db)):
    """Development only: returns 404 unless ENABLE_MOCK_PAYMENTS=true."""
    payment = create_payment(db, data.purchase_id, data.phone_number, commit=False)
    return process_mock_payment(db, payment.id, data.successful)
