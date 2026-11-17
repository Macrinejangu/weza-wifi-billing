
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def database_url(variable: str = "DATABASE_URL") -> URL:
    load_dotenv(ROOT_ENV)

    value = os.getenv(variable)
    if not value:
        raise RuntimeError(
            f"Set {variable} in the repository root .env or shell."
        )

    url = make_url(value)

    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            f"{variable} must use the postgresql+psycopg driver."
        )

    return url


def router_settings() -> dict:
    load_dotenv(ROOT_ENV)

    host = os.getenv("ROUTER_HOST")
    username = os.getenv("ROUTER_USERNAME")
    password = os.getenv("ROUTER_PASSWORD")
    expected_identity = os.getenv("EXPECTED_ROUTER_IDENTITY")

    if not all([host, username, password]):
        raise RuntimeError(
            "Set ROUTER_HOST, ROUTER_USERNAME and ROUTER_PASSWORD."
        )

    use_ssl_value = os.getenv("ROUTER_USE_SSL", "false").lower()

    if use_ssl_value not in {"true", "false"}:
        raise RuntimeError("ROUTER_USE_SSL must be true or false.")

    try:
        port = int(os.getenv("ROUTER_PORT", "8728"))
        timeout = float(os.getenv("ROUTER_TIMEOUT", "5"))
    except ValueError:
        raise RuntimeError(
            "ROUTER_PORT and ROUTER_TIMEOUT must be valid numbers."
        ) from None

    if not 1 <= port <= 65535:
        raise RuntimeError("ROUTER_PORT must be between 1 and 65535.")

    if timeout <= 0:
        raise RuntimeError("ROUTER_TIMEOUT must be greater than zero.")

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "timeout": timeout,
        "use_ssl": use_ssl_value == "true",
        "tls_ca_file": os.getenv("ROUTER_TLS_CA_FILE") or None,
        "tls_server_name": os.getenv("ROUTER_TLS_SERVER_NAME") or host,
        "expected_identity": expected_identity,
    }


def weza_api_key() -> str:
    load_dotenv(ROOT_ENV)

    value = os.getenv("WEZA_API_KEY")

    if not value:
        raise RuntimeError(
            "Set WEZA_API_KEY in the repository root .env."
        )

    return value
