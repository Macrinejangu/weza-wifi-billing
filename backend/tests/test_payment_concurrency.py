"""Two-connection concurrency test for callback settlement (WEZA-50, WEZA-51).

Every other test runs inside one rolled-back transaction, which cannot show
a real race. This test commits real rows, then delivers the SAME callback on
two separate database connections at the same instant.

A barrier inside the fake status query makes the race certain: both threads
have read the payment as 'pending' in phase 1 before either one settles.
Only the SELECT ... FOR UPDATE in settle_payment can then prevent a double
apply. Fulfilment is the real one: after the race there must be exactly one
subscription, one session linked to it, and one succeeded attempt.

The rows are deleted afterwards because they were really committed. Cleanup
removes children before parents (foreign keys), including session,
attempt and subscription rows, so a failure here can never leave data that
breaks other tests.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.connection import create_database_engine
from app.models import (
    ActivationAttempt,
    Package,
    Payment,
    PaymentEvent,
    Purchase,
    Subscription,
    User,
    WiFiSession,
)
from app.services.callback_processing import process_callback
from app.services.payment_event_service import EventSource, record_received_event

from test_callback_processing import PAID, FakeDaraja, body
from test_payment_settlement import make_payment, make_purchase

BARRIER_TIMEOUT_SECONDS = 10
THREAD_TIMEOUT_SECONDS = 30


class BarrierDaraja(FakeDaraja):
    """A fake status query that waits until BOTH threads have reached it."""

    def __init__(self, result, barrier):
        super().__init__(result)
        self.barrier = barrier

    def stk_query(self, checkout_request_id, timestamp=None):
        # No row lock is held here (process_callback rolled back first), so
        # both threads can arrive. A timeout fails the test, never hangs it.
        self.barrier.wait(timeout=BARRIER_TIMEOUT_SECONDS)
        return super().stk_query(checkout_request_id, timestamp)


@pytest.fixture
def engine():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL concurrency test.")
    engine = create_database_engine("TEST_DATABASE_URL")
    yield engine
    engine.dispose()


@pytest.fixture
def committed(engine):
    """Real committed rows for one pending payment, deleted afterwards."""
    suffix = uuid4().hex[:12]
    checkout = f"ws_CO_race_{suffix}"
    receipt = f"R{suffix.upper()}"  # 13 alphanumerics: valid receipt shape

    with Session(engine) as setup:
        user = User(full_name="Race Test", email=f"race-{suffix}@weza.local",
                    password_hash="x")
        package = Package(name=f"Race {suffix}", service_type="hotspot", price=20,
                          duration_minutes=60, download_speed_mbps=5,
                          upload_speed_mbps=2)
        setup.add_all([user, package])
        setup.commit()
        purchase = make_purchase(setup, user, package, key=f"race-{suffix}")
        payment = make_payment(setup, purchase, checkout=checkout)
        ids = {
            "user": user.id,
            "package": package.id,
            "purchase": purchase.id,
            "payment": payment.id,
            "checkout": checkout,
            "receipt": receipt,
            "events": [],
        }

    yield ids

    # Delete children before parents (foreign keys):
    # events, attempts, sessions, subscriptions, payments, purchases,
    # package, user.
    with Session(engine) as cleanup:
        cleanup.execute(delete(PaymentEvent).where(
            (PaymentEvent.payment_id == ids["payment"])
            | (PaymentEvent.id.in_(ids["events"]))
        ))
        session_ids = select(WiFiSession.id).where(WiFiSession.payment_id == ids["payment"])
        cleanup.execute(delete(ActivationAttempt).where(ActivationAttempt.session_id.in_(session_ids)))
        cleanup.execute(delete(WiFiSession).where(WiFiSession.payment_id == ids["payment"]))
        cleanup.execute(delete(Subscription).where(Subscription.payment_id == ids["payment"]))
        cleanup.execute(delete(Payment).where(Payment.id == ids["payment"]))
        cleanup.execute(delete(Purchase).where(Purchase.id == ids["purchase"]))
        cleanup.execute(delete(Package).where(Package.id == ids["package"]))
        cleanup.execute(delete(User).where(User.id == ids["user"]))
        cleanup.commit()


def deliver(engine, daraja, committed, event_id):
    """One callback delivery on its OWN session, so its OWN connection."""
    payload = body(committed["checkout"], receipt=committed["receipt"])
    with Session(engine) as session:
        return process_callback(
            session, daraja,
            event_id=event_id, payload=payload, raw_payload={"test": True},
        )


def test_two_identical_callbacks_at_once_apply_exactly_once(engine, committed):
    # Two audit rows, as the route would have written for two deliveries.
    with Session(engine) as session:
        for _ in range(2):
            committed["events"].append(record_received_event(
                session, source=EventSource.CALLBACK, payload={"test": True},
            ))

    barrier = threading.Barrier(2)
    daraja = BarrierDaraja(PAID, barrier)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(deliver, engine, daraja, committed, event_id)
            for event_id in committed["events"]
        ]
        # .result() re-raises any exception from a thread, so a crash in
        # either delivery fails the test instead of being swallowed.
        results = [f.result(timeout=THREAD_TIMEOUT_SECONDS) for f in futures]

    # Both deliveries really did pass phase 1 before settling.
    assert len(daraja.calls) == 2

    with Session(engine) as check:
        statuses = sorted(
            check.scalars(
                select(PaymentEvent.processing_status).where(
                    PaymentEvent.id.in_(committed["events"])
                )
            ).all()
        )
        payment = check.get(Payment, committed["payment"])
        purchase = check.get(Purchase, committed["purchase"])
        successful = check.scalars(
            select(Payment.id).where(
                Payment.purchase_id == committed["purchase"],
                Payment.status == "successful",
            )
        ).all()

        assert statuses == ["applied", "duplicate"]
        assert sorted(r.outcome.value for r in results) == ["applied", "duplicate"]
        assert payment.status == "successful"
        assert payment.mpesa_receipt_number == committed["receipt"]
        assert purchase.status == "paid"
        assert successful == [committed["payment"]]

        # Only the delivery that applied the success started fulfilment, so
        # there is exactly one subscription, session and attempt (.one()
        # fails on zero or two).
        assert sorted(r.fulfilment is not None for r in results) == [False, True]
        subscription = check.scalars(
            select(Subscription).where(Subscription.payment_id == payment.id)
        ).one()
        session = check.scalars(
            select(WiFiSession).where(WiFiSession.payment_id == payment.id)
        ).one()
        attempt = check.scalars(
            select(ActivationAttempt).where(ActivationAttempt.session_id == session.id)
        ).one()
        assert session.subscription_id == subscription.id
        assert attempt.status == "succeeded"
