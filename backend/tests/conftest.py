import os

import pytest

from app.db.connection import create_database_engine


@pytest.fixture
def test_database():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL integration test.")

    engine = create_database_engine("TEST_DATABASE_URL")
    try:
        with engine.begin() as connection:
            yield connection
    finally:
        engine.dispose()

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import Package, User


@pytest.fixture
def db(test_database):
    """A database session whose changes are undone after each test."""
    session = Session(bind=test_database, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    test_database.rollback()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


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
