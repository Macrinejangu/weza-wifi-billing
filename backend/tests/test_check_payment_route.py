"""HTTP tests for POST /api/recovery/cases/{payment_id}/check-payment (WEZA-63).

The staff login and Daraja client are replaced. No network.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.auth import current_staff
from app.api.routes.payments import get_daraja_client
from app.api.routes.recovery import get_require_device
from app.integrations.mpesa.errors import DarajaUnavailableError
from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.main import app
from app.models import AdminAuditLog, Payment
from app.payments.result_codes import failure_reason_for
from app.services.payment_status_check import AUDIT_ACTION

from test_payment_settlement import make_payment, make_purchase

PAID = StkQueryResult(StkQueryOutcome.PAID, result_code=0, result_desc="ok")
UNKNOWN = StkQueryResult(StkQueryOutcome.UNKNOWN)
FAILED = StkQueryResult(
    StkQueryOutcome.FAILED,
    result_code=1032,
    failure_reason=failure_reason_for(1032),
    result_desc="cancelled",
)


class FakeQuery:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def stk_query(self, checkout_request_id, timestamp=None):
        self.calls.append(checkout_request_id)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def staff(client, user, monkeypatch):
    monkeypatch.setenv("ROUTER_MODE", "mock")
    monkeypatch.setitem(app.dependency_overrides, current_staff, lambda: user)
    monkeypatch.setitem(app.dependency_overrides, get_require_device, lambda: False)
    return user


def use_daraja(monkeypatch, fake):
    monkeypatch.setitem(app.dependency_overrides, get_daraja_client, lambda: fake)


def pending_payment(db, user, package, status="pending", receipt=None):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase, status=status, receipt=receipt)
    payment.initiated_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    return payment.id


def path(payment_id):
    return f"/api/recovery/cases/{payment_id}/check-payment"


def status_of(db, payment_id):
    db.expire_all()
    return db.get(Payment, payment_id).status


def test_staff_login_is_required(client):
    assert client.post(path(1)).status_code == 401


def test_paid_answer_settles_and_is_audited(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package)
    fake = FakeQuery(PAID)
    use_daraja(monkeypatch, fake)

    response = client.post(path(payment_id))

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "settled"
    assert body["query_outcome"] == "paid"
    assert body["payment_status"] == "successful"
    assert body["fulfilment"] is not None
    assert status_of(db, payment_id) == "successful"
    assert len(fake.calls) == 1
    audits = db.scalars(
        select(AdminAuditLog).where(
            AdminAuditLog.entity_id == payment_id, AdminAuditLog.action == AUDIT_ACTION
        )
    ).all()
    assert [a.admin_id for a in audits] == [user.id]


def test_unknown_answer_leaves_it_pending(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package)
    use_daraja(monkeypatch, FakeQuery(UNKNOWN))

    response = client.post(path(payment_id))

    assert response.status_code == 200
    assert response.json()["outcome"] == "still_pending"
    assert status_of(db, payment_id) == "pending"


def test_failed_answer_is_shown_but_not_applied(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package)
    use_daraja(monkeypatch, FakeQuery(FAILED))

    response = client.post(path(payment_id))

    assert response.status_code == 200
    assert response.json()["outcome"] == "still_pending"
    assert response.json()["query_outcome"] == "failed"
    assert status_of(db, payment_id) == "pending"


def test_daraja_down_is_a_200_with_no_answer(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package)
    use_daraja(monkeypatch, FakeQuery(DarajaUnavailableError("u")))

    response = client.post(path(payment_id))

    assert response.status_code == 200
    assert response.json()["outcome"] == "no_answer"
    assert status_of(db, payment_id) == "pending"


def test_daraja_not_configured_is_a_503(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package)
    use_daraja(monkeypatch, None)

    response = client.post(path(payment_id))

    assert response.status_code == 503
    assert response.json()["code"] == "daraja_not_configured"
    assert status_of(db, payment_id) == "pending"


def test_settled_payment_is_a_409_and_not_queried(staff, client, db, user, package, monkeypatch):
    payment_id = pending_payment(db, user, package, status="successful", receipt="QGH0000001")
    fake = FakeQuery(PAID)
    use_daraja(monkeypatch, fake)

    response = client.post(path(payment_id))

    assert response.status_code == 409
    assert response.json()["code"] == "payment_not_open"
    assert fake.calls == []


def test_unknown_payment_is_a_404(staff, client, monkeypatch):
    use_daraja(monkeypatch, FakeQuery(PAID))

    assert client.post(path(999_999_999)).status_code == 404
    