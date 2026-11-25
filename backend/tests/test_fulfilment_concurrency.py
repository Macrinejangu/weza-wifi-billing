"""Two-connection concurrency test for duplicate fulfilment (WEZA-51).

Two threads call fulfil_payment for the SAME confirmed payment at the same
moment, each on its own database connection. Only the row locks taken by
create_session (payment row) and activate_session (session row) can keep
this to one session and one router call.

The fake router sleeps while the session row is locked, so the second
thread is guaranteed to arrive while the first is still inside the router.
(A barrier inside the router would deadlock: the second thread is blocked
on the lock and could never reach it.)

Rows are really committed, so they are deleted afterwards, children first
(attempts, sessions, subscriptions, payment, purchase, package, user).
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.connection import create_database_engine
from app.models import (
    ActivationAttempt,
    Package,
    Payment,
    Purchase,
    Subscription,
    User,
    WiFiSession,
)
from app.services.payment_fulfilment import FulfilmentOutcome, fulfil_payment

from test_payment_settlement import make_payment, make_purchase

ROUTER_HOLD_SECONDS = 0.5
START_TIMEOUT_SECONDS = 10
THREAD_TIMEOUT_SECONDS = 30


class SlowRouter:
    """Thread-safe fake router: counts calls and holds the lock window open."""

    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()

    def __call__(self, session_id):
        with self._lock:
            self.calls.append(session_id)
        time.sleep(ROUTER_HOLD_SECONDS)
        return {"status": "ACTIVE"}


@pytest.fixture
def engine():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL concurrency test.")
    engine = create_database_engine("TEST_DATABASE_URL")
    yield engine
    engine.dispose()


@pytest.fixture
def confirmed(engine):
    """Real committed rows for one CONFIRMED payment, deleted afterwards."""
    suffix = uuid4().hex[:12]
    with Session(engine) as setup:
        user = User(full_name="Fulfil Race", email=f"fulfil-{suffix}@weza.local",
                    password_hash="x")
        package = Package(name=f"Fulfil {suffix}", service_type="hotspot", price=20,
                          duration_minutes=60, download_speed_mbps=5,
                          upload_speed_mbps=2)
        setup.add_all([user, package])
        setup.commit()
        purchase = make_purchase(setup, user, package, key=f"fulfil-{suffix}",
                                 status="paid")
        payment = make_payment(setup, purchase, checkout=f"ws_CO_fulfil_{suffix}",
                               status="successful", receipt=f"F{suffix.upper()}")
        # Settlement sets paid_at for real payments, and create_session
        # refuses a payment without it.
        payment.paid_at = datetime.now(timezone.utc)
        setup.commit()
        ids = {
            "user": user.id,
            "package": package.id,
            "purchase": purchase.id,
            "payment": payment.id,
        }

    yield ids

    # Children before parents (foreign keys). Sessions point at subscriptions,
    # so sessions go first.
    with Session(engine) as cleanup:
        cleanup.execute(delete(ActivationAttempt).where(
            ActivationAttempt.session_id.in_(
                select(WiFiSession.id).where(
                    WiFiSession.payment_id == ids["payment"]
                )
            )
        ))
        cleanup.execute(delete(WiFiSession).where(
            WiFiSession.payment_id == ids["payment"]
        ))
        cleanup.execute(delete(Subscription).where(
            Subscription.payment_id == ids["payment"]
        ))
        cleanup.execute(delete(Payment).where(Payment.id == ids["payment"]))
        cleanup.execute(delete(Purchase).where(Purchase.id == ids["purchase"]))
        cleanup.execute(delete(Package).where(Package.id == ids["package"]))
        cleanup.execute(delete(User).where(User.id == ids["user"]))
        cleanup.commit()


def fulfil_on_own_connection(engine, payment_id, router, start):
    """One fulfilment on its OWN session. Waits at the start line first."""
    with Session(engine) as session:
        start.wait(timeout=START_TIMEOUT_SECONDS)
        return fulfil_payment(session, payment_id, router=router)


def test_two_simultaneous_fulfilments_make_one_session_and_one_router_call(
    engine, confirmed
):
    router = SlowRouter()
    start = threading.Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                fulfil_on_own_connection, engine, confirmed["payment"], router, start
            )
            for _ in range(2)
        ]
        # .result() re-raises thread exceptions, so a crash fails the test.
        results = [f.result(timeout=THREAD_TIMEOUT_SECONDS) for f in futures]

    # The router was asked exactly once, however the threads interleaved.
    assert len(router.calls) == 1

    with Session(engine) as check:
        sessions = check.scalars(
            select(WiFiSession).where(WiFiSession.payment_id == confirmed["payment"])
        ).all()
        attempts = check.scalars(
            select(ActivationAttempt).where(
                ActivationAttempt.session_id == sessions[0].id
            )
        ).all()
        payment = check.get(Payment, confirmed["payment"])

        assert len(sessions) == 1
        assert (sessions[0].status, sessions[0].activation_status) == (
            "ACTIVE", "succeeded",
        )
        assert len(attempts) == 1
        assert payment.status == "successful"

    # Both callers see the truth: access is active. The loser of the race
    # waited on the lock and then found the work already done.
    assert [r.outcome for r in results] == [FulfilmentOutcome.ACTIVATED] * 2
    assert results[0].session_id == results[1].session_id
