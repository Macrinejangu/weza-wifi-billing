"""Gates that run BEFORE a Daraja callback is read.

Callbacks are not signed, so anyone who finds the URL can POST to it. These
checks turn strangers away cheaply, before we touch the database. They are
only a first line of defence: a payload must still match a payment we created
(callback_verification.py) and success is still confirmed with the STK status
query.

Everything fails closed: missing, malformed or ambiguous input is rejected.
"""
import hmac
import re

# What secrets.token_urlsafe(32) produces: URL-safe letters, digits, "_", "-".
# At least 32 characters, so a guessable token is refused at configuration time.
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,128}")

def is_valid_token_format(value: object) -> bool:
    """True only for a string that looks like a strong generated token."""
    return isinstance(value, str) and _TOKEN_PATTERN.fullmatch(value) is not None


def token_matches(received: object, configured: object) -> bool:
    """True only if `received` equals the configured secret path token.

    A misconfigured (empty, short or odd) token makes EVERY call fail, so a
    forgotten setting can never leave the endpoint open.
    """
    if not isinstance(received, str) or not is_valid_token_format(configured):
        return False
    # Compare as bytes: hmac.compare_digest raises TypeError on non-ASCII str.
    # errors="replace" cannot create a false match, because "?" is not in the
    # token alphabet and the configured token is pure ASCII.
    return hmac.compare_digest(
        received.encode("utf-8", errors="replace"),
        configured.encode("utf-8"),
    )