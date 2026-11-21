"""Tests for initiate_payment(): the Daraja call and recording its outcome.

A scripted fake stands in for the Daraja client, so no test touches the
network. The rules proved here: one push per payment and never a retry, a
payment is marked failed ONLY when nothing could have reached the phone, and
every uncertain outcome leaves it pending.
"""
import logging

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.mpesa.client import StkPushAccepted
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaError,
    DarajaMalformedResponseError,
    DarajaRejectedError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.models import Payment
from app.payments.payment_service_errors import (
    OutcomeUnknown,
    PaymentAlreadyPending,
    ProviderNotReached,
    ProviderRejected,
    PurchaseNotFound,
)
from app.services import mpesa_payment_service
from app.services.mpesa_payment_service import initiate_payment
from app.services.purchase_service import create_purchase

PHONE = "254712345678"
ACCEPTED = StkPushAccepted(checkout_request_id="ws_CO_1", merchant_request_id="m-1")


class FakeStkClient:
    """Replies to stk_push() with a scripted outcome and records every call.

    `outcome` is a StkPushAccepted to return or an exception to raise.
    `during_call` runs inside stk_push, to observe or change the world while
    "Daraja is working".
    """

    def __init__(self, outcome=ACCEPTED, during_call=None):
        self.outcome = outcome
        self.during_call = during_call
        self.calls: list[dict] = []

    def stk_push(self, *, amount, phone_number, account_reference, description):
        self.calls.append(
            {
                "amount": amount,
                "phone_number": phone_number,
                "account_reference": account_reference,
                "description": description,
            }
        )
        if self.during_call is not None:
            self.during_call()
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def purchase(db, user, package):
    created, _ = create_purchase(db, user.id, package.id, "mpesa-initiation-test-1")
    return created


def fetch(db, payment_id):
    """Read a payment fresh from the database, ignoring cached objects."""
    db.expire_all()
    return db.get(Payment, payment_id)


def only_payment(db):
    db.expire_all()
    return db.scalars(select(Payment)).one()


def test_accepted_push_stores_the_daraja_ids_and_stays_pending(db, purchase):
    fake = FakeStkClient()

    result = initiate_payment(db, fake, purchase.id, PHONE)

    payment = fetch(db, result.payment_id)
    assert result.checkout_request_id == "ws_CO_1"
    assert result.amount == 20
    assert payment.status == "pending"  # accepted is NOT paid
    assert payment.checkout_request_id == "ws_CO_1"
    assert payment.merchant_request_id == "m-1"
    # Set explicitly with Python time, so it is later than initiated_at.
    assert payment.updated_at >= payment.initiated_at
    assert len(fake.calls) == 1


def test_daraja_receives_the_stored_amount_the_phone_and_short_texts(db, purchase):
    fake = FakeStkClient()

    result = initiate_payment(db, fake, purchase.id, PHONE)

    call = fake.calls[0]
    assert call["amount"] == 20  # from the purchase, never from the client
    assert call["phone_number"] == PHONE
    assert call["account_reference"] == f"WEZA{result.payment_id}"
    assert len(call["account_reference"]) <= 12
    assert len(call["description"]) <= 13
    assert call["account_reference"].isalnum()
    assert call["description"].isalnum()


def test_no_database_transaction_is_open_during_the_daraja_call(db, purchase):
    seen = []
    fake = FakeStkClient(during_call=lambda: seen.append(db.in_transaction()))

    initiate_payment(db, fake, purchase.id, PHONE)

    # An open transaction here would hold the purchase lock for the whole call.
    assert seen == [False]


def test_refused_push_marks_the_payment_failed(db, purchase):
    refusal = DarajaRejectedError(
        "refused", http_status=400, error_code="400.002.02", request_id="req-1"
    )
    fake = FakeStkClient(refusal)

    with pytest.raises(ProviderRejected) as info:
        initiate_payment(db, fake, purchase.id, PHONE)

    payment = fetch(db, info.value.payment_id)
    assert payment.status == "failed"
    assert payment.failure_reason == "provider_rejected"
    assert payment.checkout_request_id is None
    assert len(fake.calls) == 1


def test_a_new_attempt_is_allowed_after_a_refusal(db, purchase):
    refusal = DarajaRejectedError(
        "refused", http_status=400, error_code=None, request_id=None
    )
    with pytest.raises(ProviderRejected):
        initiate_payment(db, FakeStkClient(refusal), purchase.id, PHONE)

    second = initiate_payment(db, FakeStkClient(), purchase.id, PHONE)

    assert second.checkout_request_id == "ws_CO_1"
    assert db.scalars(select(Payment)).all().__len__() == 2


