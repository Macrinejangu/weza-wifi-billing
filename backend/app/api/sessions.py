from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.package import Package
from app.models.payment import Payment
from app.models.session import WiFiSession
from app.services.mock_payment import process_mock_payment
from app.services.session_service import activate_paid_session

router = APIRouter(prefix="/api", tags=["Payments and Sessions"])


class ActivationRequest(BaseModel):
    user_id: int
    package_id: int


@router.post("/test-activation")
def test_activation(data: ActivationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    package = db.query(Package).filter(Package.id == data.package_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not package or not package.is_active:
        raise HTTPException(status_code=404, detail="Active package not found")

    payment = Payment(
        user_id=user.id,
        package_id=package.id,
        amount=package.price,
        payment_method="MOCK",
        status="pending"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    wifi_session = WiFiSession(
        user_id=user.id,
        package_id=package.id,
        payment_id=payment.id,
        status="PENDING_PAYMENT"
    )
    db.add(wifi_session)
    db.commit()

    try:
        process_mock_payment(db, payment.id, successful=True)
        wifi_session = activate_paid_session(db, wifi_session.id)
        return {
            "payment_status": payment.status,
            "session_status": wifi_session.status,
            "started_at": wifi_session.started_at,
            "expires_at": wifi_session.expires_at
        }
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
    