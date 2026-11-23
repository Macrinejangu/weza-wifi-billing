"""HTTP tests for the M-Pesa callback route (WEZA-50).

Dependencies are replaced: the test database session, a known security
policy and a fake Daraja. No network, no real configuration.
"""

import json
import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.routes import mpesa_callback
from app.api.routes.mpesa_callback import (
    ACCEPTED_REPLY,
    MAX_BODY_BYTES,
    get_callback_policy,
)
from app.api.routes.payments import get_daraja_client
from app.db.session import get_db
from app.main import app
from app.models import ActivationAttempt, Payment, PaymentEvent, Subscription, WiFiSession
from app.payments.callback_ip_policy import CallbackIpPolicy
from app.payments.callback_security import CallbackSecurityPolicy
from app.services.callback_processing import replay_callback

from test_callback_processing import PAID, UNKNOWN, FakeDaraja, body
from test_payment_settlement import make_payment, make_purchase

TOKEN = "Abc123_-" * 5  # 40 URL-safe characters
URL = f"/api/payments/mpesa/callback/{TOKEN}"


def make_policy(*, ip_enabled=False):
    return CallbackSecurityPolicy(
        ip_policy=CallbackIpPolicy.create(enabled=ip_enabled), token=TOKEN
    )


@pytest.fixture
def daraja():
    return FakeDaraja(PAID)


