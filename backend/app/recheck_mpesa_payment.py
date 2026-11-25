"""Check a timed-out sandbox payment using its saved provider reference."""

import argparse
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.payments import get_daraja_client, require_sandbox_payments_enabled
from app.db.session import database_sessions
from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.models import Payment, PaymentEvent
from app.payments.statuses import PaymentStatus

RECHECKABLE = (PaymentStatus.PENDING, PaymentStatus.EXPIRED)


def recheck_payment(db: Session, daraja, payment_id: int) -> str:
    """Record the provider's result. Only a verified failure can settle here."""
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise LookupError("Payment not found")
    if payment.status not in RECHECKABLE:
        return payment.status
    if (
        payment.payment_method != "mpesa"
        or not payment.checkout_request_id
        or not payment.merchant_request_id
        or (payment.raw_callback or {}).get("mock") is True
    ):
        raise ValueError("This payment has no verified Daraja request reference")

    checkout_id = payment.checkout_request_id
    db.rollback()  # release the connection before the external request
    result = daraja.stk_query(checkout_id)
    current = db.scalar(
        select(Payment).where(Payment.id == payment_id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None or current.checkout_request_id != checkout_id:
        raise ValueError("The payment reference changed before the result arrived")

    status = "rejected"
    note = "No conclusive provider result"
    if current.status not in RECHECKABLE:
        status, note = "duplicate", "The payment was already settled"
    elif result.outcome == StkQueryOutcome.FAILED:
        current.status = PaymentStatus.FAILED
        current.result_code = result.result_code
        current.failure_reason = result.failure_reason.value
        status, note = "applied", None
    elif result.outcome == StkQueryOutcome.PAID:
        note = "Provider reports paid. A verified receipt is still required."

    current_status = current.status
    db.add(PaymentEvent(
        payment_id=current.id, source="query", checkout_request_id=checkout_id,
        result_code=result.result_code, payload={"outcome": result.outcome.value},
        processing_status=status, error_message=note, processed_at=datetime.now(UTC),
    ))
    db.commit()
    return current_status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payment_id", type=int)
    args = parser.parse_args()
    try:
        require_sandbox_payments_enabled()
        daraja = get_daraja_client()
        if daraja is None:
            raise ValueError("Daraja sandbox credentials are unavailable")
        with database_sessions()() as db:
            result = recheck_payment(db, daraja, args.payment_id)
    except Exception as error:
        parser.exit(1, f"Sandbox payment could not be checked ({type(error).__name__}).\n")
    print(f"Payment {args.payment_id}: {result}")


if __name__ == "__main__":
    main()
