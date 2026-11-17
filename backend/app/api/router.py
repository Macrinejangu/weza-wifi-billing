
import logging
from hmac import compare_digest

from fastapi import APIRouter, Header, HTTPException

from app.config import router_settings, weza_api_key
from app.services.router import get_router_identity

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/router/status")
def router_status(x_weza_api_key: str | None = Header(default=None)):
    # Validate server-side API key configuration.
    try:
        expected_key = weza_api_key()
    except RuntimeError:
        logger.error("WEZA API key configuration is missing or invalid")
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured",
        ) from None

    # Validate the client-supplied key safely.
    if not isinstance(x_weza_api_key, str) or not compare_digest(
        x_weza_api_key.encode("utf-8"),
        expected_key.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    # Require an expected router identity before attempting verification.
    try:
        settings = router_settings()
        expected_identity = settings["expected_identity"]

        if not expected_identity or not expected_identity.strip():
            logger.error("Expected MikroTik router identity is not configured")
            raise HTTPException(
                status_code=503,
                detail="Router identity verification is not configured",
            )

        expected_identity = expected_identity.strip()

        identity = get_router_identity()

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to communicate with MikroTik router")
        raise HTTPException(
            status_code=503,
            detail="Router is unavailable",
        ) from None

    actual_identity = (
        identity.get("name")
        if isinstance(identity, dict)
        else None
    )

    if not isinstance(actual_identity, str) or not actual_identity.strip():
        raise HTTPException(
            status_code=502,
            detail="Router did not provide a valid identity",
        )

    if actual_identity != expected_identity:
        logger.warning("Connected router identity does not match expected identity")
        raise HTTPException(
            status_code=502,
            detail="Connected router identity could not be verified",
        )

    return {
        "status": "connected",
        "identity": actual_identity,
    }
