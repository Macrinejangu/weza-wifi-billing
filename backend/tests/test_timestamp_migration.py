from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.models import AccessPoint, Subscription, User

TABLES = ("access_points", "subscriptions", "users")
KNOWN_TIME = datetime(2020, 1, 1, tzinfo=timezone.utc)


def test_timestamp_upgrade_and_downgrade_with_existing_rows(test_database):
    # Run real Alembic commands in a schema rolled back with the test transaction.
    schema = f"timestamp_test_{uuid4().hex}"
    test_database.execute(text(f"CREATE SCHEMA {schema}"))
    test_database.execute(text(f"SET LOCAL search_path TO {schema}"))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = test_database
    command.upgrade(config, "0002")

    test_database.execute(text("""
        INSERT INTO packages
            (id, name, service_type, price, duration_minutes,
             download_speed_mbps, upload_speed_mbps, is_active)
        VALUES (1, 'Test package', 'hotspot', 20, 60, 5, 2, true)
    """))
    for row_id, created_at in ((1, None), (2, KNOWN_TIME)):
        values = {"id": row_id, "created_at": created_at, "email": f"{row_id}@weza.test"}
        test_database.execute(text("""
            INSERT INTO users (id, full_name, email, password_hash, role, created_at)
            VALUES (:id, 'Test user', :email, 'x', 'customer', :created_at)
        """), values)
        test_database.execute(text("""
            INSERT INTO access_points (id, name, status, created_at)
            VALUES (:id, 'Test access point', 'offline', :created_at)
        """), values)
        test_database.execute(text("""
            INSERT INTO subscriptions (id, user_id, package_id, status, created_at)
            VALUES (:id, :id, 1, 'pending', :created_at)
        """), values)

    command.upgrade(config, "0003")
    assert MigrationContext.configure(test_database).get_current_revision() == "0003"
    migration_time = test_database.scalar(text("SELECT now()"))

    for table in TABLES:
        columns = {column["name"]: column for column in inspect(test_database).get_columns(table)}
        for name in ("created_at", "updated_at"):
            assert columns[name]["nullable"] is False
            assert columns[name]["type"].timezone is True
        rows = test_database.execute(
            text(f"SELECT id, created_at, updated_at FROM {table} ORDER BY id")
        ).all()
        assert rows == [(1, migration_time, migration_time), (2, KNOWN_TIME, migration_time)]

    command.downgrade(config, "0002")
    assert MigrationContext.configure(test_database).get_current_revision() == "0002"
    for table in TABLES:
        columns = {column["name"]: column for column in inspect(test_database).get_columns(table)}
        assert columns["created_at"]["nullable"] is True
        assert "updated_at" not in columns
        assert test_database.execute(
            text(f"SELECT id, created_at FROM {table} ORDER BY id")
        ).all() == [(1, migration_time), (2, KNOWN_TIME)]
        test_database.execute(text(f"UPDATE {table} SET created_at = NULL WHERE id = 1"))


def test_sqlalchemy_advances_updated_at_for_all_three_models(db, user, package):
    access_point = AccessPoint(name="Test access point", updated_at=KNOWN_TIME)
    subscription = Subscription(user_id=user.id, package_id=package.id, updated_at=KNOWN_TIME)
    user.updated_at = KNOWN_TIME
    db.add_all([access_point, subscription])
    db.flush()

    records = (user, access_point, subscription)
    original_created_at = [record.created_at for record in records]
    assert all(record.updated_at == KNOWN_TIME for record in records)

    user.full_name = "Updated name"
    access_point.name = "Updated access point"
    subscription.status = "active"
    db.flush()
    for record, created_at in zip(records, original_created_at):
        db.refresh(record)
        assert record.created_at == created_at
        assert record.updated_at > KNOWN_TIME
        assert record.updated_at.utcoffset() is not None
