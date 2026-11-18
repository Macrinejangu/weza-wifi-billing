"""In-memory cache for the Daraja OAuth access token.

Daraja tokens last about an hour, and every new token request invalidates the
previous token. The client therefore fetches one token, reuses it, and fetches
a new one only when this cache says the old one is (nearly) expired.

This class only stores and expires a token. It does no HTTP and takes no lock:
the client wraps "check the cache, fetch if empty, store" in one lock so that
concurrent requests cannot each fetch a token and invalidate each other's.

The token is a secret. Never log it, and never include it in an error message.
"""
import time
from collections.abc import Callable

# Treat the token as expired this many seconds before Daraja does, so a request
# that starts with a "valid" token does not fail halfway because it ran out.
EXPIRY_MARGIN_SECONDS = 60

class TokenCache:
    """Holds at most one access token and forgets it shortly before it expires."""
    def __init__(self, clock: Callable[[], float]=time.monotonic) -> None:
        # `clock` is injectable so tests can move time forward without sleeping.
        # time.monotonic is the default because it never jumps backwards whenthe system clock is adjusted, unlike time.time.
        self._clock=clock
        self._token: str | None=None
        self._expires_at: float=0.0

    def get(self)->str | None:
        """Return the cached token, or None if there is none or it has expired."""
        if self._token is None:
            return None
        if self._clock() >= self._expires_at:
            # Drop the stale token so it can never be handed out by mistake.
            self.invalidate()
            return None
        return self._token

    def store(self, token:str, expires_in: int)-> None:
        """Remember `token` for `expires_in` seconds, minus the safety margin.

        Raises ValueError for an empty token or a non-positive lifetime, so a
        malformed Daraja response is never cached. The caller must convert
        expires_in to an int first: Daraja docs are inconsistent about types.
        """
        if not token:
            raise ValueError("token must not be empty.")
        if expires_in <= 0:
            raise ValueError("expires_in must be positive.")
        self._token=token
        self._expires_at= self._clock() + expires_in - EXPIRY_MARGIN_SECONDS

    def invalidate(self) -> None:
        """Forget the token, for example after Daraja rejects it as invalid."""
        self._token=None
        self._expires_at=0.0
