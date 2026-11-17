from uuid import uuid4

from app.models import Payment
from app.services.payment_service import apply_payment_result


def process_mock_payment(db, payment_id: int, successful: bool = True) -> Payment:
    """Development only: fake the M-Pesa callback, using the same rules as a real one."""
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise LookupError("Payment not found")
    payment.checkout_request_id = payment.checkout_request_id or f"MOCK-{uuid4().hex[:16]}"
    db.commit()

    code, desc = (0, "Mock success") if successful else (1032, "Mock cancelled")
    receipt = f"MOCK{uuid4().hex[:8].upper()}" if successful else None
    apply_payment_result(db, payment.checkout_request_id, code, desc, receipt, {"mock": True})
    db.refresh(payment)
    return payment
