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
from dataclasses import dataclass, field
from enum import StrEnum

from app.payments.callback_ip_policy import CallbackIpPolicy

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



class CallbackDecision(StrEnum):
    """Outcome of the pre-read gates. The caller answers BOTH rejections with
    the same plain 404, but logs which gate stopped the request."""

    ALLOWED = "allowed"
    REJECTED_IP = "rejected_ip"
    REJECTED_TOKEN = "rejected_token"


@dataclass(frozen=True)
class CallbackSecurityPolicy:
    """The IP gate and the secret path token, checked in a fixed order.

    The token is required even when the IP policy is disabled, so switching
    the IP gate off for local tunnel work can never leave the endpoint open.
    """

    ip_policy: CallbackIpPolicy
    # repr=False keeps the secret out of logs and tracebacks.
    token: str = field(repr=False)

    def __post_init__(self) -> None:
        # A weak or missing token is a configuration mistake: refuse to start
        # rather than run with a guessable callback URL.
        if not is_valid_token_format(self.token):
            raise ValueError(
                "callback token must be 32 to 128 URL-safe characters"
            )

    def check(
        self,
        *,
        peer: object,
        forwarded_for: object,
        received_token: object,
    ) -> CallbackDecision:
        """Return ALLOWED only if the address and the token both pass."""
        # Cheapest check first, and a fixed order so the same bad request
        # always gets the same decision (easier to log and test).
        if not self.ip_policy.permits(peer, forwarded_for):
            return CallbackDecision.REJECTED_IP
        if not token_matches(received_token, self.token):
            return CallbackDecision.REJECTED_TOKEN
        return CallbackDecision.ALLOWED