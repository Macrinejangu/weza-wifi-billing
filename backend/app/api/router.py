import logging

from hmac import compare_digest

from fastapi import APIRouter, Header, HTTPException

from app.config import weza_api_key
from app.services.router import get_router_identity

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/router/status")
def router_status(x_weza_api_key: str | None = Header(default=None)):
    expected_key = weza_api_key()

    if not x_weza_api_key or not compare_digest(
        x_weza_api_key, expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    try:
        identity = get_router_identity()
    except Exception:
        logger.exception("Failed to communicate with MikroTik router")
        raise HTTPException(
            status_code=503,
            detail="Router is unavailable",
        ) from None


    return {
        "status": "connected",
        "identity": identity.get("name", "unknown"),
    }
