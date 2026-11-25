from datetime import UTC, datetime

from sqlalchemy import select

from app.api.routes import manual_stk, network
from app.core.security import create_token
from app.models import AccessPoint, AdminAuditLog, Payment, Router, User
from app.integrations.mpesa.client import StkPushAccepted
from app.services.network_checks import ping_target
from app.services.purchase_service import create_purchase


def staff(db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "z" * 40)
    result = {}
    for role in ("admin", "operator"):
        person = User(email=f"{role}@staff-actions.test", full_name=role, role=role, password_hash="test")
        db.add(person)
        db.flush()
        result[role] = {"Authorization": f"Bearer {create_token(person.id)}"}
    db.commit()
    return result


def test_simulated_manual_stk_admin_only_with_single_pending_payment(client, db, user, package, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false")
    headers = staff(db, monkeypatch)
    user.phone = "254712345678"
    db.commit()
    purchase, _ = create_purchase(db, user.id, package.id, "test-manual-stk")
    path = "/api/staff/manual-stk"
    options = client.get(f"{path}/purchases", headers=headers["admin"]).json()
    assert options["mode"] == "simulated" and options["purchases"][0]["amount"] == package.price
    assert client.post(path, headers=headers["operator"], json={
        "purchase_id": purchase.id, "phone": user.phone,
    }).status_code == 403
    assert client.post(path, headers=headers["admin"], json={
        "purchase_id": purchase.id, "phone": "254712345679",
    }).status_code == 409
    payload = {"purchase_id": purchase.id, "phone": user.phone}
    response = client.post(path, headers=headers["admin"], json=payload)
    assert response.status_code == 201
    assert response.json()["simulated"] is True
    repeated = client.post(path, headers=headers["admin"], json=payload)
    assert repeated.status_code == 409
    payment = db.scalars(select(Payment)).one()
    assert payment.status == "pending" and payment.paid_at is None
    audit = db.scalars(select(AdminAuditLog)).one()
    assert audit.entity_id == payment.id and audit.action == "Requested manual payment prompt"


def test_sweep_uses_only_registered_private_addresses(client, db, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    headers = staff(db, monkeypatch)
    db.add_all([
        Router(name="Lab gateway", host="192.168.64.3"),
        AccessPoint(name="Lab AP", management_ip="10.20.0.2"),
        AccessPoint(name="No address"),
        AccessPoint(name="Public address", management_ip="1.1.1.1"),
    ])
    db.commit()
    called = []

    def ping(address):
        called.append(address)
        return "reachable"

    monkeypatch.setattr(network, "ping_device", ping)
    path = "/api/network/ping-sweep"
    assert client.post(path, headers=headers["operator"]).status_code == 403
    result = client.post(path, headers=headers["admin"]).json()
    assert result["simulated"] is False
    assert {row["name"]: row["result"] for row in result["results"]} == {
        "Lab gateway": "reachable", "Lab AP": "reachable", "No address": "no_address",
        "Public address": "unsupported_address",
    }
    assert set(called) == {"192.168.64.3", "10.20.0.2"}
    assert ping_target("127.0.0.1") is None


def test_sandbox_prompt_requires_approved_handset_and_verified_device(client, db, user, package, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "false")
    monkeypatch.setenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "true")
    monkeypatch.setenv("DARAJA_TEST_PHONE", "254712345678")
    headers = staff(db, monkeypatch)["admin"]
    user.phone = "254712345678"
    db.commit()
    purchase, _ = create_purchase(db, user.id, package.id, "staff-sandbox-prompt")
    calls = []

    class ProviderFixture:
        def stk_push(self, **fields):
            calls.append(fields)
            return StkPushAccepted("fixture-checkout", "fixture-merchant")

    monkeypatch.setattr(manual_stk, "get_daraja_client", ProviderFixture)
    path = "/api/staff/manual-stk"
    payload = {"purchase_id": purchase.id, "phone": user.phone}
    assert client.post(path, headers=headers, json=payload).status_code == 409
    assert calls == []

    purchase.device_mac_address = "8A:AA:52:95:B9:BB"
    purchase.device_ip_address = "10.20.0.254"
    db.commit()
    accepted = client.post(path, headers=headers, json=payload)
    assert accepted.status_code == 201
    assert accepted.json()["status"] == "pending" and not accepted.json()["simulated"]
    assert client.post(path, headers=headers, json=payload).status_code == 409
    assert len(calls) == 1 and calls[0]["amount"] == purchase.amount


def test_sync_preserves_last_success_when_router_is_unreachable(client, db, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mikrotik")
    headers = staff(db, monkeypatch)
    gateway = Router(name="Lab gateway", host="192.168.64.3")
    db.add(gateway)
    db.commit()
    monkeypatch.setattr(network, "router_settings", lambda: {"host": gateway.host})
    monkeypatch.setattr(network, "read_gateway", lambda: ("CHR", True))
    url = "/api/network/sync-gateway"
    assert client.post(url, headers=headers["operator"]).status_code == 403
    result = client.post(url, headers=headers["admin"]).json()
    assert result["identity"] == "CHR" and result["hotspot_enabled"] is True
    db.refresh(gateway)
    assert gateway.last_synced_at is not None and gateway.status == "online"
    at = gateway.last_synced_at.astimezone(UTC)

    def unavailable():
        raise OSError("test network unavailable")

    monkeypatch.setattr(network, "read_gateway", unavailable)
    assert client.post(url, headers=headers["admin"]).status_code == 503
    db.refresh(gateway)
    assert gateway.last_synced_at == at
    assert datetime.fromisoformat(result["checked_at"]) == at
