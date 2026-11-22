"""Tests for POST /api/payments.

The real app is used with the test database, and the Daraja client is replaced
by a scripted fake through FastAPI's dependency_overrides, so no test touches
the network. The rules proved here: the client cannot choose the price, every
failure has the standard error body, and an unknown outcome is never reported
as "failed".
"""
import pytest
from sqlalchemy import func, select

from app.api.routes import payments as payments_route
from app.api.routes.payments import get_daraja_client
from app.config import ACCOUNT_PAYBILL, DarajaSettings
from app.integrations.mpesa.client import DarajaClient, StkPushAccepted
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaMalformedResponseError,
    DarajaRejectedError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.main import app
from app.models import Payment
from app.services.purchase_service import create_purchase

ACCEPTED = StkPushAccepted(checkout_request_id="ws_CO_1", merchant_request_id="m-1")

SETTINGS = DarajaSettings(
    environment="sandbox",
    consumer_key="KEY-123",
    consumer_secret="SECRET-456",
    shortcode="174379",
    passkey="PASSKEY-789",
    callback_url="https://example.test/callback",
    account_type=ACCOUNT_PAYBILL,
    party_b="174379",
)


class FakeStkClient:
    """Replies to stk_push() with a scripted outcome and records every call.

    `outcome` is a StkPushAccepted to return or an exception to raise. A test
    changes it after the fixture is created.
    """

    def __init__(self, outcome=ACCEPTED):
        self.outcome = outcome
        self.calls: list[dict] = []

    def stk_push(self, *, amount, phone_number, account_reference, description):
        self.calls.append({"amount": amount, "phone_number": phone_number})
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def fake(monkeypatch):
    fake_client = FakeStkClient()
    monkeypatch.setitem(app.dependency_overrides, get_daraja_client, lambda: fake_client)
    return fake_client


@pytest.fixture
def purchase(db, user, package):
    created, _ = create_purchase(db, user.id, package.id, "route-test-purchase-1")
    return created


@pytest.fixture
def fresh_client_cache():
    payments_route._build_daraja_client.cache_clear()
    yield
    payments_route._build_daraja_client.cache_clear()


def post(client, purchase_id, phone="0712345678", **extra):
    return client.post(
        "/api/payments",
        json={"purchase_id": purchase_id, "phone_number": phone, **extra},
    )


def payment_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Payment))


def stored_status(db, payment_id) -> str:
    db.expire_all()
    return db.get(Payment, payment_id).status


def test_accepted_payment_returns_201_and_a_pending_status(client, fake, purchase):
    response = post(client, purchase.id)

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "pending"  # accepted is NOT paid
    assert body["purchase_id"] == purchase.id
    assert body["amount"] == 20
    assert isinstance(body["payment_id"], int)
    assert len(fake.calls) == 1


def test_daraja_gets_the_stored_amount_and_the_normalised_phone(client, fake, purchase):
    # The client tries to choose its own price: it must have no effect.
    response = post(client, purchase.id, amount=1)

    assert response.status_code == 201
    assert response.json()["amount"] == 20
    assert fake.calls[0]["amount"] == 20
    assert fake.calls[0]["phone_number"] == "254712345678"


def test_response_never_contains_the_phone_number(client, fake, purchase):
    response = post(client, purchase.id)

    assert "254712345678" not in response.text
    assert "0712345678" not in response.text


@pytest.mark.parametrize(
    "body",
    [
        {"purchase_id": 0, "phone_number": "0712345678"},
        {"purchase_id": 1, "phone_number": "12345"},
        {"phone_number": "0712345678"},
        {"purchase_id": 1},
        {},
    ],
)
def test_invalid_requests_are_rejected_before_anything_happens(client, fake, db, body):
    response = client.post("/api/payments", json=body)

    assert response.status_code == 422
    assert fake.calls == []
    assert payment_count(db) == 0


def test_unknown_purchase_is_a_404_with_the_standard_body(client, fake):
    response = post(client, 999999)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Purchase not found.",
        "code": "purchase_not_found",
    }
    assert fake.calls == []


@pytest.mark.parametrize("status", ["paid", "failed", "expired"])
def test_purchase_that_is_not_pending_is_a_409(client, fake, db, purchase, status):
    purchase.status = status
    db.commit()

    response = post(client, purchase.id)

    assert response.status_code == 409
    assert response.json()["code"] == "purchase_not_payable"
    assert fake.calls == []


def test_double_tap_returns_409_with_the_existing_payment_id(client, fake, purchase):
    first = post(client, purchase.id)
    second = post(client, purchase.id)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "payment_already_pending"
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert len(fake.calls) == 1  # Daraja was asked only once


def test_refused_push_is_a_502_and_the_payment_is_failed(client, fake, db, purchase):
    fake.outcome = DarajaRejectedError(
        "refused", http_status=400, error_code="400.002.02", request_id="req-1"
    )

    response = post(client, purchase.id)

    body = response.json()
    assert response.status_code == 502
    assert body["code"] == "provider_rejected"
    assert stored_status(db, body["payment_id"]) == "failed"
    assert "400.002.02" not in response.text  # Daraja's codes never reach the client


def test_missing_token_is_a_503_and_the_payment_is_failed(client, fake, db, purchase):
    fake.outcome = DarajaAuthError("no push was sent")

    response = post(client, purchase.id)

    body = response.json()
    assert response.status_code == 503
    assert body["code"] == "provider_not_reached"
    assert stored_status(db, body["payment_id"]) == "failed"


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (DarajaTimeoutError("slow"), 504),
        (DarajaUnavailableError("down"), 502),
        (DarajaMalformedResponseError("odd"), 502),
    ],
)
def test_unknown_outcome_keeps_the_payment_pending(
    client, fake, db, purchase, error, expected_status
):
    fake.outcome = error

    response = post(client, purchase.id)

    body = response.json()
    assert response.status_code == expected_status
    assert body["code"] == "outcome_unknown"
    assert stored_status(db, body["payment_id"]) == "pending"  # never "failed"
    assert "fail" not in body["detail"].lower()


def test_unconfigured_daraja_is_a_503_and_records_nothing(
    client, db, purchase, monkeypatch
):
    monkeypatch.setitem(app.dependency_overrides, get_daraja_client, lambda: None)

    response = post(client, purchase.id)

    assert response.status_code == 503
    assert response.json()["code"] == "payments_not_configured"
    assert payment_count(db) == 0


def test_a_value_error_is_a_generic_500_that_leaks_nothing(client, fake, db, purchase):
    fake.outcome = ValueError("secret internal detail")

    response = post(client, purchase.id)

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "secret" not in response.text
    assert stored_status(db, db.scalars(select(Payment.id)).one()) == "failed"


def test_missing_daraja_settings_give_no_client(monkeypatch, fresh_client_cache):
    def broken_settings():
        raise RuntimeError("Set DARAJA_CONSUMER_KEY in the repository root .env or shell.")

    monkeypatch.setattr(payments_route, "daraja_settings", broken_settings)

    assert payments_route.get_daraja_client() is None


def test_the_daraja_client_is_built_once_and_reused(monkeypatch, fresh_client_cache):
    calls = []

    def counting_settings():
        calls.append(1)
        return SETTINGS

    monkeypatch.setattr(payments_route, "daraja_settings", counting_settings)

    first = payments_route.get_daraja_client()
    second = payments_route.get_daraja_client()

    # One shared client means one shared token cache.
    assert isinstance(first, DarajaClient)
    assert first is second
    assert len(calls) == 1