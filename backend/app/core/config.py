import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


def database_url() -> URL:
    load_dotenv(ROOT_ENV)
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL in the repository root .env or shell.")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use the postgresql+psycopg driver.")
    return url
