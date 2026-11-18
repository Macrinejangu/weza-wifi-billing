import os
from dataclasses import dataclass, field
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