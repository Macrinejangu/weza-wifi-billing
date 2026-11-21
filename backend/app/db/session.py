from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.db.connection import create_database_engine


@lru_cache(maxsize=1)
def database_sessions():
    return sessionmaker(bind=create_database_engine())


def get_db():
    with database_sessions()() as db:
        yield db
