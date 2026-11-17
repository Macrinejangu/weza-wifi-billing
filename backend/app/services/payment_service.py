import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Payment, PaymentEvent, Purchase

log = logging.getLogger(__name__)


def create_payment(db: Session, purchase_id: int, phone_number: str, checkout_request_id: str | None = None, *, commit: bool = True) -> Payment:
    """Start a new payment attempt for a purchase that is still unpaid."""
    purchase = db.get(Purchase, purchase_id, with_for_update=True)
    if purchase is None:
        raise LookupError("Purchase not found")
    if purchase.status != "pending":
        raise ValueError("Purchase is not awaiting payment")
    payment = Payment(
        purchase_id=purchase.id, amount=purchase.amount, phone_number=phone_number,
        checkout_request_id=checkout_request_id, initiated_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    if commit:
        db.commit()
    else:
        db.flush()
    return payment


def apply_payment_result(db, checkout_request_id, result_code, result_desc=None,
                         receipt_number=None, payload=None, source="callback") -> PaymentEvent:

    #Apply an M-Pesa callback/query result. Always logs an event, so repeats are harmless.
    now = datetime.now(timezone.utc)
    event = PaymentEvent(checkout_request_id=checkout_request_id, source=source,
                         result_code=result_code, payload=payload, processing_status="unmatched")
    payment = (
        db.query(Payment).filter_by(checkout_request_id=checkout_request_id).with_for_update().first()
        if checkout_request_id else None
    )

    if payment:
        event.payment_id = payment.id
        if payment.status != "pending":  # already settled: a repeated callback
            event.processing_status = "duplicate"
        elif result_code == 0 and not receipt_number:
            event.processing_status, event.error_message = "rejected", "Success without receipt number"
        else:
            paid = result_code == 0
            payment.status = "successful" if paid else "failed"
            payment.result_code, payment.result_desc = result_code, result_desc
            payment.raw_callback, payment.callback_received_at = payload, now
            if paid:
                payment.mpesa_receipt_number, payment.paid_at = receipt_number, now
                payment.purchase.status = "paid"
            else:
                payment.failure_reason = result_desc
            event.processing_status = "applied"

    event.processed_at = now
    db.add(event)
    db.commit()
    log.info("payment event %s for %s", event.processing_status, checkout_request_id)
    return event
