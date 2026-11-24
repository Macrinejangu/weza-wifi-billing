import logging
import os
import signal
from datetime import datetime
from threading import Event

from app.db.session import database_sessions
from app.services.session_expiry_service import expire_due_sessions


logger = logging.getLogger("weza.session_expiry")


def run_expiry_cycle(
    limit: int = 100,
    now: datetime | None = None,
) -> dict:
    """Run one database-backed session expiry cycle."""
    session_factory = database_sessions()

    with session_factory() as db:
        return expire_due_sessions(
            db=db,
            now=now,
            limit=limit,
        )


def run_worker(
    interval_seconds: int | None = None,
    batch_limit: int | None = None,
) -> None:
    """
    Run the expiry processor continuously.

    Configuration:
      WEZA_EXPIRY_INTERVAL_SECONDS: seconds between expiry cycles
      WEZA_EXPIRY_BATCH_SIZE: maximum sessions processed per cycle

    Runs independently of the operating system's scheduling service.
    """
    interval = (
        interval_seconds
        if interval_seconds is not None
        else int(os.getenv("WEZA_EXPIRY_INTERVAL_SECONDS", "30"))
    )

    limit = (
        batch_limit
        if batch_limit is not None
        else int(os.getenv("WEZA_EXPIRY_BATCH_SIZE", "100"))
    )

    if interval < 1:
        raise ValueError("Expiry interval must be at least one second")

    if limit < 1:
        raise ValueError("Expiry batch size must be greater than zero")

    stop_event = Event()

    def request_stop(signum, frame):
        logger.info("Received shutdown signal: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    logger.info(
        "WEZA session expiry worker started "
        "(interval=%s seconds, batch_limit=%s)",
        interval,
        limit,
    )

    while not stop_event.is_set():
        try:
            result = run_expiry_cycle(limit=limit)
            logger.info(
                "Expiry cycle completed: processed=%s expired=%s failed=%s",
                result.get("processed", 0),
                result.get("expired", 0),
                result.get("failed", 0),
            )
        except Exception:
            logger.exception("Expiry cycle failed; worker will retry")

        stop_event.wait(interval)

    logger.info("WEZA session expiry worker stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("WEZA_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_worker()
