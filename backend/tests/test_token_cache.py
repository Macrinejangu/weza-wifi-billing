"""Tests for the in-memory Daraja token cache.

A fake clock stands in for time.monotonic, so tests move time forward
instantly and never sleep.
"""

import pytest

from app.integrations.mpesa.token_cache import EXPIRY_MARGIN_SECONDS, TokenCache


class FakeClock:
    """A clock the test controls by hand."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float)-> None:
        self.now += seconds


def test_stored_token_is_returned_while_fresh():
    clock = FakeClock()
    cache = TokenCache(clock=clock)

    cache.store("abc", 3599)
    clock.advance(100)

    assert cache.get() == "abc"


def test_empty_cache_returns_none():
    assert TokenCache(clock=FakeClock()).get() is None

def test_token_expires_at_the_safety_margin():
    clock = FakeClock()
    cache = TokenCache(clock=clock)
    cache.store("abc", 3599)

    # One second before the cutoff (lifetime minus margin): still usable
    clock.advance(3599 - EXPIRY_MARGIN_SECONDS -1)
    assert cache.get() == "abc"

    # Exactly at the cutoff: treated as expired, so a request never starts with a token that is about to die.
    clock.advance(1)
    assert cache.get() is None

def test_invalidate_forgets_the_token():
    cache = TokenCache(clock=FakeClock())
    cache.store("abc", 3599)

    cache.invalidate()

    assert cache.get() is None


def test_store_replaces_the_previous_token():
    cache = TokenCache(clock=FakeClock())
    cache.store("old", 3599)

    cache.store("new", 3599)

    assert cache.get() == "new"


@pytest.mark.parametrize(
    "token, expires_in",
    [
        ("", 3599),    # empty token
        ("abc", 0),    # zero lifetime
        ("abc", -5),   # negative lifetime
    ],
)
def test_store_rejects_bad_input_and_caches_nothing(token, expires_in):
    cache=TokenCache(clock=FakeClock())

    with pytest.raises(ValueError):
        cache.store(token, expires_in)

    # A rejected token must not be half-stored.
    assert cache.get() is None