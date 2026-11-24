from app.core.security import create_token

from test_auth import add_user

URL = "/api/staff/settings"


def auth(user):
    return {"Authorization": f"Bearer {create_token(user.id)}"}


def test_staff_settings_returns_runtime_configuration_without_secrets(client, db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "true")
    monkeypatch.setenv("DARAJA_CONSUMER_SECRET", "private-credential")
    staff = add_user(db)
    assert client.get(URL).status_code == 401
    result = client.get(URL, headers=auth(staff))
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    payload = result.json()
    assert payload == {
        "preferences": {"name": "Weza Wi-Fi Core", "maintenance_start": None, "maintenance_end": None},
        "role": "operator",
        "active_staff_by_role": {"admin": 0, "operator": 1},
        "daraja_sandbox_enabled": True,
        "mock_payments_enabled": True,
        "router_mode": "mock",
    }
    assert client.get(URL + "/audit", headers=auth(staff)).status_code == 403


def test_only_admins_save_preferences_and_changes_are_audited_once(client, db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    admin = auth(add_user(db, role="admin"))
    operator = auth(add_user(db, email="operator@weza.test"))
    data = {"name": "Client Pilot", "maintenance_start": "23:30", "maintenance_end": "00:30"}

    assert client.put(URL, json=data, headers=operator).status_code == 403
    assert client.put(URL, json={**data, "maintenance_end": None}, headers=admin).status_code == 422
    for _ in range(2):
        assert client.put(URL, json=data, headers=admin).status_code == 200

    preferences = client.get(URL, headers=operator).json()["preferences"]
    assert preferences == {**data, "maintenance_start": "23:30:00", "maintenance_end": "00:30:00"}
    audit = client.get(URL + "/audit", headers=admin).json()
    assert len(audit) == 1
    assert audit[0]["action"] == "Updated system preferences"
    assert audit[0]["actor"] == "Staff"
    assert "old_values" not in audit[0]
