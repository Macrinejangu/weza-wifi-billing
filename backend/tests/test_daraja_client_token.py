"""Tests for the Daraja client's OAuth token handling.

A scripted fake stands in for Daraja, so no test touches the real network.
The fake's `sleep` is recorded instead of waited on, so tests run instantly.
"""

import base64
import threading
import time

import httpx
import pytest

from app.config import DarajaSettings
from app.integrations.mpesa.client import(
    TOKEN_MAX_ATTEMPTS,
    TOKEN_RETRY_DELAY_SECONDS,
    DarajaClient,
)
from app.integrations.mpesa.errors import(
    DarajaAuthError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)

# Distinctive values so we can assert they never leak into error messages
SETTINGS = DarajaSettings(
    environment="sandbox",
    consumer_key="KEY-123",
    consumer_secret="SECRET-456",
    shortcode="174379",
    passkey="PASSKEY-789",
    callback_url="https://example.test/callback",
)
OK = (200, {"access_token": "tok", "expires_in": "3599"})

class FakeDaraja:
    """Replies with scripted outcomes, one per request, repeating the last.

    An outcome is either an exception to raise or a (status, body) pair, where
    body is a dict (sent as JSON) or bytes (sent as-is). A fresh Response is
    built for every request, so nothing is reused between calls.
    """
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        status, body = outcome
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)

def make_client(handler):
    """Build a client wired to the fake. Returns (client, recorded sleeps)."""
    sleeps: list[float] = []
    client = DarajaClient(
        SETTINGS,
        httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_token_request_sends_basic_auth_and_grant_type():
    fake = FakeDaraja(OK)
    client, _=make_client(fake)

    assert client.get_access_token() == "tok"

    request=fake.requests[0]
    assert request.url.params["grant_type"] == "client_credentials"
    encoded = request.headers["authorization"].removeprefix("Basic ")
    assert base64.b64decode(encoded).decode() == "KEY-123:SECRET-456"

def test_second_call_uses_the_cached_token():
    fake = FakeDaraja(OK)
    client, _=make_client(fake)

    client.get_access_token()
    client.get_access_token()

    assert len(fake.requests) == 1

def test_numeric_expires_in_is_accepted():
    # Daraja's docs disagree on string versus number, so both must work.
    client, _=make_client(FakeDaraja((200, {"access_token": "tok", "expires_in": 3599})))

    assert client.get_access_token() == "tok"

def test_invalidate_forces_a_new_fetch():
    fake = FakeDaraja(OK)
    client, _=make_client(fake)

    client.get_access_token()
    client.invalidate_token()
    client.get_access_token()

    assert len(fake.requests) == 2


def test_transient_server_errors_are_retried_with_growing_pauses():
    fake =  FakeDaraja((500, {}), (503, {}), OK)
    client, sleeps = make_client(fake)

    assert client.get_access_token() == "tok"

    assert len(fake.requests) == 3
    assert sleeps == [TOKEN_RETRY_DELAY_SECONDS*1, TOKEN_RETRY_DELAY_SECONDS*2]

def test_gives_up_after_the_maximum_attempts():
    fake = FakeDaraja((503, {}))
    client, _=make_client(fake)

    with pytest.raises(DarajaUnavailableError) as info:
        client.get_access_token()

    assert len(fake.requests) == TOKEN_MAX_ATTEMPTS
    assert info.value.outcome_unknown is True

def test_timeouts_are_retried_then_reported_as_timeout():
    fake = FakeDaraja(httpx.ReadTimeout("slow"))
    client, _=make_client(fake)

    with pytest.raises(DarajaTimeoutError):
        client.get_access_token()

    assert len(fake.requests) == TOKEN_MAX_ATTEMPTS

def test_connection_failure_is_unavailable_not_timeout():
    fake = FakeDaraja(httpx.ConnectError("down"))
    client, _=make_client(fake)

    with pytest.raises(DarajaUnavailableError) as info:
        client.get_access_token()

    # A timeout is a subclass of "unavailable", so check we got the plain one.
    assert not isinstance(info.value, DarajaTimeoutError)

def test_refused_credentials_are_not_retried_and_leak_nothing():
    fake = FakeDaraja((401, {"errorMessage": "Invalid credentials SECRET-456"}))
    client, sleeps = make_client(fake)

    with pytest.raises(DarajaAuthError) as info:
        client.get_access_token()

    assert len(fake.requests) == 1 # retrying a refusal would fail the same way
    assert sleeps == []
    assert info.value.outcome_unknown is False
    message = str(info.value)
    assert "KEY-123" not in message
    assert "SECRET-456" not in message

@pytest.mark.parametrize(
    "outcome",
    [
        (200, b"<html>not json</html>"),                          # not JSON
        (200, {}),                                                 # empty object
        (200, {"access_token": "", "expires_in": "3599"}),         # empty token
        (200, {"access_token": "tok"}),                            # no expires_in
        (200, {"access_token": "tok", "expires_in": "abc"}),       # not a number
        (200, {"access_token": 123, "expires_in": "3599"}),        # token not a string
        (200, {"access_token": "tok", "expires_in": "0"}),         # zero lifetime
        (200, {"access_token": "tok", "expires_in": "-5"}),        # negative lifetime
    ],
)
def test_malformed_token_responses_are_rejected(outcome):
    client, _ = make_client(FakeDaraja(outcome))

    with pytest.raises(DarajaAuthError):
        client.get_access_token()

def test_concurrent_callers_cause_a_single_fetch():
    calls: list[int] = []

    def slow_daraja(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        time.sleep(0.05) # widen the window in which a race could happen
        return httpx.Response(200, json={"access_token": "tok", "expires_in": "3599"})

    client, _=make_client(slow_daraja)
    results: list[str] = []

    threads = [
        threading.Thread(target=lambda: results.append(client.get_access_token()))
        for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Without the lock each thread would fetch its own token and invalidate the others' tokens.
    assert len(calls) == 1
    assert results == ["tok"] * 5

def test_malformed_body_error_does_not_carry_the_original_exception():
    # The original parse error can contain pieces of Daraja's response body.
    # `raise ... from None` keeps it out of the exception chain, so it is
    # never written to logs by a traceback.
    client, _ = make_client(FakeDaraja((200, b"body-that-must-not-leak")))

    with pytest.raises(DarajaAuthError) as info:
        client.get_access_token()

    assert info.value.__suppress_context__ is True
