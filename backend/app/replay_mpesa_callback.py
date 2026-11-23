"""Replay a stored Daraja sandbox callback without starting a payment."""

import argparse

import httpx

from app.config import daraja_settings
from app.db.session import database_sessions
from app.integrations.mpesa.client import DarajaClient
from app.services.callback_processing import replay_callback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_id", type=int, help="Original callback audit event ID")
    args = parser.parse_args()

    try:
        settings = daraja_settings()
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")

    with httpx.Client() as client, database_sessions()() as db:
        try:
            result = replay_callback(db, DarajaClient(settings, client), args.event_id)
        except (LookupError, ValueError) as error:
            parser.exit(1, f"{error}\n")

    print(f"Callback event {args.event_id}: {result.outcome.value}")


if __name__ == "__main__":
    main()
