from sqlalchemy import select

from app.core.security import create_token
from app.models import AdminAuditLog, User, WiFiSession


def staff_headers(db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    headers = {}
    for role in ("admin", "operator"):
        staff = User(full_name=role, email=f"{role}@admin-actions.test", password_hash="test", role=role)
        db.add(staff)
        db.flush()
        headers[role] = {"Authorization": f"Bearer {create_token(staff.id)}"}
    db.commit()
    return headers


def test_only_admin_can_create_and_edit_customer_accounts(client, db, monkeypatch):
    staff = staff_headers(db, monkeypatch)
    payload = {
        "full_name": "Test customer", "email": "customer@admin-actions.test",
        "password": "local-test-password", "phone": "0712345678",
    }
    assert client.post("/api/customers", json=payload, headers=staff["operator"]).status_code == 403
    created = client.post("/api/customers", json=payload, headers=staff["admin"])
    assert created.status_code == 201
    customer_id = created.json()["id"]
    path = f"/api/customers/{customer_id}"
    update = {"full_name": "Corrected name", "phone": "0712345679"}
    assert client.put(path, json=update, headers=staff["operator"]).status_code == 403
    assert client.put(path, json=update, headers=staff["admin"]).json()["phone"] == "254712345679"
    login = client.post("/api/auth/customer/login", json={
        "email": payload["email"], "password": payload["password"],
    })
    assert login.status_code == 200
    audit = db.scalars(select(AdminAuditLog.action).order_by(AdminAuditLog.id)).all()
    assert audit == ["Registered customer", "Updated customer"]


def test_admin_disconnect_preserves_paid_time(client, db, monkeypatch, user, package):
    from app.api.auth import CUSTOMER_AUDIENCE

    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false")
    staff = staff_headers(db, monkeypatch)
    customer = {"Authorization": f"Bearer {create_token(user.id, audience=CUSTOMER_AUDIENCE)}"}
    purchase = client.post("/api/customer/purchases", json={"package_id": package.id}, headers={
        **customer, "Idempotency-Key": "disconnect-test-purchase",
    })
    paid = client.post("/api/customer/payments/mock", json={
        "purchase_id": purchase.json()["id"], "phone_number": "254712345678",
    }, headers=customer)
    session = db.scalar(select(WiFiSession).where(WiFiSession.payment_id == paid.json()["payment_id"]))
    expires = session.expires_at
    path = f"/api/sessions/{session.id}/disconnect"
    assert client.post(path, headers=staff["operator"]).status_code == 403
    result = client.post(path, headers=staff["admin"])
    assert result.status_code == 200 and result.json() == {"simulated": True}
    db.refresh(session)
    assert session.status == "ACTIVE"
    assert session.expires_at == expires == session.subscription.end_date
    assert db.scalar(select(AdminAuditLog.action)) == "Simulated disconnect"
