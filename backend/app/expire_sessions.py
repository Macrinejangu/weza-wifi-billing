import argparse
import logging
import os
from time import sleep

from app.db.session import database_sessions
from app.services.session_expiry import expire_due_sessions


def main():
    parser = argparse.ArgumentParser(description="Revoke access for expired Weza sessions.")
    parser.add_argument("--once", action="store_true", help="Process expired sessions once and exit.")
    parser.add_argument("--interval", type=int, default=os.getenv("WEZA_EXPIRY_INTERVAL_SECONDS", "2"))
    parser.add_argument("--batch-size", type=int, default=os.getenv("WEZA_EXPIRY_BATCH_SIZE", "50"))
    args = parser.parse_args()
    if args.interval < 1 or args.batch_size < 1:
        parser.error("interval and batch size must be positive")
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    while True:
        with database_sessions()() as db:
            try:
                count = expire_due_sessions(db, limit=args.batch_size)
            except Exception as error:
                logger.error("Could not check session expiry: %s", type(error).__name__)
                if args.once:
                    raise SystemExit(1) from None
            else:
                if count or args.once:
                    logger.info("Ended %s expired sessions", count)
        if args.once:
            return
        sleep(args.interval)


if __name__ == "__main__":
    main()