@pytest.fixture
def api(db, daraja, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    monkeypatch.setitem(app.dependency_overrides, get_callback_policy, make_policy)
    monkeypatch.setitem(app.dependency_overrides, get_daraja_client, lambda: daraja)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def pending(db, user, package):
    purchase = make_purchase(db, user, package)
    return purchase, make_payment(db, purchase)


def events(db):
    db.expire_all()
    return db.query(PaymentEvent).order_by(PaymentEvent.id).all()


def post(api, content, url=URL, **kwargs):
    return api.post(url, content=content, **kwargs)


def test_valid_callback_settles_the_payment_and_gets_the_accepted_reply(
    api, db, pending, daraja, caplog
):
    _, payment = pending

    # Capture only OUR loggers. The test client's own httpx logger prints
    # the full request URL (including the token), which is not our code.
    with caplog.at_level("DEBUG", logger="app"):
        response = post(api, json.dumps(body()))

    assert response.status_code == 200
    assert response.json() == ACCEPTED_REPLY
    db.expire_all()
    assert payment.status == "successful"
    assert [e.processing_status for e in events(db)] == ["applied"]

    app_logs = " ".join(
        r.getMessage()
        for r in caplog.records
        if r.name == "app" or r.name.startswith("app.")
    )
    assert app_logs  # proves our code logged something, so the check below can fail
    assert TOKEN not in app_logs  # the route and services never log the secret


def test_duplicate_delivery_settles_once_and_queries_once(api, db, pending, daraja):
    _, payment = pending

    first = post(api, json.dumps(body()))
    second = post(api, json.dumps(body()))

    assert first.status_code == second.status_code == 200
    assert [e.processing_status for e in events(db)] == ["applied", "duplicate"]
    assert daraja.calls == ["ws_CO_0001"]
    assert db.query(Payment).filter_by(status="successful").count() == 1
    subscription = db.query(Subscription).filter_by(payment_id=payment.id).one()
    session = db.query(WiFiSession).filter_by(payment_id=payment.id).one()
    assert session.subscription_id == subscription.id
    assert session.activation_status == "succeeded"
    assert subscription.start_date == session.started_at == payment.paid_at
    assert subscription.end_date == session.expires_at == payment.paid_at + timedelta(
        minutes=payment.purchase.duration_minutes
    )
    assert db.query(ActivationAttempt).filter_by(session_id=session.id).count() == 1


def test_activation_failure_preserves_the_verified_payment(api, db, pending, monkeypatch):
    _, payment = pending

    def fail_activation(**kwargs):
        raise RuntimeError("Mock router unavailable")

    monkeypatch.setattr("app.services.session_service.activate_access_device", fail_activation)
    assert post(api, json.dumps(body())).json() == ACCEPTED_REPLY
    assert post(api, json.dumps(body())).json() == ACCEPTED_REPLY

    db.expire_all()
    assert payment.status == "successful"
    session = db.query(WiFiSession).filter_by(payment_id=payment.id).one()
    assert session.activation_status == "failed"
    assert session.subscription.start_date == payment.paid_at
    assert db.query(ActivationAttempt).filter_by(session_id=session.id).count() == 1


def test_wrong_token_gets_a_plain_404_and_leaves_no_audit_row(api, db, pending):
    response = post(api, json.dumps(body()), url="/api/payments/mpesa/callback/" + "x" * 40)

    assert response.status_code == 404
    assert response.content == b""
    assert events(db) == []


def test_wrong_ip_and_wrong_token_are_indistinguishable(api, db, pending, monkeypatch):
    wrong_token = post(api, json.dumps(body()), url="/api/payments/mpesa/callback/" + "x" * 40)
    # The test client's peer address is not an allowed Safaricom IP.
    monkeypatch.setitem(
        app.dependency_overrides, get_callback_policy, lambda: make_policy(ip_enabled=True)
    )
    wrong_ip = post(api, json.dumps(body()))

    assert wrong_ip.status_code == wrong_token.status_code == 404
    assert wrong_ip.content == wrong_token.content
    assert dict(wrong_ip.headers) == dict(wrong_token.headers)
    assert events(db) == []


def test_unconfigured_endpoint_answers_404_and_records_nothing(
    api, db, pending, monkeypatch
):
    monkeypatch.setitem(app.dependency_overrides, get_callback_policy, lambda: None)

    response = post(api, json.dumps(body()))

    assert response.status_code == 404
    assert events(db) == []


def test_oversized_body_gets_413_and_is_not_stored(api, db, pending):
    response = post(api, b"{" + b" " * MAX_BODY_BYTES + b"}")

    assert response.status_code == 413
    assert events(db) == []


@pytest.mark.parametrize("declared", ["abc", "-1x", str(MAX_BODY_BYTES + 1)])
def test_bad_or_oversized_content_length_is_refused(api, db, pending, declared):
    response = post(api, b"{}", headers={"content-length": declared})

    assert response.status_code == 413
    assert events(db) == []


@pytest.mark.parametrize("junk", [b"not json at all", b"", b"[1, 2]", b"\xff\xfe"])
def test_unreadable_body_is_stored_rejected_and_answered_200(api, db, pending, junk):
    _, payment = pending

    response = post(api, junk)

    assert response.status_code == 200
    stored = events(db)
    assert [e.processing_status for e in stored] == ["rejected"]
    db.expire_all()
    assert payment.status == "pending"


def test_database_failure_while_recording_gets_503_without_internals(
    api, db, pending, monkeypatch
):
    def fail(*args, **kwargs):
        raise OperationalError("INSERT ...", {"phone": "254712345678"}, Exception("secret detail"))

    monkeypatch.setattr(mpesa_callback, "record_received_event", fail)

    response = post(api, json.dumps(body()))

    assert response.status_code == 503
    assert "secret" not in response.text
    assert "254712345678" not in response.text


def test_processing_bug_gets_a_fixed_500_and_the_event_stays_received(
    api, db, pending, monkeypatch
):
    def explode(*args, **kwargs):
        raise ValueError("internal wording must not leak")

    monkeypatch.setattr(mpesa_callback, "process_callback", explode)

    response = post(api, json.dumps(body()))

    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong.", "code": "internal_error"}
    assert [e.processing_status for e in events(db)] == ["received"]


def test_lookup_error_is_not_turned_into_a_404_by_main(api, db, pending, monkeypatch):
    def missing(*args, **kwargs):
        raise LookupError("payment 9 does not exist")

    monkeypatch.setattr(mpesa_callback, "process_callback", missing)

    response = post(api, json.dumps(body()))

    assert response.status_code == 500
    assert "payment 9" not in response.text


def test_replay_recovers_callback_that_arrived_before_request_ids(api, db, pending, daraja):
    purchase, payment = pending
    checkout, merchant = payment.checkout_request_id, payment.merchant_request_id
    payment.checkout_request_id = payment.merchant_request_id = None
    db.commit()

    assert post(api, json.dumps(body())).status_code == 200
    original = events(db)[0]
    assert original.processing_status == "unmatched"
    original_id = original.id
    assert daraja.calls == []

    payment.checkout_request_id, payment.merchant_request_id = checkout, merchant
    db.commit()
    assert replay_callback(db, daraja, original_id).outcome == "applied"
    assert replay_callback(db, daraja, original_id).outcome == "duplicate"

    audit_rows = events(db)
    assert [row.processing_status for row in audit_rows] == ["unmatched", "applied", "duplicate"]
    assert [row.payload["replay_of_event_id"] for row in audit_rows[1:]] == [original_id, original_id]
    assert daraja.calls == [checkout]
    assert payment.status == "successful"
    assert purchase.status == "paid"


def test_replay_recovers_inconclusive_query(api, db, pending, daraja):
    _, payment = pending
    daraja.result = UNKNOWN
    assert post(api, json.dumps(body())).status_code == 200
    original = events(db)[0]
    assert original.processing_status == "rejected"
    assert payment.status == "pending"

    daraja.result = PAID
    assert replay_callback(db, daraja, original.id).outcome == "applied"
    assert payment.status == "successful"


def test_replay_rejects_callback_with_wrong_amount(api, db, pending, daraja):
    _, payment = pending
    assert post(api, json.dumps(body(amount=99999))).status_code == 200
    event = events(db)[0]

    with pytest.raises(ValueError, match="not eligible"):
        replay_callback(db, daraja, event.id)

    assert len(events(db)) == 1
    assert daraja.calls == []
    assert payment.status == "pending"


def test_uvicorn_access_log_omits_callback_path_and_keeps_health(caplog):
    logger = logging.getLogger("uvicorn.access")
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info('%s - "%s %s HTTP/%s" %d', "peer", "POST", URL, "1.1", 404)
        logger.info('%s - "%s %s HTTP/%s" %d', "peer", "GET", "/health", "1.1", 200)

    assert TOKEN not in caplog.text
    assert "GET /health" in caplog.text
