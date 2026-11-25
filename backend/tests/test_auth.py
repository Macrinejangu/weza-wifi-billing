from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_token, hash_password
from app.api import staff as staff_api
from app.models import AccessPoint, ActivationAttempt, Router, User, WiFiSession

from test_payment_settlement import make_payment, make_purchase

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)


def add_user(db, role="operator", status="active", email="staff@weza.local"):
    user = User(full_name="Staff", email=email, password_hash=hash_password(PASSWORD), role=role, status=status)
    db.add(user)
    db.commit()
    return user


def login(client, email="staff@weza.local", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_staff_can_log_in_and_use_the_token(client, db):
    add_user(db)
    token = login(client).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["role"] == "operator"


def test_bad_logins_all_get_the_same_401(client, db):
    add_user(db)
    add_user(db, role="customer", email="c@weza.local")
    add_user(db, status="suspended", email="s@weza.local")
    for email, password in [("staff@weza.local", "wrong"), ("nobody@weza.local", PASSWORD),
                            ("c@weza.local", PASSWORD), ("s@weza.local", PASSWORD)]:
        response = login(client, email, password)
        assert response.status_code == 401 and response.json()["detail"] == "Invalid email or password"


@pytest.mark.parametrize("path", ["/api/payments", "/api/payments/1", "/api/sessions", "/api/auth/me"])
def test_protected_routes_reject_missing_or_bad_tokens(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401


def test_customer_token_is_forbidden_and_suspended_staff_is_cut_off(client, db):
    customer = add_user(db, role="customer", email="c@weza.local")
    headers = {"Authorization": f"Bearer {create_token(customer.id)}"}
    assert client.get("/api/payments", headers=headers).status_code == 403
    staff = add_user(db)
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}
    assert client.get("/api/payments", headers=headers).status_code == 200
    staff.status = "suspended"
    db.commit()
    assert client.get("/api/payments", headers=headers).status_code == 401  # checked on every request


def test_staff_can_read_payments_and_sessions(client, db, package):
    staff = add_user(db)
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}
    assert client.get("/api/payments", headers=headers).json() == []
    assert client.get("/api/sessions?limit=5", headers=headers).json() == []
    assert client.get("/api/payments/999", headers=headers).status_code == 404
    assert client.get("/api/payments?limit=0", headers=headers).status_code == 422


