from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text


def test_postgres_is_migrated_and_accepts_transactional_writes(test_database):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    actual_heads = set(MigrationContext.configure(test_database).get_current_heads())
    assert actual_heads == expected_heads

    test_database.execute(
        text("CREATE TEMP TABLE weza_smoke (value integer) ON COMMIT DROP")
    )
    test_database.execute(text("INSERT INTO weza_smoke VALUES (1)"))
    assert test_database.scalar(text("SELECT value FROM weza_smoke")) == 1
