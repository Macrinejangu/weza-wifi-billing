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
    salt_hex, separator, key_hex = stored.partition("$")
    if not separator or len(salt_hex) != 32 or len(key_hex) != 128:
        return False

    try:
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
    except ValueError:
        return False
    if len(salt) != 16 or len(key) != 64:
        return False

    check = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(check, key)


def _secret() -> str:
    load_dotenv(ROOT_ENV)
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("Set JWT_SECRET (at least 32 characters) in the repository root .env.")
    return secret


def create_token(user_id: int, minutes: int = 60, *, audience: str | None = None) -> str:
    claims = {"sub": str(user_id), "exp": int(time.time()) + minutes * 60}
    if audience is not None:
        claims["aud"] = audience
    return jwt.encode(claims, _secret(), algorithm="HS256")


def read_token(token: str, *, audience: str | None = None) -> int | None:
    """Read the user ID from a valid token issued for the expected audience."""
    try:
        claims = jwt.decode(
            token, _secret(), algorithms=["HS256"], audience=audience,
            options={"require": ["sub", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, TypeError, ValueError, OverflowError):
        return None
    return user_id if 0 < user_id <= 2**31 - 1 else None


def create_device_reference(claims: dict) -> str:
    return jwt.encode(
        {**claims, "aud": "checkout-device", "exp": int(time.time()) + 300},
        _secret(),
        algorithm="HS256",
    )


def read_device_reference(token: str) -> dict:
    try:
        return jwt.decode(
            token, _secret(), algorithms=["HS256"], audience="checkout-device",
            options={"require": ["exp", "aud", "ip", "mac", "user", "package", "key"]},
        )
    except jwt.PyJWTError:
        raise ValueError("Unknown or expired device reference") from None
