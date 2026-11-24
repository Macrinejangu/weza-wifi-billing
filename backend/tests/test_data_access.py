"""Two customers and one staff account: access stays with the right person."""
import pytest

from app.api.auth import CUSTOMER_AUDIENCE
from app.core.security import create_token, hash_password
from app.models import User
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase

STAFF_ROUTES = [
    "/api/payments", "/api/payments/{payment_id}", "/api/sessions", "/api/customers", "/api/overview",
    "/api/network/devices", "/api/connection-issues", "/api/staff/settings", "/api/staff/settings/audit",
]


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)


def add_user(db, email, role):
    user = User(full_name=email.split("@")[0], email=email, role=role, status="active",
                password_hash=hash_password("correct-horse-battery"))
    db.add(user)
    db.commit()
    return user


def customer_headers(user):
    return {"Authorization": f"Bearer {create_token(user.id, audience=CUSTOMER_AUDIENCE)}"}


def staff_headers(user):
    return {"Authorization": f"Bearer {create_token(user.id)}"}


@pytest.fixture
def people(db, package):
    amina = add_user(db, "amina@weza.local", "customer")
    brian = add_user(db, "brian@weza.local", "customer")
    staff = add_user(db, "staff@weza.local", "admin")  # admin: the settings audit is admin-only
    payments = {}
    for owner, key in ((amina, "access-key-amina-1"), (brian, "access-key-brian-1")):
        purchase, _ = create_purchase(db, owner.id, package.id, key)
        payments[owner.id] = create_payment(db, purchase.id, "254712345678")
    return amina, brian, staff, payments


def test_each_customer_sees_only_their_own_payment(client, people):
    amina, brian, _, payments = people
    own = client.get(f"/api/customer/payments/{payments[amina.id].id}", headers=customer_headers(amina))
    assert own.status_code == 200 and own.json()["id"] == payments[amina.id].id
    for me, other in ((amina, brian), (brian, amina)):
        hidden = client.get(f"/api/customer/payments/{payments[other.id].id}", headers=customer_headers(me))
        assert hidden.status_code == 404


@pytest.mark.parametrize("route", STAFF_ROUTES)
def test_staff_routes_reject_customers_and_signed_out_users_but_open_for_staff(client, people, route):
    amina, _, staff, payments = people
    path = route.format(payment_id=payments[amina.id].id)
    assert client.get(path).status_code == 401
    assert client.get(path, headers=customer_headers(amina)).status_code in (401, 403)
    assert client.get(path, headers=staff_headers(staff)).status_code not in (401, 403)


def test_a_staff_token_does_not_open_customer_routes(client, people):
    amina, _, staff, payments = people
    response = client.get(f"/api/customer/payments/{payments[amina.id].id}", headers=staff_headers(staff))
    assert response.status_code == 401


def test_staff_can_see_both_customers_payments(client, people):
    _, _, staff, payments = people
    listed = client.get("/api/payments", headers=staff_headers(staff))
    assert listed.status_code == 200
    assert {payment["id"] for payment in listed.json()} == {payment.id for payment in payments.values()}