def test_both_react_apps_are_allowed_by_cors(client):
    for origin in ("http://localhost:5173", "http://127.0.0.1:5174"):
        reply = client.options("/api/auth/login", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"})
        assert reply.status_code == 200 and reply.headers["access-control-allow-origin"] == origin
    reply = client.options("/api/auth/login", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in reply.headers


def test_database_rejects_unknown_role_and_status(db):
    for role, status in [("boss", "active"), ("operator", "banana")]:
        with pytest.raises(IntegrityError):
            add_user(db, role=role, status=status)
        db.rollback()


PACKAGE_PAYLOAD = {
    "name": "Demo",
    "service_type": "hotspot",
    "price": 20,
    "duration_minutes": 60,
    "download_speed_mbps": 5,
    "upload_speed_mbps": 2,
}


@pytest.mark.parametrize(("role", "status", "minutes", "expected"), [
    (None, None, None, 401),
    ("customer", "active", 60, 403),
    ("operator", "suspended", 60, 401),
    ("operator", "active", -1, 401),
    ("operator", "active", 60, 403),
])
def test_package_writes_reject_unauthorized_requests(client, db, package, role, status, minutes, expected):
    headers = {}
    if role:
        user = add_user(db, role=role, status=status)
        headers["Authorization"] = f"Bearer {create_token(user.id, minutes=minutes)}"

    path = f"/api/packages/{package.id}"
    assert client.post("/api/packages/", json=PACKAGE_PAYLOAD, headers=headers).status_code == expected
    assert client.put(path, json={**PACKAGE_PAYLOAD, "is_active": False}, headers=headers).status_code == expected
    assert client.delete(path, headers=headers).status_code == expected
    assert client.get("/api/packages/").json()[0]["name"] == "1 Hour"
    assert db.query(type(package)).count() == 1


def test_admin_manages_packages_when_mock_payments_are_off(client, db, monkeypatch):
    add_user(db, role="admin")
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "false")

    invalid_package = {**PACKAGE_PAYLOAD, "duration_minutes": 0}
    assert client.post("/api/packages/", json=invalid_package, headers=headers).status_code == 422
    created = client.post("/api/packages/", json=PACKAGE_PAYLOAD, headers=headers)
    assert created.status_code == 200
    path = f"/api/packages/{created.json()['id']}"
    updated_package = {**PACKAGE_PAYLOAD, "price": 30, "is_active": True}

    updated = client.put(path, json=updated_package, headers=headers)
    assert updated.status_code == 200 and updated.json()["price"] == 30
    assert client.get("/api/packages/").json()[0]["price"] == 30
    assert client.delete(path, headers=headers).status_code == 200
    assert client.get("/api/packages/").json() == []
    staff_catalogue = client.get("/api/packages/staff", headers=headers)
    assert staff_catalogue.json()[0]["is_active"] is False


@pytest.mark.parametrize("stored_hash", ["missing-separator", "z" * 32 + "$" + "0" * 128,
                                        "0" * 32 + "$" + "é" * 128])
def test_malformed_password_hash_returns_generic_login_failure(client, db, stored_hash):
    user = add_user(db)
    user.password_hash = stored_hash
    db.commit()

    response = login(client)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_session_detail_and_activation_are_staff_only(client, db):
    customer = add_user(db, role="customer", email="c@weza.local")
    headers = {"Authorization": f"Bearer {create_token(customer.id)}"}
    for send, path in [(client.get, "/api/sessions/1"), (client.post, "/api/sessions/1/activate")]:
        assert send(path).status_code == 401
        assert send(path, headers=headers).status_code == 403



def test_customer_directory_is_staff_only(client, db):
    customer = add_user(db, role="customer", email="customer@weza.local")
    suspended_staff = add_user(db, status="suspended")

    assert client.get("/api/customers").status_code == 401
    customer_headers = {"Authorization": f"Bearer {create_token(customer.id)}"}
    suspended_headers = {"Authorization": f"Bearer {create_token(suspended_staff.id)}"}
    assert client.get("/api/customers", headers=customer_headers).status_code == 403
    assert client.get("/api/customers", headers=suspended_headers).status_code == 401


def test_customer_directory_returns_minimal_customer_fields(client, db):
    staff = add_user(db)
    customer = add_user(db, role="customer", email="customer@weza.local")
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}

    response = client.get("/api/customers", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [customer.id]
    assert set(rows[0]) == {"id", "full_name", "phone", "status", "created_at"}
    assert rows[0]["phone"] is None


def test_customer_directory_applies_search_status_and_pagination(client, db):
    staff = add_user(db)
    first = add_user(db, role="customer", email="first@weza.local")
    second = add_user(db, role="customer", status="inactive", email="second@weza.local")
    first.full_name = "Audit Customer"
    first.phone = "+254700000001"
    db.commit()
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}

    def ids(**params):
        response = client.get("/api/customers", headers=headers, params=params)
        assert response.status_code == 200
        return [row["id"] for row in response.json()]

    assert ids(limit=1) == [second.id]
    assert ids(limit=1, offset=1) == [first.id]
    assert ids(status="inactive") == [second.id]
    assert ids(q="audit") == [first.id]
    assert ids(q="700000001") == [first.id]
    assert ids(q=str(first.id)) == [first.id]
    assert ids(q="%") == []
    assert client.get("/api/customers?limit=101", headers=headers).status_code == 422



def test_overview_requires_active_staff(client, db):
    customer = add_user(db, role="customer")
    suspended = add_user(db, status="suspended", email="suspended@weza.local")
    assert client.get("/api/overview").status_code == 401
    assert client.get("/api/overview", headers={"Authorization": f"Bearer {create_token(customer.id)}"}).status_code == 403
    assert client.get("/api/overview", headers={"Authorization": f"Bearer {create_token(suspended.id)}"}).status_code == 401


