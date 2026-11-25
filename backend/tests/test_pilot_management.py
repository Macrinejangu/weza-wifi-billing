from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_token, verify_password
from app.models import AdminAuditLog, Payment, Purchase, User, WiFiSession
from app.services.session_expiry import expire_due_sessions


REGISTRATION = {
    "full_name": " Pilot Customer ",
    "email": "PILOT@example.test",
    "phone": "0712 345 678",
    "password": "local checkout test password",
}
PACKAGE = {
    "name": "Pilot package",
    "service_type": "hotspot",
    "price": 20,
    "duration_minutes": 15,
    "download_speed_mbps": 5,
    "upload_speed_mbps": 2,
}


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)


def staff_headers(db, role):
    staff = User(full_name=role.title(), email=f"{role}@pilot.example.test", password_hash="x", role=role)
    db.add(staff)
    db.commit()
    return {"Authorization": f"Bearer {create_token(staff.id)}"}


def test_registration_rejects_bad_details_and_cannot_replace_staff(client, db):
    register = "/api/auth/customer/register"
    staff_headers(db, "admin")

    assert client.post(register, json={**REGISTRATION, "email": "broken"}).status_code == 422
    assert client.post(register, json={**REGISTRATION, "phone": "123"}).status_code == 422
    short = client.post(register, json={**REGISTRATION, "password": "shortpw"})
    assert short.status_code == 422
    assert "shortpw" not in short.text
    result = client.post(register, json={**REGISTRATION, "email": " ADMIN@pilot.example.test "})
    assert result.status_code == 409
    assert client.post(register, json={**REGISTRATION, "role": "admin"}).status_code == 422
    assert db.scalar(select(User)).role == "admin"

    created = client.post(register, json=REGISTRATION)
    assert created.status_code == 201
    assert created.json()["email"] == "pilot@example.test"
    assert created.json()["phone"] == "254712345678"
    assert created.json()["full_name"] == "Pilot Customer"
    user = db.get(User, created.json()["id"])
    assert user.role == "customer"
    assert verify_password(REGISTRATION["password"], user.password_hash)
    assert client.post(register, json={**REGISTRATION, "email": "other@example.test",
                                      "phone": "+254712345678"}).status_code == 409


def test_new_customer_buys_again_after_expiry_with_updated_terms(client, db, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false")
    admin = staff_headers(db, "admin")
    operator = staff_headers(db, "operator")
    assert client.post("/api/auth/customer/register", json=REGISTRATION).status_code == 201
    credentials = {key: REGISTRATION[key] for key in ("email", "password")}
    assert client.post("/api/auth/login", json=credentials).status_code == 401
    login = client.post("/api/auth/customer/login", json=credentials)
    assert login.status_code == 200
    customer = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/packages/staff", headers=customer).status_code == 401
    assert client.post("/api/packages/", json=PACKAGE, headers=operator).status_code == 403
    response = client.post("/api/packages/", json=PACKAGE, headers=admin)
    assert response.status_code == 200
    package_id = response.json()["id"]

    def buy(key):
        response = client.post("/api/customer/purchases", json={"package_id": package_id}, headers={
            **customer, "Idempotency-Key": key,
        })
        assert response.status_code == 201
        return response.json()["id"]

    purchase_id = buy("pilot-created-account")
    terms = {**PACKAGE, "name": "Updated package", "price": 25,
             "duration_minutes": 30, "download_speed_mbps": 8, "is_active": True}
    package_url = f"/api/packages/{package_id}"
    assert client.put(package_url, json=terms, headers=admin).status_code == 200

    def pay(purchase):
        response = client.post("/api/customer/payments/mock", json={
            "purchase_id": purchase, "phone_number": "254712345678",
        }, headers=customer)
        assert response.status_code == 200
        return response.json()["payment_id"]

    payment_id = pay(purchase_id)
    saved = db.get(Purchase, purchase_id)
    assert (saved.package_name, saved.amount, saved.duration_minutes, saved.download_speed_mbps) == (
        "Pilot package", 20, 15, 5,
    )
    payment = db.get(Payment, payment_id)
    session = db.scalar(select(WiFiSession).where(WiFiSession.payment_id == payment_id))
    assert session.started_at == payment.paid_at
    assert session.expires_at == payment.paid_at + timedelta(minutes=15)

    payment.paid_at = datetime.now(UTC) - timedelta(minutes=16)
    session.expires_at = session.subscription.end_date = payment.paid_at + timedelta(minutes=15)
    db.commit()
    assert expire_due_sessions(db) == 1
    assert client.get("/api/customer/connection", headers=customer).json()["access_status"] == "expired"

    new_purchase = buy("pilot-repurchase-after-expiry")
    assert pay(new_purchase) != payment_id
    saved = db.get(Purchase, new_purchase)
    assert (saved.package_name, saved.amount, saved.duration_minutes, saved.download_speed_mbps) == (
        "Updated package", 25, 30, 8,
    )
    assert client.delete(package_url, headers=admin).status_code == 200
    assert client.delete(package_url, headers=admin).status_code == 200
    assert client.get("/api/packages/").json() == []
    assert client.get("/api/packages/staff", headers=operator).json()[0]["is_active"] is False

    audit = client.get("/api/staff/settings/audit", headers=admin).json()
    assert [entry["action"] for entry in audit if entry["entity_type"] == "package"] == [
        "Deactivated package", "Updated package", "Created package",
    ]


def test_admin_updates_public_faq_and_records_change(client, db):
    url = "/api/support/faqs"
    topics = client.get(url).json()
    assert len(topics) == 4
    topic = topics[0]
    path = f"{url}/{topic['id']}"
    operator = staff_headers(db, "operator")
    admin = staff_headers(db, "admin")
    fields = {"question": " Payment confirmed? ", "steps": [" Check your connection. "]}
    assert client.put(path, json=fields).status_code == 401
    assert client.put(path, json=fields, headers=operator).status_code == 403
    assert client.put(path, json={**fields, "steps": []}, headers=admin).status_code == 422
    assert client.put(path, json=fields, headers=admin).status_code == 200
    assert client.get(url).json()[0] == {
        "id": topic["id"], "question": "Payment confirmed?", "steps": ["Check your connection."],
    }
    assert client.put(path, json=fields, headers=admin).status_code == 200
    log = db.scalars(select(AdminAuditLog).where(AdminAuditLog.entity_type == "support_faq")).one()
    assert log.old_values["question"] == topic["question"]
    assert log.new_values["question"] == "Payment confirmed?"
