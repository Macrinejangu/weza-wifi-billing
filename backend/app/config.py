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



def router_settings() -> dict:
    load_dotenv(ROOT_ENV)

    host = os.getenv("ROUTER_HOST")
    username = os.getenv("ROUTER_USERNAME")
    password = os.getenv("ROUTER_PASSWORD")

    if not all([host, username, password]):
        raise RuntimeError(
            "Set ROUTER_HOST, ROUTER_USERNAME and ROUTER_PASSWORD."
        )

    return {
        "host": host,
        "port": int(os.getenv("ROUTER_PORT", "8728")),
        "username": username,
        "password": password,
        "timeout": float(os.getenv("ROUTER_TIMEOUT", "5")),
    }


def weza_api_key() -> str:
    load_dotenv(ROOT_ENV)

    value = os.getenv("WEZA_API_KEY")
    if not value:
        raise RuntimeError("Set WEZA_API_KEY in the repository root .env.")

    return value
