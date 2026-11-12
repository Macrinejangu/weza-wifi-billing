import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def database_url(variable: str = "DATABASE_URL") -> URL:
    load_dotenv(ROOT_ENV)
    value = os.getenv(variable)
    if not value:
        raise RuntimeError(f"Set {variable} in the repository root .env or shell.")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(f"{variable} must use the postgresql+psycopg driver.")
    return url
