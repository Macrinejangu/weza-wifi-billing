from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def test_staff_migration_upgrades_and_downgrades_populated_0003(test_database):
    schema = f"staff_test_{uuid4().hex}"
    test_database.execute(text(f"CREATE SCHEMA {schema}"))
    test_database.execute(text(f"SET LOCAL search_path TO {schema}"))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = test_database
    command.upgrade(config, "0003")

    for role in ("customer", "operator", "admin"):
        test_database.execute(text("""
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES ('Test User', :email, 'legacy-hash', :role)
        """), {"email": f"{role}@weza.test", "role": role})
    timestamps = test_database.execute(text(
        "SELECT id, updated_at FROM users ORDER BY id"
    )).all()

    command.upgrade(config, "0004")
    assert MigrationContext.configure(test_database).get_current_revision() == "0004"
    assert test_database.execute(text(
        "SELECT role, status, password_hash FROM users ORDER BY id"
    )).all() == [(role, "active", "legacy-hash") for role in ("customer", "operator", "admin")]
    assert test_database.execute(text(
        "SELECT id, updated_at FROM users ORDER BY id"
    )).all() == timestamps

    for statement in ("UPDATE users SET role = 'unknown'", "UPDATE users SET status = 'unknown'"):
        with pytest.raises(IntegrityError), test_database.begin_nested():
            test_database.execute(text(statement))

    command.downgrade(config, "0003")
    assert MigrationContext.configure(test_database).get_current_revision() == "0003"
    columns = {column["name"] for column in inspect(test_database).get_columns("users")}
    assert "status" not in columns
    assert "updated_at" in columns
    assert test_database.execute(text(
        "SELECT id, updated_at FROM users ORDER BY id"
    )).all() == timestamps
