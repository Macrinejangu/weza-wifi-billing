from sqlalchemy import select

from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import PaymentEvent, Subscription, WiFiSession
from app.payments.result_codes import FailureReason
from app.recheck_mpesa_payment import recheck_payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase


class Query:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def stk_query(self, checkout_id):
        self.calls.append(checkout_id)
        return self.result


def pending_payment(db, user, package):
    purchase, _ = create_purchase(db, user.id, package.id, "daraja-recheck-test")
    payment = create_payment(db, purchase.id, "254712345678", "test-checkout")
    payment.merchant_request_id = "test-merchant"
    db.commit()
    return payment


def test_failed_provider_query_releases_pending_payment_without_grant(db, user, package):
    payment = pending_payment(db, user, package)
    provider = Query(StkQueryResult(StkQueryOutcome.FAILED, 1037, FailureReason.TIMED_OUT))
    assert recheck_payment(db, provider, payment.id) == "failed"
    assert recheck_payment(db, provider, payment.id) == "failed"
    assert provider.calls == ["test-checkout"]
    assert payment.failure_reason == "timed_out"
    assert payment.purchase.status == "pending"
    event = db.scalar(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id))
    assert (event.source, event.processing_status, event.result_code) == ("query", "applied", 1037)
    assert db.query(Subscription).count() == db.query(WiFiSession).count() == 0


def test_paid_query_alone_never_grants_access(db, user, package):
    payment = pending_payment(db, user, package)
    provider = Query(StkQueryResult(StkQueryOutcome.PAID, 0))
    assert recheck_payment(db, provider, payment.id) == "pending"
    assert payment.paid_at is None
    event = db.scalar(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id))
    assert event.processing_status == "rejected"
    assert db.query(Subscription).count() == db.query(WiFiSession).count() == 0
