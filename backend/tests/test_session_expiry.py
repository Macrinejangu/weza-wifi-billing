from datetime import datetime, timedelta, timezone

from app.models import WiFiSession
from app.services.mock_payment import process_mock_payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase
from app.services.session_service import activate_session, create_session
from app.services.session_expiry_service import expire_due_sessions


PHONE = "254712345678"


def make_active_session(db, user, package, access_key):
    purchase, _ = create_purchase(
        db, user.id, package.id, access_key
    )
    payment = process_mock_payment(
        db,
        create_payment(db, purchase.id, PHONE).id,
        True,
    )
    session = create_session(db, payment.id)

    return activate_session(
        db,
        session.id,
        lambda session_id: {"status": "ACTIVE"},
    )


class SuccessfulDisconnector:
    def __init__(self):
        self.calls = []

    def disconnect_device(
        self,
        session_id,
        mac_address,
        server_name,
        router_identity,
        router_session_id,
    ):
        self.calls.append(session_id)
        return {"status": "DISCONNECTED"}


class FailedDisconnector:
    def disconnect_device(
        self,
        session_id,
        mac_address,
        server_name,
        router_identity,
        router_session_id,
    ):
        raise RuntimeError("Simulated router disconnection failure")


def test_due_session_expires_after_confirmed_disconnection(
    db, user, package, monkeypatch
):
    from app.services import session_expiry_service

    now = datetime.now(timezone.utc)
    session = make_active_session(
        db, user, package, "expiry-success-key"
    )
    session.expires_at = now - timedelta(minutes=1)
    db.commit()

    provider = SuccessfulDisconnector()
    monkeypatch.setattr(
        session_expiry_service,
        "get_access_authenticator",
        lambda: provider,
    )

    result = expire_due_sessions(db, now=now)

    db.refresh(session)

    assert result == {
        "processed": 1,
        "expired": 1,
        "failed": 0,
    }
    assert session.status == "EXPIRED"
    assert session.disconnection_status == "succeeded"
    assert session.disconnected_at == now
    assert session.ended_at == now
    assert provider.calls == [session.id]

    # A second cycle must not disconnect an already expired session.
    second_result = expire_due_sessions(db, now=now)

    assert second_result == {
        "processed": 0,
        "expired": 0,
        "failed": 0,
    }
    assert provider.calls == [session.id]


def test_failed_disconnection_remains_active_and_can_retry(
    db, user, package, monkeypatch
):
    from app.services import session_expiry_service

    now = datetime.now(timezone.utc)
    session = make_active_session(
        db, user, package, "expiry-retry-key"
    )
    session.expires_at = now - timedelta(minutes=1)
    db.commit()

    monkeypatch.setattr(
        session_expiry_service,
        "get_access_authenticator",
        FailedDisconnector,
    )

    failed_result = expire_due_sessions(db, now=now)

    db.refresh(session)

    assert failed_result == {
        "processed": 1,
        "expired": 0,
        "failed": 1,
    }
    assert session.status == "ACTIVE"
    assert session.disconnection_status == "failed"
    assert session.ended_at is None
    assert "Simulated router disconnection failure" in (
        session.disconnection_error
    )

    provider = SuccessfulDisconnector()
    monkeypatch.setattr(
        session_expiry_service,
        "get_access_authenticator",
        lambda: provider,
    )

    retry_result = expire_due_sessions(db, now=now)

    db.refresh(session)

    assert retry_result == {
        "processed": 1,
        "expired": 1,
        "failed": 0,
    }
    assert session.status == "EXPIRED"
    assert session.disconnection_status == "succeeded"
    assert provider.calls == [session.id]


def test_session_that_has_not_expired_is_not_disconnected(
    db, user, package, monkeypatch
):
    from app.services import session_expiry_service

    now = datetime.now(timezone.utc)
    session = make_active_session(
        db, user, package, "expiry-not-due-key"
    )

    provider_calls = []

    def unexpected_provider():
        provider_calls.append(True)
        raise AssertionError(
            "Provider must not be called for a session that is not due"
        )

    monkeypatch.setattr(
        session_expiry_service,
        "get_access_authenticator",
        unexpected_provider,
    )

    result = expire_due_sessions(db, now=now)

    db.refresh(session)

    assert result == {
        "processed": 0,
        "expired": 0,
        "failed": 0,
    }
    assert session.status == "ACTIVE"
    assert session.disconnection_status == "not_started"
    assert provider_calls == []



def test_mikrotik_disconnection_requires_recorded_router_identity(monkeypatch):
    from app.services import access_auth

    authenticator = access_auth.MikroTikAuthenticator()
    disconnect_calls = []

    monkeypatch.setattr(
        access_auth,
        "disconnect_hotspot_device",
        lambda **kwargs: disconnect_calls.append(kwargs),
    )

    with __import__("pytest").raises(
        ValueError,
        match="Recorded router identity",
    ):
        authenticator.disconnect_device(
            session_id=1,
            mac_address="AA:BB:CC:DD:EE:FF",
            server_name="WEZA-Hotspot",
            router_identity=None,
            router_session_id="*active-1",
        )

    assert disconnect_calls == []