def test_overview_counts_sandbox_receipts_and_current_session_states(client, db, user, package, monkeypatch):
    staff = add_user(db)
    now = datetime(2026, 11, 23, 4, tzinfo=UTC)
    midnight = datetime(2026, 11, 22, 21, tzinfo=UTC)
    provider = {"Body": {"stkCallback": {"ResultCode": 0}}}
    original_overview = staff_api.read_overview
    monkeypatch.setattr(staff_api, "read_overview", lambda session, _: original_overview(session, now))

    def add_payment(key, *, status="successful", paid_at=None, raw_callback=None):
        purchase = make_purchase(db, user, package, key=key)
        payment = make_payment(
            db, purchase, checkout=key, status=status,
            receipt=f"receipt-{key}" if status == "successful" else None,
        )
        payment.paid_at = paid_at
        payment.raw_callback = raw_callback
        db.commit()
        return payment

    active_payment = add_payment("today-provider", paid_at=midnight, raw_callback=provider)
    expired_payment = add_payment("yesterday-provider", paid_at=midnight - timedelta(seconds=1), raw_callback=provider)
    failed_payment = add_payment("today-mock", paid_at=now, raw_callback={"mock": True})
    ended_payment = add_payment("today-ended", paid_at=now)
    add_payment("pending", status="pending")
    add_payment("failed", status="failed")

    def add_session(payment, status, activation, *, expires=None, ended=None):
        db.add(WiFiSession(
            payment_id=payment.id, user_id=user.id, package_id=package.id,
            status=status, activation_status=activation,
            started_at=now - timedelta(hours=1) if expires else None,
            expires_at=expires, ended_at=ended,
        ))

    add_session(active_payment, "ACTIVE", "succeeded", expires=now + timedelta(hours=1))
    add_session(expired_payment, "ACTIVE", "succeeded", expires=now)
    add_session(ended_payment, "ACTIVE", "succeeded", expires=now + timedelta(hours=1), ended=now)
    add_session(failed_payment, "FAILED", "failed")
    db.commit()

    response = client.get("/api/overview", headers={"Authorization": f"Bearer {create_token(staff.id)}"})
    assert response.status_code == 200
    assert response.json() == {
        "sandbox_settled_today_kes": active_payment.amount,
        "sandbox_settled_today_count": 1,
        "active_session_records": 1,
        "pending_payments": 1,
        "failed_activations": 1,
    }


def test_network_inventory_is_staff_only(client, db):
    customer = add_user(db, role="customer", email="inventory-customer@weza.local")
    suspended = add_user(db, status="suspended", email="inventory-suspended@weza.local")

    assert client.get("/api/network/devices").status_code == 401
    assert client.get("/api/network/devices", headers={"Authorization": f"Bearer {create_token(customer.id)}"}).status_code == 403
    assert client.get("/api/network/devices", headers={"Authorization": f"Bearer {create_token(suspended.id)}"}).status_code == 401


