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
