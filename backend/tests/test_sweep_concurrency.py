"""Two-connection concurrency test for the stale-payment sweep (WEZA-63).

Two threads sweep the SAME stale pending payment at the same moment, each on
its own database connection. The status query is slow, so both threads have a
PAID answer before either one settles. Only the database (row lock and
conditional update) can keep this to one settlement and one fulfilment.

Rows are really committed, so they are deleted afterwards, children first
(payment events, payment, purchase, package, user).
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.connection import create_database_engine
from app.integrations.mpesa.stk_query import StkQueryOutcome, StkQueryResult
from app.models import Package, Payment, PaymentEvent, Purchase, User
from app.services.payment_status_check import sweep_stale_payments

from test_payment_settlement import make_payment, make_purchase
from test_payment_status_check import FakeFulfil

QUERY_HOLD_SECONDS = 0.5
START_TIMEOUT_SECONDS = 10
THREAD_TIMEOUT_SECONDS = 30
PAID = StkQueryResult(StkQueryOutcome.PAID, result_code=0, result_desc="ok")
UNKNOWN = StkQueryResult(StkQueryOutcome.UNKNOWN)


class SlowQuery:
    """Thread-safe fake Daraja. Answers PAID only for our checkout id, so any
    other stale payment left in the test database is never settled."""

    def __init__(self, checkout):
        self.checkout = checkout
        self.calls = []
        self._lock = threading.Lock()

    def stk_query(self, checkout_request_id, timestamp=None):
        with self._lock:
            self.calls.append(checkout_request_id)
        time.sleep(QUERY_HOLD_SECONDS)
        return PAID if checkout_request_id == self.checkout else UNKNOWN


@pytest.fixture
def committed_stale_payment():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL integration test.")

    engine = create_database_engine("TEST_DATABASE_URL")
    suffix = uuid4().hex[:12]
    checkout = f"ws_CO_sweep_{suffix}"
    ids = {}
    try:
        with Session(engine) as db:
            user = User(
                full_name="Sweep race", email=f"sweep-{suffix}@weza.local", password_hash="x"
            )
            package = Package(
                name=f"Sweep {suffix}", service_type="hotspot", price=20,
                duration_minutes=60, download_speed_mbps=5, upload_speed_mbps=2,
            )
            db.add_all([user, package])
            db.commit()
            ids["user"], ids["package"] = user.id, package.id
            purchase = make_purchase(db, user, package, key=f"sweep-race-{suffix}")
            payment = make_payment(db, purchase, checkout=checkout, status="pending", receipt=None)
            payment.initiated_at = datetime.now(UTC) - timedelta(hours=1)
            db.commit()
            ids["purchase"], ids["payment"] = purchase.id, payment.id
        yield engine, checkout, ids["payment"]
    finally:
        with Session(engine) as db:
            if "payment" in ids:
                db.execute(delete(PaymentEvent).where(PaymentEvent.payment_id == ids["payment"]))
                db.execute(delete(Payment).where(Payment.id == ids["payment"]))
            if "purchase" in ids:
                db.execute(delete(Purchase).where(Purchase.id == ids["purchase"]))
            if "package" in ids:
                db.execute(delete(Package).where(Package.id == ids["package"]))
            if "user" in ids:
                db.execute(delete(User).where(User.id == ids["user"]))
            db.commit()
        engine.dispose()


def test_two_simultaneous_sweeps_settle_and_fulfil_once(committed_stale_payment):
    engine, checkout, payment_id = committed_stale_payment
    query = SlowQuery(checkout)
    fulfil = FakeFulfil()
    start = threading.Barrier(2, timeout=START_TIMEOUT_SECONDS)

    def sweep():
        with Session(engine) as db:
            start.wait()
            sweep_stale_payments(
                db, query, now=datetime.now(UTC), limit=100, fulfil=fulfil
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(sweep), pool.submit(sweep)]
        for future in futures:
            future.result(timeout=THREAD_TIMEOUT_SECONDS)

    # Both threads really asked Daraja, so the race happened.
    assert query.calls.count(checkout) == 2

    with Session(engine) as db:
        payment = db.get(Payment, payment_id)
        purchase = db.get(Purchase, payment.purchase_id)
        assert payment.status == "successful"
        assert payment.mpesa_receipt_number is None
        assert payment.paid_at is not None
        assert purchase.status == "paid"

    assert fulfil.calls == [payment_id]
    