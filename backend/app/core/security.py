import hashlib
import hmac
import os
import time

import jwt
from dotenv import load_dotenv

from app.config import ROOT_ENV


def hash_password(password: str) -> str:
    """scrypt with a random salt, stored as 'salt$hash'."""
    salt = os.urandom(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, key = stored.split("$")
    check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(check.hex(), key)


def _secret() -> str:
    load_dotenv(ROOT_ENV)
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("Set JWT_SECRET (at least 32 characters) in the repository root .env.")
    return secret


def create_token(user_id: int, minutes: int = 60) -> str:
    return jwt.encode({"sub": str(user_id), "exp": int(time.time()) + minutes * 60}, _secret(), algorithm="HS256")


def read_token(token: str) -> int | None:
    """The user id inside a valid, unexpired token, otherwise None."""
    try:
        return int(jwt.decode(token, _secret(), algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
