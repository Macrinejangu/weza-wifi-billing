"""HTTP tests for the staff recovery routes (WEZA-63).

The staff login and the router-mode check are replaced so the tests are
deterministic. No network, no Daraja.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.api.auth import current_staff
from app.api.routes.recovery import get_require_device
from app.main import app
from app.models import AdminAuditLog, WiFiSession

from test_payment_fulfilment_db import make_paid

EXPECTED_FIELDS = {
    "payment_id", "purchase_id", "user_id", "session_id", "reason", "action",
    "payment_status", "session_status", "activation_status", "last_error_code",
    "paid_at", "waiting_since", "age_seconds",
}


@pytest.fixture
def staff(client, user, monkeypatch):
    """Log in as staff, with a router that needs no verified device."""
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setitem(app.dependency_overrides, current_staff, lambda: user)
    monkeypatch.setitem(app.dependency_overrides, get_require_device, lambda: False)
    return user


def stuck_payment(db, user, package):
    """A confirmed payment, paid an hour ago, with no session."""
    payment = make_paid(db, user, package)
    payment.paid_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    return payment


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/recovery/cases"),
        ("get", "/api/recovery/cases/1"),
        ("post", "/api/recovery/cases/1/retry"),
    ],
)
def test_staff_login_is_required(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_list_shows_the_unresolved_case_without_raw_text(staff, client, db, user, package):
    payment = stuck_payment(db, user, package)

    response = client.get("/api/recovery/cases")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    cases = {case["payment_id"]: case for case in response.json()}
    case = cases[payment.id]
    assert set(case) == EXPECTED_FIELDS
    assert case["reason"] == "paid_no_session"
    assert case["action"] == "retry_activation"
    assert case["session_id"] is None


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_bad_paging_is_a_422(staff, client, query):
    assert client.get(f"/api/recovery/cases?{query}").status_code == 422


def test_detail_returns_one_case(staff, client, db, user, package):
    payment = stuck_payment(db, user, package)

    response = client.get(f"/api/recovery/cases/{payment.id}")

    assert response.status_code == 200
    assert response.json()["payment_id"] == payment.id


def test_detail_is_404_when_there_is_no_unresolved_case(staff, client):
    assert client.get("/api/recovery/cases/999999999").status_code == 404


def test_retry_connects_the_customer_and_audits_it(staff, client, db, user, package):
    payment = stuck_payment(db, user, package)

    response = client.post(f"/api/recovery/cases/{payment.id}/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "activated"
    assert body["reason_before"] == "paid_no_session"
    db.expire_all()
    session = db.get(WiFiSession, body["session_id"])
    assert (session.status, session.activation_status) == ("ACTIVE", "succeeded")
    audit = db.get(AdminAuditLog, body["audit_id"])
    assert audit.admin_id == user.id
    assert audit.new_values["outcome"] == "activated"


def test_retrying_again_is_refused_with_409(staff, client, db, user, package):
    payment = stuck_payment(db, user, package)
    assert client.post(f"/api/recovery/cases/{payment.id}/retry").status_code == 200

    response = client.post(f"/api/recovery/cases/{payment.id}/retry")

    assert response.status_code == 409
    assert response.json()["code"] == "nothing_to_retry"


def test_unknown_payment_is_a_404(staff, client):
    assert client.post("/api/recovery/cases/999999999/retry").status_code == 404


def test_unconfirmed_payment_is_refused(staff, client, db, user, package):
    payment = make_paid(db, user, package, successful=False)

    response = client.post(f"/api/recovery/cases/{payment.id}/retry")

    assert response.status_code == 409
    assert response.json()["code"] == "payment_not_confirmed"


def test_missing_device_on_a_live_router_needs_staff_review(
    staff, client, db, user, package, monkeypatch
):
    monkeypatch.setitem(app.dependency_overrides, get_require_device, lambda: True)
    payment = stuck_payment(db, user, package)

    case = client.get(f"/api/recovery/cases/{payment.id}").json()
    response = client.post(f"/api/recovery/cases/{payment.id}/retry")

    assert case["reason"] == "needs_device"
    assert case["action"] == "staff_review"
    assert response.status_code == 409
    assert response.json()["code"] == "needs_staff_review"


def test_router_failure_is_reported_as_an_outcome_not_an_error(
    staff, client, db, user, package, monkeypatch
):
    def fail_activation(**kwargs):
        raise RuntimeError("Mock router unavailable")

    monkeypatch.setattr("app.services.session_service.activate_access_device", fail_activation)
    payment = stuck_payment(db, user, package)

    response = client.post(f"/api/recovery/cases/{payment.id}/retry")

    assert response.status_code == 200
    assert response.json()["outcome"] == "activation_failed"
    assert "unavailable" not in response.text  # raw router text is never returned
    