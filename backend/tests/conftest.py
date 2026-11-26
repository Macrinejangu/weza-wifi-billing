import os

import pytest

from app.db.connection import create_database_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import Package, User


@pytest.fixture(autouse=True)
def router_mode_mock(monkeypatch):
    """Run every test against the mock router unless the test says otherwise.

    get_access_authenticator() refuses to start unless ROUTER_MODE is exactly
    'mock' or 'mikrotik' (fail closed). CI exported it, so the suite only
    passed where that variable happened to be set. Setting it here makes the
    suite pass on any machine. Tests that need another mode call
    monkeypatch.setenv themselves, which runs later and wins.
    """
    monkeypatch.setenv("ROUTER_MODE", "mock")


@pytest.fixture(autouse=True)
def sandbox_router_override_off(monkeypatch):
    """Keep the live-router override closed unless a test opens it itself.

    A developer may export ALLOW_SANDBOX_ROUTER_ACTIVATION=true for an isolated
    lab. Tests must not inherit that from the shell, so they behave the same on
    every machine.
    """
    monkeypatch.delenv("ALLOW_SANDBOX_ROUTER_ACTIVATION", raising=False)


@pytest.fixture
def test_database():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL integration test.")

    engine = create_database_engine("TEST_DATABASE_URL")
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def db(test_database):
    """A database session whose changes are undone after each test."""
    session = Session(bind=test_database, join_transaction_mode="create_savepoint")
    with session:
        yield session


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "true")
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user(db):
    db.add(User(full_name="Test", email="t@weza.local", password_hash="x"))
    db.commit()
    return db.query(User).one()


@pytest.fixture
def package(db):
    db.add(Package(name="1 Hour", service_type="hotspot", price=20, duration_minutes=60,
                   download_speed_mbps=5, upload_speed_mbps=2))
    db.commit()
    return db.query(Package).one()
