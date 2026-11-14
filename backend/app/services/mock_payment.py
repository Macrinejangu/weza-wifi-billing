from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.payment import Payment


def process_mock_payment(
    db: Session,
    payment_id: int,
    successful: bool = True
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if payment is None:
        raise ValueError("Payment not found")

    # Do not process an already completed payment again
    if payment.status != "pending":
        return payment

    if successful:
        payment.status = "completed"
        payment.paid_at = datetime.now(timezone.utc)
    else:
        payment.status = "failed"

    db.commit()
    db.refresh(payment)

    return payment
