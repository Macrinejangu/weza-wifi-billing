from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app.config import database_url


def create_database_engine(variable: str = "DATABASE_URL") -> Engine:
    return create_engine(database_url(variable), poolclass=NullPool)