def test_staff_network_inventory_returns_saved_records_and_empty_lists(client, db):
    staff = add_user(db)
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}
    empty = client.get("/api/network/devices", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == {"routers": [], "access_points": []}

    router = Router(name="Audit Router", identity="audit-router", host="192.0.2.10", status="online")
    db.add(router)
    db.flush()
    seen = datetime(2026, 11, 23, 8, tzinfo=UTC)
    point = AccessPoint(
        router_id=router.id, name="Audit Access Point", location="Test Lab",
        mac_address="02:00:00:00:00:01", status="offline", last_seen_at=seen,
    )
    db.add(point)
    db.commit()

    response = client.get("/api/network/devices", headers=headers)
    assert response.status_code == 200
    inventory = response.json()
    assert inventory["routers"] == [{
        "id": router.id, "name": "Audit Router", "identity": "audit-router", "status": "online",
        "last_synced_at": None, "hotspot_enabled": None,
    }]
    [record] = inventory["access_points"]
    assert record == {
        "id": point.id, "name": "Audit Access Point", "router_id": router.id,
        "location": "Test Lab", "mac_address": "02:00:00:00:00:01", "status": "offline",
        "last_seen_at": record["last_seen_at"],
    }
    assert datetime.fromisoformat(record["last_seen_at"]) == seen


def test_connection_issues_require_active_staff(client, db):
    customer = add_user(db, role="customer", email="issues-customer@weza.local")
    suspended = add_user(db, status="suspended", email="issues-suspended@weza.local")

    assert client.get("/api/connection-issues").status_code == 401
    assert client.get("/api/connection-issues", headers={"Authorization": f"Bearer {create_token(customer.id)}"}).status_code == 403
    assert client.get("/api/connection-issues", headers={"Authorization": f"Bearer {create_token(suspended.id)}"}).status_code == 401


def test_connection_issues_show_paid_customers_waiting_or_failed_without_raw_diagnostics(client, db, user, package):
    staff = add_user(db)
    headers = {"Authorization": f"Bearer {create_token(staff.id)}"}
    assert client.get("/api/connection-issues", headers=headers).json() == []

    def create_session(key, payment_status, activation_status, session_status):
        purchase = make_purchase(db, user, package, key=key)
        payment = make_payment(
            db, purchase, checkout=key, status=payment_status,
            receipt=f"receipt-{key}" if payment_status == "successful" else None,
        )
        session = WiFiSession(
            payment_id=payment.id, user_id=user.id, package_id=package.id,
            status=session_status, activation_status=activation_status,
            failure_reason="internal diagnostic text",
        )
        db.add(session)
        db.commit()
        return payment, session

    payment, failed = create_session("paid-failed", "successful", "failed", "FAILED")
    create_session("unpaid-failed", "pending", "failed", "FAILED")
    waiting_payment, waiting = create_session("paid-waiting", "successful", "waiting", "ACTIVATING")
    missing_purchase = make_purchase(db, user, package, key="paid-no-session")
    missing_payment = make_payment(db, missing_purchase, checkout="paid-no-session", status="successful")
    db.add_all([
        ActivationAttempt(session_id=failed.id, attempt_number=1, status="failed", error_code="RouterActivationError"),
        ActivationAttempt(session_id=failed.id, attempt_number=2, status="failed", error_code="TimeoutError", error_message="internal diagnostic text"),
    ])
    db.commit()

    response = client.get("/api/connection-issues", headers=headers)
    assert response.status_code == 200
    issues = {record["payment_id"]: record for record in response.json()}
    assert set(issues) == {payment.id, waiting_payment.id, missing_payment.id}
    assert issues[waiting_payment.id]["session_id"] == waiting.id
    assert issues[waiting_payment.id]["activation_status"] == "waiting"
    assert issues[missing_payment.id]["session_id"] is None
    assert issues[missing_payment.id]["activation_status"] == "not_started"
    issue = issues[payment.id]
    assert issue["session_id"] == failed.id
    assert issue["customer_id"] == user.id
    assert issue["payment_id"] == payment.id
    assert issue["payment_reference"] == "receipt-paid-failed"
    assert issue["payment_status"] == "successful"
    assert issue["activation_status"] == "failed"
    assert issue["failure_reason"] == "The activation request timed out."
    assert "internal diagnostic text" not in response.text
    assert client.get("/api/connection-issues?offset=3", headers=headers).json() == []


def test_customer_login_reads_only_its_own_profile(client, db):
    customer = add_user(db, role="customer", email="pilot-customer@weza.local")
    customer.full_name = "Pilot Customer"
    customer.phone = "+254700000001"
    db.commit()

    login_response = client.post("/api/auth/customer/login", json={
        "email": " PILOT-CUSTOMER@weza.local ", "password": PASSWORD,
    })
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    assert client.get("/api/auth/customer/me", headers=headers).json() == {
        "id": customer.id, "full_name": "Pilot Customer",
        "email": "pilot-customer@weza.local", "phone": "+254700000001",
    }

    customer.status = "suspended"
    db.commit()
    assert client.get("/api/auth/customer/me", headers=headers).status_code == 401


def test_customer_login_rejects_ineligible_accounts_with_the_same_error(client, db):
    add_user(db)
    add_user(db, role="customer", email="customer@weza.local")
    add_user(db, role="customer", status="suspended", email="suspended@weza.local")
    for email, password in [
        ("staff@weza.local", PASSWORD), ("customer@weza.local", "wrong"),
        ("suspended@weza.local", PASSWORD), ("missing@weza.local", PASSWORD),
    ]:
        response = client.post("/api/auth/customer/login", json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}


def test_customer_and_staff_tokens_are_not_interchangeable(client, db):
    add_user(db)
    customer = add_user(db, role="customer", email="customer@weza.local")
    staff_token = login(client).json()["access_token"]
    customer_response = client.post("/api/auth/customer/login", json={
        "email": "customer@weza.local", "password": PASSWORD,
    })
    assert customer_response.status_code == 200
    customer_headers = {"Authorization": f"Bearer {customer_response.json()['access_token']}"}

    assert client.get("/api/auth/customer/me").status_code == 401
    assert client.get("/api/auth/customer/me", headers={"Authorization": f"Bearer {staff_token}"}).status_code == 401
    assert client.get("/api/auth/me", headers=customer_headers).status_code == 401
    assert client.get("/api/payments", headers=customer_headers).status_code == 401

    customer.role = "operator"
    db.commit()
    assert client.get("/api/auth/customer/me", headers=customer_headers).status_code == 401
    assert client.get("/api/auth/me", headers=customer_headers).status_code == 401
