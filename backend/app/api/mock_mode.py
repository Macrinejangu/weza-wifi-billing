import os

from fastapi import HTTPException

from app.config import ROOT_ENV
from dotenv import load_dotenv


def require_mock_mode() -> None:
    load_dotenv(ROOT_ENV)
    if os.getenv("ENABLE_MOCK_PAYMENTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
