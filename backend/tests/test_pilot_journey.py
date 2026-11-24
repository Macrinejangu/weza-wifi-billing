from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.api.auth import CUSTOMER_AUDIENCE
from app.core.security import create_token
from app.models import Payment, Subscription, User, WiFiSession
from app.services import session_service
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase
from app.services.session_expiry import expire_due_sessions


def auth_headers(user, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "a" * 40)
    return {"Authorization": f"Bearer {create_token(user.id, audience=CUSTOMER_AUDIENCE)}"}


def test_simulated_checkout_ends_one_session_and_keeps_paid_clock(client, db, user, package, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false")
    headers = auth_headers(user, monkeypatch)
    purchase = client.post("/api/customer/purchases", json={"package_id": package.id}, headers={
        **headers, "Idempotency-Key": "pilot-mock-purchase",
    })
    assert purchase.status_code == 201
    payload = {"purchase_id": purchase.json()["id"], "phone_number": "254712345678"}
    first = client.post("/api/customer/payments/mock", json=payload, headers=headers)
    repeat = client.post("/api/customer/payments/mock", json=payload, headers=headers)
    assert first.status_code == repeat.status_code == 200
    assert first.json() == repeat.json()
    payment_id = first.json()["payment_id"]
    session = db.scalar(select(WiFiSession).where(WiFiSession.payment_id == payment_id))
    subscription = db.scalar(select(Subscription).where(Subscription.payment_id == payment_id))
    payment = db.get(Payment, payment_id)
    assert subscription.start_date == session.started_at == payment.paid_at
    assert session.expires_at == payment.paid_at + timedelta(minutes=package.duration_minutes)

    target = f"/api/customer/connection?payment_id={payment_id}"
    overview = client.get(target, headers=headers)
    assert overview.status_code == 200
    assert overview.json()["access_status"] == "active"
    assert overview.json()["simulated"] is True
    assert client.get(target).status_code == 401
    other = User(full_name="Other customer", email="other-pilot@example.test", password_hash="x")
    db.add(other)
    db.commit()
    assert client.get(target, headers=auth_headers(other, monkeypatch)).status_code == 404

    expired_time = datetime.now(UTC) - timedelta(seconds=1)
    subscription.end_date = session.expires_at = expired_time
    db.commit()
    assert expire_due_sessions(db) == 1
    assert expire_due_sessions(db) == 0
    assert client.get(target, headers=headers).json()["access_status"] == "expired"
    assert db.get(WiFiSession, session.id).status == "EXPIRED"
    assert db.get(Payment, payment_id).status == "successful"


def test_paid_with_no_session_still_has_countdown(client, db, user, package, monkeypatch):
    headers = auth_headers(user, monkeypatch)
    purchase, _ = create_purchase(db, user.id, package.id, "paid-no-session-pilot")
    payment = create_payment(db, purchase.id, "254712345678")
    payment = process_mock_payment(db, payment.id)
    response = client.get("/api/customer/connection", headers=headers)

    assert response.status_code == 200
    value = response.json()
    assert value["access_status"] == "activating"
    assert value["payment_status"] == "successful"
    assert datetime.fromisoformat(value["started_at"]) == payment.paid_at
    assert datetime.fromisoformat(value["expires_at"]) == payment.paid_at + timedelta(minutes=package.duration_minutes)


def test_customer_simulation_is_disabled_on_mikrotik(client, user, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    response = client.post("/api/customer/payments/mock", headers=auth_headers(user, monkeypatch), json={
        "purchase_id": 1, "phone_number": "254712345678",
    })
    assert response.status_code == 404


def test_delayed_activation_keeps_verified_payment_expiry(db, user, package, monkeypatch):
    purchase, _ = create_purchase(db, user.id, package.id, "delayed-pilot")
    payment = process_mock_payment(db, create_payment(db, purchase.id, "254712345678").id)
    paid_at = datetime.now(UTC) - timedelta(minutes=5)
    payment.paid_at = paid_at
    db.commit()
    session = session_service.create_session(db, payment.id, verified_checkout=True)

    failed = session_service.activate_session(db, session.id, lambda _: {"status": "ERROR"})
    assert failed.activation_status == "failed"
    assert failed.subscription.start_date == paid_at
    assert failed.subscription.end_date == paid_at + timedelta(minutes=60)

    recovered = session_service.activate_session(db, session.id, lambda _: {"status": "ACTIVE"})
    assert recovered.started_at == paid_at
    assert recovered.expires_at == paid_at + timedelta(minutes=60)


def test_active_package_blocks_a_second_payment_until_expiry(client, db, user, package, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false")
    headers = auth_headers(user, monkeypatch)
    first, _ = create_purchase(db, user.id, package.id, "first-pilot-package")
    second, _ = create_purchase(db, user.id, package.id, "second-pilot-package")

    url = "/api/customer/payments/mock"
    first_result = client.post(url, json={
        "purchase_id": first.id, "phone_number": "254712345678",
    }, headers=headers)
    assert first_result.status_code == 200
    second_data = {"purchase_id": second.id, "phone_number": "254712345678"}
    assert client.post(url, json=second_data, headers=headers).status_code == 409

    payment = db.get(Payment, first_result.json()["payment_id"])
    payment.paid_at = datetime.now(UTC) - timedelta(minutes=package.duration_minutes + 1)
    db.commit()
    assert client.post(url, json=second_data, headers=headers).status_code == 200


def test_staff_recovers_a_paid_purchase_without_charging_again(client, db, user, package, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    customer_headers = auth_headers(user, monkeypatch)
    purchase, _ = create_purchase(db, user.id, package.id, "paid-recovery-pilot")
    payment = process_mock_payment(db, create_payment(db, purchase.id, "254712345678").id)
    staff = User(full_name="Test operator", email="operator-pilot@example.test", password_hash="x", role="operator")
    db.add(staff)
    db.commit()
    staff_headers = {"Authorization": f"Bearer {create_token(staff.id)}"}

    endpoint = f"/api/connection-issues/{payment.id}/retry"
    assert client.post(endpoint, headers=customer_headers).status_code == 401
    assert client.post(endpoint, headers=staff_headers).json() == {"outcome": "activated"}
    assert client.post(endpoint, headers=staff_headers).json() == {"outcome": "activated"}
    assert db.query(Payment).filter_by(purchase_id=purchase.id).count() == 1
    assert db.query(WiFiSession).filter_by(payment_id=payment.id).count() == 1


def test_failed_disconnect_is_recorded_and_the_same_grant_is_retried(db, user, package, monkeypatch):
    from app.services import session_expiry

    purchase, _ = create_purchase(
        db, user.id, package.id, "disconnect-retry-pilot",
        device_mac="AA:BB:CC:DD:EE:FF", device_ip="10.20.0.254",
    )
    payment = process_mock_payment(db, create_payment(db, purchase.id, "254712345678").id)
    payment.raw_callback = {"test": "verified Daraja fixture"}
    db.commit()
    session = session_service.create_session(db, payment.id, verified_checkout=True)
    session.router_grant_id = "a" * 32
    db.commit()
    active = session_service.activate_session(db, session.id, lambda _: {
        "status": "ACTIVE", "router_identity": "Test router", "server": "Test hotspot",
        "router_session_id": "*ABC",
    })
    assert active.router_session_id == "*ABC"

    attempted = []

    def expire_grant(mac, grant_id, *, router_identity, router_server_name):
        attempted.append((mac, grant_id, router_identity, router_server_name))
        if len(attempted) == 1:
            raise TimeoutError("A device-specific diagnostic")

    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    monkeypatch.setattr(session_expiry, "expire_hotspot_grant", expire_grant)
    deadline = active.expires_at + timedelta(seconds=1)
    assert expire_due_sessions(db, now=deadline) == 0
    assert active.status == "ACTIVE"
    assert active.disconnection_status == "failed"
    assert active.disconnection_error == "TimeoutError"
    assert active.ended_at is None

    assert expire_due_sessions(db, now=deadline) == 1
    assert active.status == "EXPIRED"
    assert active.subscription.status == "expired"
    assert active.disconnection_status == "succeeded"
    assert active.disconnection_error is None
    assert active.disconnected_at == active.ended_at == deadline
    assert attempted == [("AA:BB:CC:DD:EE:FF", "a" * 32, "Test router", "Test hotspot")] * 2
    assert expire_due_sessions(db, now=deadline) == 0
    assert len(attempted) == 2


def test_expired_unconfirmed_grant_stays_eligible_for_cleanup(db, user, package):
    purchase, _ = create_purchase(db, user.id, package.id, "expired-possible-grant")
    payment = process_mock_payment(db, create_payment(db, purchase.id, "254712345678").id)
    payment.paid_at = datetime.now(UTC) - timedelta(hours=2)
    db.commit()
    session = session_service.create_session(db, payment.id, verified_checkout=True)
    session.router_grant_id = "b" * 32
    db.commit()

    def unexpected_activation(_):
        raise AssertionError("An expired grant must not be activated")

    after_retry = session_service.activate_session(db, session.id, unexpected_activation)
    assert after_retry.status == "PAYMENT_CONFIRMED"
    assert after_retry.ended_at is None
