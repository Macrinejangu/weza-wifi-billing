"""Database tests for settle_payment (WEZA-50).

Each test builds a purchase, a payment and an audit event, calls
settle_payment, and checks the rows. The verdict and the status-query
outcome are passed in directly, so these tests focus on what settlement
does with them; the verdict and query logic have their own tests.
"""

import pytest
from sqlalchemy import text

from app.integrations.mpesa.callback_payload import parse_stk_callback
from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.models import Payment, PaymentEvent, Purchase
from app.payments.callback_verification import CallbackVerdict
from app.payments.settlement_plan import SettlementAction

from app.payments.result_codes import failure_reason_for
from app.services import payment_settlement
from app.services.payment_event_service import EventSource, record_received_event
from app.services.payment_settlement import settle_payment

PHONE = "254712345678"
AMOUNT = 20
CHECKOUT = "ws_CO_0001"


def make_purchase(db, user, package, *, key="purchase-1", status="pending"):
    purchase = Purchase(
        user_id=user.id,
        package_id=package.id,
        amount=AMOUNT,
        package_name=package.name,
        duration_minutes=60,
        download_speed_mbps=5,
        upload_speed_mbps=2,
        status=status,
        idempotency_key=key,
    )
    db.add(purchase)
    db.commit()
    return purchase


def make_payment(db, purchase, *, checkout=CHECKOUT, status="pending", receipt=None):
    payment = Payment(
        purchase_id=purchase.id,
        amount=AMOUNT,
        phone_number=PHONE,
        status=status,
        checkout_request_id=checkout,
        merchant_request_id=f"mr-{checkout}",
        mpesa_receipt_number=receipt,
        idempotency_key=f"pay-{checkout}",
    )
    db.add(payment)
    db.commit()
    return payment


def new_event(db):
    return record_received_event(
        db, source=EventSource.CALLBACK, payload={"test": True}
    )


def success_callback(checkout=CHECKOUT, receipt="QGH1234ABC"):
    return parse_stk_callback(
        {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"mr-{checkout}",
                    "CheckoutRequestID": checkout,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": AMOUNT},
                            {"Name": "MpesaReceiptNumber", "Value": receipt},
                            {"Name": "TransactionDate", "Value": 20261123101500},
                            {"Name": "PhoneNumber", "Value": int(PHONE)},
                        ]
                    },
                }
            }
        }
    )


def failure_callback(checkout=CHECKOUT):
    return parse_stk_callback(
        {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"mr-{checkout}",
                    "CheckoutRequestID": checkout,
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user",
                }
            }
        }
    )


def run(db, payment, event_id, verdict, outcome, callback):
    return settle_payment(
        db,
        event_id=event_id,
        payment_id=payment.id,
        verdict=verdict,
        query_outcome=outcome,
        callback=callback,
        raw_payload={"test": True},
    )


def event_row(db, event_id):
    db.expire_all()
    return db.get(PaymentEvent, event_id)


def test_confirmed_success_marks_payment_successful_and_purchase_paid(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    result = run(
        db, payment, event_id,
        CallbackVerdict.SUCCESS_MATCHED, StkQueryOutcome.PAID, success_callback(),
    )

    assert result.action is SettlementAction.APPLY_SUCCESS
    assert payment.status == "successful"
    assert payment.mpesa_receipt_number == "QGH1234ABC"
    assert payment.paid_at is not None
    assert payment.callback_received_at is not None
    assert payment.raw_callback == {"test": True}
    assert purchase.status == "paid"
    event = event_row(db, event_id)
    assert event.processing_status == "applied"
    assert event.payment_id == payment.id
    assert event.processed_at is not None


def test_duplicate_callback_changes_nothing(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    first = new_event(db)
    run(db, payment, first, CallbackVerdict.SUCCESS_MATCHED,
        StkQueryOutcome.PAID, success_callback())
    paid_at = payment.paid_at

    second = new_event(db)
    result = run(db, payment, second, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback())

    assert result.action is SettlementAction.ALREADY_SETTLED
    assert payment.paid_at == paid_at
    assert event_row(db, second).processing_status == "duplicate"
    successful = db.query(Payment).filter_by(status="successful").count()
    assert successful == 1


@pytest.mark.parametrize(
    "outcome", [StkQueryOutcome.FAILED, StkQueryOutcome.UNKNOWN, None]
)
def test_success_callback_without_query_confirmation_stays_pending(
    db, user, package, outcome
):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 outcome, success_callback())

    assert result.action is SettlementAction.KEEP_PENDING
    assert payment.status == "pending"
    assert payment.mpesa_receipt_number is None
    assert purchase.status == "pending"
    assert event_row(db, event_id).processing_status == "rejected"


@pytest.mark.parametrize(
    "outcome", [StkQueryOutcome.PAID, StkQueryOutcome.UNKNOWN, None]
)
def test_forged_failure_cannot_cancel_a_payment(db, user, package, outcome):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.FAILURE_MATCHED,
                 outcome, failure_callback())

    assert result.action is SettlementAction.KEEP_PENDING
    assert payment.status == "pending"


def test_confirmed_failure_marks_payment_failed_and_keeps_purchase_open(
    db, user, package
):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.FAILURE_MATCHED,
                 StkQueryOutcome.FAILED, failure_callback())

    assert result.action is SettlementAction.APPLY_FAILURE
    assert payment.status == "failed"
    assert payment.result_code == 1032
    assert payment.failure_reason == failure_reason_for(1032).value
    assert payment.mpesa_receipt_number is None
    assert purchase.status == "pending"  # customer may pay again
    assert event_row(db, event_id).processing_status == "applied"


