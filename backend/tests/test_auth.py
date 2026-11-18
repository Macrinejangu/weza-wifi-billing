import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_token, hash_password
from app.models import User

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
