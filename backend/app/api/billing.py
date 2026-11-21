from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.billing import MockPaymentIn, PaymentOut, PurchaseIn, PurchaseOut
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase

router = APIRouter(prefix="/api", tags=["Purchases and Payments"])


@router.post("/purchases", response_model=PurchaseOut, status_code=201)
def new_purchase(data: PurchaseIn, response: Response, db: Session = Depends(get_db),
                 idempotency_key: str = Header(min_length=8, max_length=100)):
    purchase, created = create_purchase(db, data.user_id, data.package_id, idempotency_key)
    response.status_code = 201 if created else 200  # repeated key: same purchase back
    return purchase


@router.post("/payments/mock", response_model=PaymentOut)
def mock_payment(data: MockPaymentIn, db: Session = Depends(get_db)):
    """Development only: returns 404 unless ENABLE_MOCK_PAYMENTS=true."""
    payment = create_payment(db, data.purchase_id, data.phone_number, commit=False)
    return process_mock_payment(db, payment.id, data.successful)
