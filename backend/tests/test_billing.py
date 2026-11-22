import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import ActivationAttempt, Payment, User
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import apply_payment_result, create_payment
from app.services.purchase_service import create_purchase
from app.services.session_service import activate_session, create_session

PHONE = "254712345678"


def paid_payment(db, user, package, ok=True):
    purchase, _ = create_purchase(db, user.id, package.id, "key-12345")
    return process_mock_payment(db, create_payment(db, purchase.id, PHONE).id, ok)


def test_get_packages(client, package):
    assert client.get("/api/packages/").json()[0]["name"] == "1 Hour"


def test_purchase_copies_price_and_repeated_key_gives_same_purchase(client, user, package):
    body, key = {"user_id": user.id, "package_id": package.id}, {"Idempotency-Key": "key-12345"}
    first = client.post("/api/purchases", json=body, headers=key)
    again = client.post("/api/purchases", json=body, headers=key)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["id"] == again.json()["id"] and first.json()["amount"] == 20


def test_callback_updates_payment_and_duplicate_is_ignored(db, user, package):
    purchase, _ = create_purchase(db, user.id, package.id, "key-12345")
    payment = create_payment(db, purchase.id, PHONE, "ws_1")
    assert apply_payment_result(db, "ws_1", 0, "OK", "REC1").processing_status == "applied"
    assert (payment.status, purchase.status) == ("successful", "paid")
    assert apply_payment_result(db, "ws_1", 1, "late").processing_status == "duplicate"
    assert payment.status == "successful"


def test_unpaid_payment_cannot_start_a_session(db, user, package):
    with pytest.raises(ValueError):
        create_session(db, paid_payment(db, user, package, ok=False).id)


def test_timer_starts_only_after_router_confirms(db, user, package):
    session = create_session(db, paid_payment(db, user, package).id)
    assert session.started_at is None
    failed = activate_session(db, session.id, lambda i: {"status": "ERROR"})
    assert failed.activation_status == "failed" and failed.started_at is None
    active = activate_session(db, session.id, lambda i: {"status": "ACTIVE"})
    assert active.status == "ACTIVE" and (active.expires_at - active.started_at).seconds == 3600


def test_database_allows_one_successful_payment_per_purchase(db, user, package):
    purchase, _ = create_purchase(db, user.id, package.id, "key-12345")
    for receipt in ("A1", "A2"):
        db.add(Payment(purchase_id=purchase.id, amount=20, phone_number=PHONE,
                       status="successful", mpesa_receipt_number=receipt))
    with pytest.raises(IntegrityError):
        db.commit()


def test_unsafe_endpoints_are_closed(client, monkeypatch):
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "false")
    assert client.post("/api/test-activation").status_code in (404, 405)
    assert client.post("/api/payments/mock", json={"purchase_id": 1, "phone_number": PHONE}).status_code == 404

def test_mock_purchase_payment_and_activation(client, user, package):
    purchase = client.post(
        "/api/purchases",
        json={"user_id": user.id, "package_id": package.id},
        headers={"Idempotency-Key": "mock-activation"},
    )
    assert purchase.status_code == 201
    payment = client.post("/api/payments/mock", json={
        "purchase_id": purchase.json()["id"], "phone_number": PHONE,
    })
    assert payment.status_code == 200
    assert payment.json()["status"] == "successful"
    created = client.post("/api/sessions", json={"payment_id": payment.json()["id"]})
    assert created.status_code == 201
    assert created.json()["started_at"] is None
    path = f"/api/sessions/{created.json()['id']}"
    active = client.post(f"{path}/activate")
    assert active.status_code == 200
    assert active.json()["status"] == "ACTIVE"
    assert active.json()["started_at"] and active.json()["expires_at"]
    assert client.post(f"{path}/activate").json() == active.json()
    assert client.get(path).json() == active.json()


def test_package_writes_require_mock_mode(client, db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    staff = User(
        full_name="Staff",
        email="billing-staff@weza.local",
        password_hash=hash_password("correct-horse-battery"),
        role="operator",
        status="active",
    )
    db.add(staff)
    db.commit()

    login = client.post("/api/auth/login", json={
        "email": "billing-staff@weza.local",
        "password": "correct-horse-battery",
    })
    assert login.status_code == 200
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    monkeypatch.delenv("ENABLE_MOCK_PAYMENTS", raising=False)
    payload = {
        "name": "Demo", "service_type": "hotspot", "price": 20,
        "duration_minutes": 60, "download_speed_mbps": 5, "upload_speed_mbps": 2,
    }
    assert client.post("/api/packages/", json=payload, headers=headers).status_code == 404

    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "true")
    assert client.post(
        "/api/packages/",
        json={**payload, "duration_minutes": 0},
        headers=headers,
    ).status_code == 422

    created = client.post("/api/packages/", json=payload, headers=headers)
    assert created.status_code == 200
    assert client.delete(
        f"/api/packages/{created.json()['id']}", headers=headers
    ).status_code == 200
    assert client.get("/api/packages/").json() == []


def test_mock_payment_is_rejected_before_mikrotik_activation(
    db, user, package, monkeypatch
):
    import app.services.session_service as session_service

    monkeypatch.setenv("ROUTER_MODE", "mikrotik")

    provider_called = False

    def unexpected_router_call(**kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("MikroTik provider must not be called for mock payment")

    monkeypatch.setattr(
        session_service, "activate_access_device", unexpected_router_call
    )

    payment = paid_payment(db, user, package)
    assert payment.raw_callback == {"mock": True}

    session = create_session(db, payment.id)
    result = activate_session(db, session.id)

    assert provider_called is False
    assert result.status == "FAILED"
    assert result.activation_status == "failed"
    assert "Mock payment cannot activate access" in result.failure_reason

    attempt = (
        db.query(ActivationAttempt)
        .filter_by(session_id=session.id)
        .one()
    )
    assert attempt.status == "failed"
    assert "Mock payment cannot activate access" in attempt.error_message
    assert attempt.completed_at is not None


def test_unconfirmed_activation_reuses_attempt_until_router_confirms(
    client, db, user, package, monkeypatch
):
    from app.services import session_service
    from app.services.router import RouterActivationUnconfirmed

    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    payment = paid_payment(db, user, package)
    payment.raw_callback = {"test": "verified payment fixture"}
    db.commit()
    session = create_session(db, payment.id, "AA:BB:CC:DD:EE:FF", "10.20.0.254")
    calls = []

    def activate_once(**kwargs):
        calls.append("activate")
        raise RouterActivationUnconfirmed("Router timed out")

    def verify_only(**kwargs):
        assert kwargs["verify_only"] is True
        calls.append("verify")
        if calls.count("verify") == 1:
            raise RouterActivationUnconfirmed("Router has not confirmed the session")
        return {"status": "ACTIVE"}

    monkeypatch.setattr(session_service, "activate_access_device", activate_once)
    monkeypatch.setattr(session_service, "activate_hotspot_device", verify_only)
    endpoint = f"/api/sessions/{session.id}/activate"

    for _ in range(2):
        response = client.post(endpoint)
        assert response.status_code == 202
        assert response.json()["activation_status"] == "waiting"
        assert response.json()["started_at"] is None

    response = client.post(endpoint)
    assert response.status_code == 200
    assert response.json()["activation_status"] == "succeeded"
    assert response.json()["started_at"] is not None
    assert client.post(endpoint).status_code == 200
    assert calls == ["activate", "verify", "verify"]

    attempt = db.query(ActivationAttempt).filter_by(session_id=session.id).one()
    assert attempt.status == "succeeded"
    assert attempt.completed_at is not None
