import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_token
from app.models import ActivationAttempt, Payment, User
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import apply_payment_result, create_payment
from app.services.purchase_service import create_purchase
from app.services.session_service import (
    activate_session,
    create_session,
    sandbox_router_activation_allowed,
)

PHONE = "254712345678"


def staff_headers(db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    staff = User(full_name="Staff", email="session-staff@weza.local", password_hash="x", role="operator")
    db.add(staff)
    db.commit()
    return {"Authorization": f"Bearer {create_token(staff.id)}"}


def paid_payment(db, user, package, ok=True):
    purchase, _ = create_purchase(db, user.id, package.id, "key-12345")
    return process_mock_payment(db, create_payment(db, purchase.id, PHONE).id, ok)


def verified_device_session(db, user, package):
    """A session for a verified (non-mock) payment on a purchase with a device."""
    purchase, _ = create_purchase(
        db, user.id, package.id, "key-12345",
        device_mac="AA:BB:CC:DD:EE:FF", device_ip="10.20.0.254",
    )
    payment = process_mock_payment(db, create_payment(db, purchase.id, PHONE).id, True)
    payment.raw_callback = {"test": "verified payment fixture"}
    db.commit()
    return create_session(db, payment.id)


def test_checkout_binds_verified_device_to_session(db, user, package, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import billing
    from app.db.session import get_db
    from app.main import app
    from app.models import Purchase

    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "true")
    monkeypatch.setenv("ENABLE_DIRECT_HOTSPOT_CHECKOUT", "true")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    mac = "8A:AA:52:95:B9:BB"
    ip = "10.20.0.254"

    def lookup(address):
        assert address == ip
        return mac

    monkeypatch.setattr(billing, "resolve_hotspot_device", lookup)
    checkout = {"user_id": user.id, "package_id": package.id}
    headers = {"Idempotency-Key": "checkout-verified"}
    with TestClient(app, client=(ip, 50000)) as hotspot:
        reference_url = "/api/checkout/device-reference"
        forwarded = hotspot.post(reference_url, json=checkout, headers={
            **headers, "X-Forwarded-For": "10.20.0.253",
        })
        assert forwarded.status_code == 400
        reference = hotspot.post(reference_url, json=checkout, headers=headers)
        assert reference.status_code == 200
        verified_checkout = {**checkout, **reference.json()}

        for bad_checkout, bad_headers in (
            ({**checkout, "device_reference": "unknown"}, headers),
            (verified_checkout, {"Idempotency-Key": "another-checkout"}),
        ):
            rejected = hotspot.post("/api/purchases", json=bad_checkout, headers=bad_headers)
            assert rejected.status_code == 400

        purchased = hotspot.post("/api/purchases", json=verified_checkout, headers=headers)
        assert purchased.status_code == 201
        again = hotspot.post("/api/purchases", json=verified_checkout, headers=headers)
        assert again.status_code == 200
        assert again.json()["id"] == purchased.json()["id"]

    purchase = db.get(Purchase, purchased.json()["id"])
    assert (purchase.device_mac_address, purchase.device_ip_address) == (mac, ip)
    payment = process_mock_payment(db, create_payment(db, purchase.id, PHONE).id)
    with pytest.raises(ValueError, match="does not match the purchase"):
        create_session(db, payment.id, "AA:BB:CC:DD:EE:FF", ip)
    session = create_session(db, payment.id)
    assert (session.device_mac_address, session.device_ip_address) == (mac, ip)

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

def test_mock_purchase_payment_and_activation(client, db, user, package, monkeypatch):
    headers = staff_headers(db, monkeypatch)
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
    assert client.post(f"{path}/activate").status_code == 401  # staff only
    active = client.post(f"{path}/activate", headers=headers)
    assert active.status_code == 200
    assert active.json()["status"] == "ACTIVE"
    assert active.json()["started_at"] and active.json()["expires_at"]
    assert client.post(f"{path}/activate", headers=headers).json() == active.json()
    assert client.get(path, headers=headers).json() == active.json()


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
    monkeypatch.setenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", "true")
    purchase, _ = create_purchase(
        db, user.id, package.id, "key-12345",
        device_mac="AA:BB:CC:DD:EE:FF", device_ip="10.20.0.254",
    )
    payment = process_mock_payment(db, create_payment(db, purchase.id, PHONE).id, True)
    payment.raw_callback = {"test": "verified payment fixture"}
    db.commit()
    session = create_session(db, payment.id)
    calls = []

    grant_ids = set()

    def router_call(**kwargs):
        grant_ids.add(kwargs["grant_id"])
        if not kwargs.get("verify_only"):
            calls.append("activate")
            raise RouterActivationUnconfirmed("Router timed out")
        calls.append("verify")
        if calls.count("verify") == 1:
            raise RouterActivationUnconfirmed("Router has not confirmed the session")
        return {"status": "ACTIVE"}

    monkeypatch.setattr(session_service, "activate_hotspot_device", router_call)
    endpoint = f"/api/sessions/{session.id}/activate"
    headers = staff_headers(db, monkeypatch)

    for _ in range(2):
        response = client.post(endpoint, headers=headers)
        assert response.status_code == 202
        assert response.json()["activation_status"] == "waiting"
        assert response.json()["started_at"] is None

    response = client.post(endpoint, headers=headers)
    assert response.status_code == 200
    assert response.json()["activation_status"] == "succeeded"
    assert response.json()["started_at"] is not None
    assert client.post(endpoint, headers=headers).status_code == 200
    assert calls == ["activate", "verify", "verify"]
    assert grant_ids == {db.get(type(session), session.id).router_grant_id}

    attempt = db.query(ActivationAttempt).filter_by(session_id=session.id).one()
    assert attempt.status == "succeeded"
    assert attempt.completed_at is not None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ("", False),
        ("false", False),
        ("0", False),
        ("yes", False),
        ("1", False),
        ("true", True),
        ("TRUE", True),
        (" true ", True),
    ],
)
def test_sandbox_router_override_opens_only_for_true(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", raising=False)
    else:
        monkeypatch.setenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", value)
    assert sandbox_router_activation_allowed() is expected


@pytest.mark.parametrize("override", [None, "false", "", "1", "yes"])
def test_sandbox_payment_cannot_open_a_live_router_without_the_override(
    db, user, package, monkeypatch, tmp_path, override
):
    from app.services import access_auth, session_service

    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    # get_access_authenticator() loads the repository .env and load_dotenv fills any
    # variable that is missing. Point it at a missing file so a lab .env that sets
    # the override to "true" cannot change what this test proves.
    monkeypatch.setattr(access_auth, "ROOT_ENV", tmp_path / "no-such.env")
    if override is None:
        monkeypatch.delenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", raising=False)
    else:
        monkeypatch.setenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", override)
    router_calls = []

    def unexpected_router_call(**kwargs):
        router_calls.append(kwargs)
        raise AssertionError("A sandbox payment must not reach the router")

    monkeypatch.setattr(session_service, "activate_hotspot_device", unexpected_router_call)
    session = verified_device_session(db, user, package)

    result = activate_session(db, session.id)

    assert router_calls == []
    assert result.status == "FAILED"
    assert result.activation_status == "failed"
    assert result.router_grant_id is None
    assert "Sandbox payment cannot activate access" in result.failure_reason

    attempt = db.query(ActivationAttempt).filter_by(session_id=session.id).one()
    assert attempt.status == "failed"
    assert "Sandbox payment cannot activate access" in attempt.error_message
    assert attempt.completed_at is not None


def test_sandbox_payment_reaches_the_router_when_the_override_is_true(
    db, user, package, monkeypatch
):
    from app.services import session_service

    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    monkeypatch.setenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", "true")
    router_calls = []

    def router_call(**kwargs):
        router_calls.append(kwargs)
        return {"status": "ACTIVE"}

    monkeypatch.setattr(session_service, "activate_hotspot_device", router_call)
    session = verified_device_session(db, user, package)

    result = activate_session(db, session.id)

    assert result.status == "ACTIVE"
    assert result.activation_status == "succeeded"
    assert result.router_grant_id is not None
    assert len(router_calls) == 1
    assert router_calls[0]["grant_id"] == result.router_grant_id
    assert router_calls[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"
