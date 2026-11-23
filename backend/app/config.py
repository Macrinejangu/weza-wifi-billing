
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

from app.payments.callback_ip_policy import CallbackIpPolicy
from app.payments.callback_security import CallbackSecurityPolicy, is_valid_token_format

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


# Safaricom has two kinds of business number, and Daraja needs a different
# TransactionType for each. Which one Weza uses is not yet confirmed, so it is
# a setting rather than a hard-coded choice.
ACCOUNT_PAYBILL = "paybill"
ACCOUNT_TILL = "till"
_ACCOUNT_TYPES = (ACCOUNT_PAYBILL, ACCOUNT_TILL)


@dataclass(frozen=True)
class DarajaSettings:
    """Safaricom Daraja (M-Pesa Express) settings, read from the environment.

    Frozen so that settings cannot be changed accidentally while the app runs.
    The credentials use repr=False so they are never printed in logs or tracebacks.
    """

    environment: str
    consumer_key: str = field(repr=False)
    consumer_secret: str = field(repr=False)
    shortcode: str
    passkey: str = field(repr=False)
    callback_url: str
    # PartyB is the organisation that receives the money. For a paybill it is the shortcode. 
    # For a till it is set separately: the till path is not yet verified against Safaricom's documentation or the sandbox.
    account_type: str = ACCOUNT_PAYBILL
    party_b: str | None = None


def daraja_settings() -> DarajaSettings:
    """Load and validate the Daraja settings from the repository root .env or shell.

    Raises RuntimeError if a value is missing, if DARAJA_ENV is anything other
    than "sandbox", or if the callback URL is not HTTPS. This project is
    sandbox-only: refusing other environments here stops a mistake from ever
    sending a request to the production Daraja API.
    """
    load_dotenv(ROOT_ENV)

    environment = os.getenv("DARAJA_ENV", "sandbox")
    if environment != "sandbox":
        raise RuntimeError("DARAJA_ENV must be 'sandbox'. Production is not supported.")

    # Collect every missing name first so the developer fixes them in one go.
    names = [
        "DARAJA_CONSUMER_KEY",
        "DARAJA_CONSUMER_SECRET",
        "DARAJA_SHORTCODE",
        "DARAJA_PASSKEY",
        "DARAJA_CALLBACK_URL",
    ]

    values = {name: os.getenv(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} in the repository root .env or shell.")

    # We require HTTPS because callbacks carry payment data.
    if not values["DARAJA_CALLBACK_URL"].startswith("https://"):
        raise RuntimeError("DARAJA_CALLBACK_URL must start with https://")

    # strip and lower-case so "Till " in a .env file is not a startup failure.
    # An empty or unknown value is still rejected: we never guess.
    account_type = os.getenv("DARAJA_ACCOUNT_TYPE", ACCOUNT_PAYBILL).strip().lower()
    if account_type not in _ACCOUNT_TYPES:
        raise RuntimeError("DARAJA_ACCOUNT_TYPE must be 'paybill' or 'till'.")

    if account_type == ACCOUNT_TILL:
        # A till needs its own receiving number. Falling back to the shortcode
        # would risk directing the payment at the wrong party.
        party_b = (os.getenv("DARAJA_PARTY_B") or "").strip()
        if not party_b:
            raise RuntimeError("Set DARAJA_PARTY_B when DARAJA_ACCOUNT_TYPE is 'till'.")
        # isascii() first: str.isdigit() also accepts digits from other scripts.
        if not (party_b.isascii() and party_b.isdigit()):
            raise RuntimeError("DARAJA_PARTY_B must contain digits only.")
    else:
        party_b = values["DARAJA_SHORTCODE"]

    return DarajaSettings(
        environment=environment,
        consumer_key=values["DARAJA_CONSUMER_KEY"],
        consumer_secret=values["DARAJA_CONSUMER_SECRET"],
        shortcode=values["DARAJA_SHORTCODE"],
        passkey=values["DARAJA_PASSKEY"],
        callback_url=values["DARAJA_CALLBACK_URL"],
        account_type=account_type,
        party_b=party_b,
    )


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


def _read_bool(name: str, default: bool) -> bool:
    """Read a strict true/false setting.

    Anything else is an error, not "false": a typo such as "ture" must not
    silently switch a security gate off.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise RuntimeError(f"{name} must be 'true' or 'false'.")


def _read_list(name: str) -> list[str]:
    """Read a comma-separated setting into a list, ignoring blanks."""
    return [part.strip() for part in os.getenv(name, "").split(",") if part.strip()]


def callback_security_policy() -> CallbackSecurityPolicy:
    """Build the gates that protect the Daraja callback endpoint.

    Callbacks are not signed, so the endpoint is protected by a secret token
    in its URL path plus an optional source-IP check. Raises RuntimeError if
    the token is missing or weak, or if the registered callback URL does not
    end with the token (Safaricom would then call a path we reject).
    Error messages never include the token's value.
    """
    load_dotenv(ROOT_ENV)

    token = (os.getenv("DARAJA_CALLBACK_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("Set DARAJA_CALLBACK_TOKEN in the repository root .env or shell.")
    if not is_valid_token_format(token):
        raise RuntimeError(
            "DARAJA_CALLBACK_TOKEN must be 32 to 128 characters: "
            "letters, digits, '-' and '_' only."
        )

    callback_url = (os.getenv("DARAJA_CALLBACK_URL") or "").strip()
    if not callback_url.rstrip("/").endswith("/" + token):
        raise RuntimeError(
            "DARAJA_CALLBACK_URL must end with the DARAJA_CALLBACK_TOKEN value."
        )

    try:
        ip_policy = CallbackIpPolicy.create(
            enabled=_read_bool("CALLBACK_IP_CHECK_ENABLED", default=False),
            trusted_proxies=_read_list("CALLBACK_TRUSTED_PROXIES"),
        )
        return CallbackSecurityPolicy(ip_policy=ip_policy, token=token)
    except ValueError as error:
        # The ValueError texts name the setting, never a secret value.
        raise RuntimeError(f"Invalid callback security settings: {error}") from None