def test_late_success_repairs_an_expired_payment(db, user, package):
    purchase = make_purchase(db, user, package, status="expired")
    payment = make_payment(db, purchase, status="expired")
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback())

    assert result.action is SettlementAction.APPLY_SUCCESS
    assert payment.status == "successful"
    assert purchase.status == "paid"


def test_late_success_after_failure_is_rejected_and_recorded(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase, status="failed")
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback())

    assert result.action is SettlementAction.REJECT
    assert payment.status == "failed"
    assert purchase.status == "pending"
    assert event_row(db, event_id).processing_status == "rejected"


def test_success_for_an_already_paid_purchase_is_rejected_for_staff(
    db, user, package
):
    purchase = make_purchase(db, user, package, status="paid")
    make_payment(db, purchase, checkout="ws_CO_other", status="successful",
                 receipt="OTHER00001")
    late = make_payment(db, purchase, checkout="ws_CO_late", status="expired")
    event_id = new_event(db)

    result = run(db, late, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback(checkout="ws_CO_late"))

    assert result.action is SettlementAction.REJECT
    assert late.status == "expired"
    event = event_row(db, event_id)
    assert event.processing_status == "rejected"
    assert "staff review" in event.error_message


def test_unique_index_collision_is_caught_and_recorded(db, user, package):
    # Inconsistent data on purpose: the purchase still says pending although
    # another payment for it is successful. The purchase check passes, so
    # only the database's unique index can stop the second success.
    purchase = make_purchase(db, user, package, status="pending")
    make_payment(db, purchase, checkout="ws_CO_other", status="successful",
                 receipt="OTHER00001")
    late = make_payment(db, purchase, checkout="ws_CO_late", status="expired")
    event_id = new_event(db)

    result = run(db, late, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback(checkout="ws_CO_late"))

    assert result.action is SettlementAction.REJECT
    assert late.status == "expired"
    assert late.mpesa_receipt_number is None
    assert purchase.status == "pending"  # savepoint rollback undid the purchase change too
    event = event_row(db, event_id)
    assert event.processing_status == "rejected"
    assert "conflicts" in event.error_message


def test_receipt_already_used_by_another_payment_is_rejected(db, user, package):
    first_purchase = make_purchase(db, user, package, key="purchase-1")
    make_payment(db, first_purchase, checkout="ws_CO_first", status="successful",
                 receipt="QGH1234ABC")
    second_purchase = make_purchase(db, user, package, key="purchase-2")
    second = make_payment(db, second_purchase, checkout="ws_CO_second")
    event_id = new_event(db)

    result = run(db, second, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID,
                 success_callback(checkout="ws_CO_second", receipt="QGH1234ABC"))

    assert result.action is SettlementAction.REJECT
    assert second.status == "pending"
    assert second_purchase.status == "pending"


@pytest.mark.parametrize(
    "verdict",
    [
        CallbackVerdict.REJECTED_AMOUNT_MISMATCH,
        CallbackVerdict.REJECTED_PHONE_MISMATCH,
        CallbackVerdict.REJECTED_CHECKOUT_ID_MISMATCH,
    ],
)
def test_callback_that_failed_verification_changes_nothing(
    db, user, package, verdict
):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    # Even with a PAID query answer, a mismatched callback must not apply.
    result = run(db, payment, event_id, verdict,
                 StkQueryOutcome.PAID, success_callback())

    assert result.action is SettlementAction.REJECT
    assert payment.status == "pending"
    assert event_row(db, event_id).processing_status == "rejected"


def test_stale_session_state_is_refreshed_under_the_lock(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    assert payment.status == "pending"  # now cached in the session
    # Simulate another worker settling it meanwhile, behind the session's back.
    db.execute(
        text("UPDATE payments SET status = 'successful' WHERE id = :id"),
        {"id": payment.id},
    )
    event_id = new_event(db)

    result = run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
                 StkQueryOutcome.PAID, success_callback())

    # If the stale "pending" were used, this would try to apply success again.
    assert result.action is SettlementAction.ALREADY_SETTLED


def test_an_event_cannot_be_settled_twice(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)
    run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
        StkQueryOutcome.PAID, success_callback())

    with pytest.raises(ValueError):
        run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
            StkQueryOutcome.PAID, success_callback())


def test_unknown_payment_id_raises(db, user, package):
    event_id = new_event(db)
    with pytest.raises(LookupError):
        settle_payment(
            db,
            event_id=event_id,
            payment_id=999999,
            verdict=CallbackVerdict.SUCCESS_MATCHED,
            query_outcome=StkQueryOutcome.PAID,
            callback=success_callback(),
            raw_payload={"test": True},
        )


def test_crash_after_payment_update_rolls_everything_back(
    db, user, package, monkeypatch
):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase)
    event_id = new_event(db)

    def crash(*args, **kwargs):
        raise RuntimeError("simulated crash")

    # The payment is already modified in memory when this runs.
    monkeypatch.setattr(payment_settlement, "mark_event_outcome", crash)

    with pytest.raises(RuntimeError):
        run(db, payment, event_id, CallbackVerdict.SUCCESS_MATCHED,
            StkQueryOutcome.PAID, success_callback())

    db.expire_all()
    assert payment.status == "pending"
    assert purchase.status == "pending"
    assert event_row(db, event_id).processing_status == "received"