def test_missing_token_marks_the_payment_failed_and_nothing_was_sent(db, purchase):
    fake = FakeStkClient(DarajaAuthError("no push was sent"))

    with pytest.raises(ProviderNotReached) as info:
        initiate_payment(db, fake, purchase.id, PHONE)

    payment = fetch(db, info.value.payment_id)
    assert payment.status == "failed"
    assert payment.failure_reason == "provider_not_reached"


@pytest.mark.parametrize(
    ("error", "timed_out"),
    [
        (DarajaTimeoutError("slow"), True),
        (DarajaUnavailableError("down"), False),
        (DarajaMalformedResponseError("odd"), False),
        (DarajaError("unrecognised kind"), False),
    ],
)
def test_uncertain_outcomes_leave_the_payment_pending(db, purchase, error, timed_out):
    fake = FakeStkClient(error)

    with pytest.raises(OutcomeUnknown) as info:
        initiate_payment(db, fake, purchase.id, PHONE)

    payment = fetch(db, info.value.payment_id)
    assert info.value.timed_out is timed_out
    assert payment.status == "pending"  # never "failed": we do not know
    assert payment.checkout_request_id is None
    assert len(fake.calls) == 1  # never retried


def test_after_an_unknown_outcome_a_second_attempt_is_blocked(db, purchase):
    first = FakeStkClient(DarajaTimeoutError("slow"))
    with pytest.raises(OutcomeUnknown) as unknown:
        initiate_payment(db, first, purchase.id, PHONE)

    second = FakeStkClient()
    with pytest.raises(PaymentAlreadyPending) as blocked:
        initiate_payment(db, second, purchase.id, PHONE)

    # The customer may already have a prompt: Daraja must not be asked again.
    assert blocked.value.payment_id == unknown.value.payment_id
    assert second.calls == []


def test_a_second_tap_after_success_does_not_call_daraja_again(db, purchase):
    initiate_payment(db, FakeStkClient(), purchase.id, PHONE)

    second = FakeStkClient()
    with pytest.raises(PaymentAlreadyPending):
        initiate_payment(db, second, purchase.id, PHONE)

    assert second.calls == []


def test_a_value_error_from_the_client_marks_the_payment_failed(db, purchase):
    fake = FakeStkClient(ValueError("bad request body"))

    with pytest.raises(ValueError):
        initiate_payment(db, fake, purchase.id, PHONE)

    payment = only_payment(db)
    assert payment.status == "failed"
    assert payment.failure_reason == "request_invalid"


def test_unknown_purchase_never_reaches_daraja(db):
    fake = FakeStkClient()

    with pytest.raises(PurchaseNotFound):
        initiate_payment(db, fake, 999999, PHONE)

    assert fake.calls == []


def test_failure_to_store_the_ids_is_reported_and_logs_the_checkout_id(
    db, purchase, monkeypatch, caplog
):
    def broken_store(db, payment_id, accepted):
        raise SQLAlchemyError("database went away")

    monkeypatch.setattr(mpesa_payment_service, "_record_accepted", broken_store)
    caplog.set_level(logging.ERROR)

    with pytest.raises(OutcomeUnknown):
        initiate_payment(db, FakeStkClient(), purchase.id, PHONE)

    payment = only_payment(db)
    assert payment.status == "pending"
    assert payment.checkout_request_id is None
    # Staff can reconcile the prompt the customer received from this line.
    assert "ws_CO_1" in caplog.text


def test_payment_expired_during_the_call_is_reported_and_logged(
    db, purchase, caplog
):
    def expire_it():
        db.execute(update(Payment).values(status="expired"))
        db.commit()

    caplog.set_level(logging.ERROR)

    with pytest.raises(OutcomeUnknown):
        initiate_payment(
            db, FakeStkClient(during_call=expire_it), purchase.id, PHONE
        )

    payment = only_payment(db)
    assert payment.status == "expired"  # we did not overwrite it
    assert payment.checkout_request_id is None
    assert "ws_CO_1" in caplog.text


def test_logs_have_the_ids_and_never_the_full_phone_number(db, purchase, caplog):
    caplog.set_level(logging.INFO)

    result = initiate_payment(db, FakeStkClient(), purchase.id, PHONE)

    assert f"payment_id={result.payment_id}" in caplog.text
    assert "ws_CO_1" in caplog.text
    assert PHONE not in caplog.text