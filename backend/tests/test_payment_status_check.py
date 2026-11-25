"""Tests for check_payment and sweep_stale_payments (WEZA-63). No network."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import AdminAuditLog, Payment
from app.payments.result_codes import failure_reason_for
from app.services.payment_fulfilment import FulfilmentOutcome, FulfilmentResult
from app.services.payment_status_check import (
    AUDIT_ACTION,
    CheckOutcome,
    PaymentNotCheckable,
    check_payment,
    sweep_stale_payments,
)

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
    """Records every query. `answers` maps a checkout id to a result or an
    exception instance (raised); anything else gets `default`."""

    def __init__(self, default=UNKNOWN, answers=None):
        self.default, self.answers, self.calls = default, answers or {}, []

    def stk_query(self, checkout_request_id, timestamp=None):
        self.calls.append(checkout_request_id)
        answer = self.answers.get(checkout_request_id, self.default)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeFulfil:
    def __init__(self):
        self.calls = []

    def __call__(self, db, payment_id):
        self.calls.append(payment_id)
        return FulfilmentResult(payment_id, 1, FulfilmentOutcome.ACTIVATED)


def stale_payment(db, user, package, key, checkout, *, age=timedelta(hours=1),
                  status="pending", receipt=None):
    """One purchase and one payment, initiated `age` ago. Returns (payment, purchase) ids."""
    purchase = make_purchase(db, user, package, key=key)
    payment = make_payment(db, purchase, checkout=checkout, status=status, receipt=receipt)
    payment.initiated_at = datetime.now(UTC) - age
    db.commit()
    return payment.id, purchase.id


def reload(db, payment_id):
    db.expire_all()
    return db.get(Payment, payment_id)


# ---------------------------------------------------------------- check_payment

def test_check_paid_settles_and_fulfils(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    daraja, fulfil = FakeQuery(PAID), FakeFulfil()

    result = check_payment(db, daraja, payment_id, fulfil=fulfil)

    assert result.outcome is CheckOutcome.SETTLED
    assert result.query_outcome == "paid"
    assert result.payment_status == "successful"
    assert result.fulfilment is FulfilmentOutcome.ACTIVATED
    assert daraja.calls == ["ws_CO_a"]
    assert fulfil.calls == [payment_id]
    assert reload(db, payment_id).status == "successful"


def test_check_unknown_leaves_the_payment_pending(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    fulfil = FakeFulfil()

    result = check_payment(db, FakeQuery(UNKNOWN), payment_id, fulfil=fulfil)

    assert result.outcome is CheckOutcome.STILL_PENDING
    assert result.query_outcome == "unknown"
    assert reload(db, payment_id).status == "pending"
    assert fulfil.calls == []


def test_check_failed_alone_is_reported_but_never_applied(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    fulfil = FakeFulfil()

    result = check_payment(db, FakeQuery(FAILED), payment_id, fulfil=fulfil)

    assert result.outcome is CheckOutcome.STILL_PENDING
    assert result.query_outcome == "failed"  # staff can see what Safaricom said
    assert reload(db, payment_id).status == "pending"
    assert fulfil.calls == []


@pytest.mark.parametrize(
    "error",
    [
        DarajaTimeoutError("t"),
        DarajaUnavailableError("u"),
        DarajaAuthError("a"),
        ValueError("v"),
    ],
)
def test_check_query_error_is_no_answer_and_changes_nothing(db, user, package, error):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    fulfil = FakeFulfil()

    result = check_payment(db, FakeQuery(error), payment_id, fulfil=fulfil)

    assert result.outcome is CheckOutcome.NO_ANSWER
    assert result.query_outcome is None
    assert reload(db, payment_id).status == "pending"
    assert fulfil.calls == []


def test_check_without_a_client_is_no_answer(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")

    result = check_payment(db, None, payment_id, fulfil=FakeFulfil())

    assert result.outcome is CheckOutcome.NO_ANSWER
    assert reload(db, payment_id).status == "pending"


def test_check_refuses_a_settled_payment_without_querying(db, user, package):
    payment_id, _ = stale_payment(
        db, user, package, "k-a", "ws_CO_a", status="successful", receipt="QGH0000001"
    )
    daraja = FakeQuery(PAID)

    with pytest.raises(PaymentNotCheckable) as refused:
        check_payment(db, daraja, payment_id, fulfil=FakeFulfil())

    assert refused.value.code == "payment_not_open"
    assert daraja.calls == []


def test_check_refuses_a_failed_payment_without_querying(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a", status="failed")
    daraja = FakeQuery(PAID)

    with pytest.raises(PaymentNotCheckable):
        check_payment(db, daraja, payment_id, fulfil=FakeFulfil())

    assert daraja.calls == []
    assert reload(db, payment_id).status == "failed"


def test_check_refuses_a_payment_with_no_checkout_id(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", None)
    daraja = FakeQuery(PAID)

    with pytest.raises(PaymentNotCheckable) as refused:
        check_payment(db, daraja, payment_id, fulfil=FakeFulfil())

    assert refused.value.code == "no_checkout_request_id"
    assert daraja.calls == []


def test_check_unknown_payment_raises_lookup_error(db):
    with pytest.raises(LookupError):
        check_payment(db, FakeQuery(PAID), 999_999_999, fulfil=FakeFulfil())


def test_staff_check_is_audited_even_without_an_answer(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")

    check_payment(
        db, FakeQuery(DarajaUnavailableError("u")), payment_id,
        fulfil=FakeFulfil(), staff_id=user.id,
    )

    db.expire_all()
    [audit] = db.scalars(
        select(AdminAuditLog).where(
            AdminAuditLog.entity_id == payment_id,
            AdminAuditLog.action == AUDIT_ACTION,
        )
    ).all()
    assert audit.admin_id == user.id
    assert audit.new_values["outcome"] == "no_answer"


# ---------------------------------------------------------- sweep_stale_payments

def test_sweep_settles_a_stale_paid_payment(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    fulfil = FakeFulfil()

    summary = sweep_stale_payments(db, FakeQuery(PAID), fulfil=fulfil)

    assert (summary.examined, summary.settled, summary.errors) == (1, 1, 0)
    assert reload(db, payment_id).status == "successful"
    assert fulfil.calls == [payment_id]


def test_sweep_ignores_a_fresh_pending_payment(db, user, package):
    stale_payment(db, user, package, "k-a", "ws_CO_a", age=timedelta(minutes=1))
    daraja = FakeQuery(PAID)

    summary = sweep_stale_payments(db, daraja, fulfil=FakeFulfil())

    assert summary.examined == 0
    assert daraja.calls == []  # the customer may still be at the PIN prompt


def test_sweep_ignores_settled_payments(db, user, package):
    stale_payment(
        db, user, package, "k-a", "ws_CO_a", status="successful", receipt="QGH0000001"
    )
    stale_payment(db, user, package, "k-b", "ws_CO_b", status="failed")
    daraja = FakeQuery(PAID)

    summary = sweep_stale_payments(db, daraja, fulfil=FakeFulfil())

    assert summary.examined == 0
    assert daraja.calls == []


def test_sweep_ignores_a_pending_payment_without_a_checkout_id(db, user, package):
    stale_payment(db, user, package, "k-a", None)
    daraja = FakeQuery(PAID)

    summary = sweep_stale_payments(db, daraja, fulfil=FakeFulfil())

    assert summary.examined == 0
    assert daraja.calls == []


def test_sweep_carries_on_after_a_failed_query(db, user, package):
    first, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    second, _ = stale_payment(db, user, package, "k-b", "ws_CO_b")
    daraja = FakeQuery(PAID, answers={"ws_CO_a": DarajaUnavailableError("u")})

    summary = sweep_stale_payments(db, daraja, fulfil=FakeFulfil())

    assert (summary.examined, summary.no_answer, summary.settled) == (2, 1, 1)
    assert reload(db, first).status == "pending"
    assert reload(db, second).status == "successful"


def test_sweep_respects_the_limit_and_goes_lowest_id_first(db, user, package):
    for letter in "abc":
        stale_payment(db, user, package, f"k-{letter}", f"ws_CO_{letter}")
    daraja = FakeQuery(UNKNOWN)

    summary = sweep_stale_payments(db, daraja, limit=2, fulfil=FakeFulfil())

    assert summary.examined == 2
    assert daraja.calls == ["ws_CO_a", "ws_CO_b"]


def test_a_second_sweep_finds_nothing_and_fulfils_once(db, user, package):
    payment_id, _ = stale_payment(db, user, package, "k-a", "ws_CO_a")
    fulfil = FakeFulfil()

    first = sweep_stale_payments(db, FakeQuery(PAID), fulfil=fulfil)
    second = sweep_stale_payments(db, FakeQuery(PAID), fulfil=fulfil)

    assert first.settled == 1
    assert second.examined == 0
    assert fulfil.calls == [payment_id]


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_sweep_rejects_a_bad_limit(db, limit):
    with pytest.raises(ValueError):
        sweep_stale_payments(db, FakeQuery(PAID), limit=limit)
        