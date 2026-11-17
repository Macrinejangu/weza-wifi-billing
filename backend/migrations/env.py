from alembic import context
from app.config import database_url
from app.db.base import Base
from app.db.connection import create_database_engine
import app.models  # noqa: F401  (loads every table so Alembic can see it)


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_database_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
