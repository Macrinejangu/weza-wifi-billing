"""Tests for how DarajaClient reacts when Daraja rejects its access token.

Daraja invalidates the previous token every time a new one is issued, and it can
reject a token we still believe is valid. The client must then DISCARD the
cached token, or every later request would fail until it expired.

What these tests prove, for both stk_push and stk_query:
  * An invalid-token reply (HTTP 401, 403, or errorCode 404.001.03 on any HTTP
    status) discards the token, and the very next call fetches a fresh one.
  * The rejected request is NEVER retried: for an STK Push a repeat could prompt
    the customer twice.
  * Other errors, odd error bodies and successful replies keep the token. If
    the token were dropped on every error, we would hammer Daraja's token
    endpoint and invalidate tokens that are still good.
  * Neither the token, the credentials, nor Daraja's error text reach the logs
    or the exception message.

A scripted fake stands in for Daraja, so no test touches the real network. Each
token it issues is numbered (tok-1, tok-2, ...), which lets a test prove WHICH
token a request used.
"""
import logging

import httpx
import pytest

from app.config import ACCOUNT_PAYBILL, DarajaSettings
from app.integrations.mpesa.client import TOKEN_PATH, DarajaClient
from app.integrations.mpesa.errors import (
    DarajaRejectedError,
    DarajaUnavailableError,
)

TIMESTAMP = "20261118120000"
PHONE = "254708374149"
CHECKOUT_ID = "ws_CO_1"

# Distinctive values so we can assert they never leak into logs or errors.
SETTINGS = DarajaSettings(
    environment="sandbox",
    consumer_key="KEY-123",
    consumer_secret="SECRET-456",
    shortcode="174379",
    passkey="PASSKEY-789",
    callback_url="https://example.test/callback",
    account_type=ACCOUNT_PAYBILL,
    party_b="174379",
)

# The error body Daraja documents for an invalid access token.
INVALID_TOKEN_BODY = {
    "requestId": "req-1",
    "errorCode": "404.001.03",
    "errorMessage": "Invalid Access Token",
}

PUSH_OK = (
    200,
    {
        "ResponseCode": "0",
        "ResponseDescription": "Success. Request accepted for processing",
        "MerchantRequestID": "m-1",
        "CheckoutRequestID": CHECKOUT_ID,
        "CustomerMessage": "Success. Request accepted for processing",
    },
)
QUERY_OK = (
    200,
    {
        "ResponseCode": "0",
        "MerchantRequestID": "m-1",
        "CheckoutRequestID": CHECKOUT_ID,
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    },
)


class FakeDaraja:
    """Issues numbered tokens and replies to API calls with scripted outcomes.

    `api_outcomes` is a list of (status, body) pairs, used in order, one per
    push or query request. body is a dict (sent as JSON) or bytes (sent as-is).
    Running out of scripted replies raises IndexError, so a test that triggers
    an unexpected extra request fails loudly instead of passing by accident.
    """

    def __init__(self, api_outcomes):
        self.api_outcomes = list(api_outcomes)
        self.token_requests: list[httpx.Request] = []
        self.api_requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            self.token_requests.append(request)
            number = len(self.token_requests)
            return httpx.Response(
                200, json={"access_token": f"tok-{number}", "expires_in": "3599"}
            )
        self.api_requests.append(request)
        status, body = self.api_outcomes.pop(0)
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)


def make_client(api_outcomes):
    """Build a client wired to the fake. Pauses are skipped, not waited on."""
    fake = FakeDaraja(api_outcomes)
    client = DarajaClient(
        SETTINGS,
        httpx.Client(transport=httpx.MockTransport(fake)),
        sleep=lambda seconds: None,
    )
    return client, fake


def push(client):
    return client.stk_push(
        amount=10,
        phone_number=PHONE,
        account_reference="WEZA1",
        description="WiFi",
        timestamp=TIMESTAMP,
    )


def query(client):
    return client.stk_query(CHECKOUT_ID, timestamp=TIMESTAMP)


# Each operation paired with a reply that succeeds.
OPERATIONS = [
    pytest.param(push, PUSH_OK, id="push"),
    pytest.param(query, QUERY_OK, id="query"),
]

# Replies that mean "your token is no longer valid", with the error we expect.
# The errorCode is honoured whatever the HTTP status, because the status that
# accompanies 404.001.03 is not confirmed to be 401 or 403.
DROPS_TOKEN = [
    pytest.param((401, {}), DarajaRejectedError, id="http-401"),
    pytest.param((403, {}), DarajaRejectedError, id="http-403"),
    pytest.param((404, INVALID_TOKEN_BODY), DarajaRejectedError, id="code-on-404"),
    pytest.param((400, INVALID_TOKEN_BODY), DarajaRejectedError, id="code-on-400"),
    pytest.param((500, INVALID_TOKEN_BODY), DarajaUnavailableError, id="code-on-500"),
]

# Replies that are errors but NOT an invalid token: the token must be kept.
KEEPS_TOKEN = [
    pytest.param(
        (404, {"requestId": "r", "errorCode": "404.002.01", "errorMessage": "x"}),
        DarajaRejectedError,
        id="other-code-on-404",
    ),
    pytest.param(
        (400, {"requestId": "r", "errorCode": "400.002.02", "errorMessage": "x"}),
        DarajaRejectedError,
        id="other-code-on-400",
    ),
    pytest.param((404, b"<html>gone</html>"), DarajaRejectedError, id="html-body"),
    # errorCode must be a string to match. A number or a list never counts.
    pytest.param((404, {"errorCode": 404001}), DarajaRejectedError, id="numeric-code"),
    pytest.param(
        (404, {"errorCode": ["404.001.03"]}), DarajaRejectedError, id="list-code"
    ),
    pytest.param((500, {}), DarajaUnavailableError, id="http-500-no-code"),
    pytest.param((502, b"bad gateway"), DarajaUnavailableError, id="http-502-html"),
]


@pytest.mark.parametrize(("call", "ok_reply"), OPERATIONS)
@pytest.mark.parametrize(("reply", "expected_error"), DROPS_TOKEN)
def test_rejected_token_is_discarded_and_the_request_is_not_retried(
    call, ok_reply, reply, expected_error
):
    client, fake = make_client([reply, ok_reply])

    with pytest.raises(expected_error):
        call(client)

    # One token fetched, one API request sent: the rejected request was NOT
    # retried behind our back.
    assert len(fake.token_requests) == 1
    assert len(fake.api_requests) == 1

    call(client)  # the caller's next request must succeed

    # A second token was fetched, and the second request used it.
    assert len(fake.token_requests) == 2
    assert fake.api_requests[0].headers["authorization"] == "Bearer tok-1"
    assert fake.api_requests[1].headers["authorization"] == "Bearer tok-2"


@pytest.mark.parametrize(("call", "ok_reply"), OPERATIONS)
@pytest.mark.parametrize(("reply", "expected_error"), KEEPS_TOKEN)
def test_other_errors_keep_the_cached_token(call, ok_reply, reply, expected_error):
    client, fake = make_client([reply, ok_reply])

    with pytest.raises(expected_error):
        call(client)
    call(client)

    # Still ONE token: it was reused, not refetched.
    assert len(fake.token_requests) == 1
    assert fake.api_requests[0].headers["authorization"] == "Bearer tok-1"
    assert fake.api_requests[1].headers["authorization"] == "Bearer tok-1"


@pytest.mark.parametrize(("call", "ok_reply"), OPERATIONS)
def test_successful_calls_share_one_token(call, ok_reply):
    client, fake = make_client([ok_reply, ok_reply])

    call(client)
    call(client)

    assert len(fake.token_requests) == 1


@pytest.mark.parametrize("call", [push, query], ids=["push", "query"])
def test_discarding_a_token_never_logs_or_leaks_secrets(call, caplog):
    client, _ = make_client([(404, INVALID_TOKEN_BODY)])

    with caplog.at_level(logging.WARNING):
        with pytest.raises(DarajaRejectedError) as excinfo:
            call(client)

    # The discard is logged, so staff can see it happened...
    assert "discarding" in caplog.text
    # ...but nothing secret, and none of Daraja's own error text, is written.
    for forbidden in (
        "tok-1",
        "KEY-123",
        "SECRET-456",
        "PASSKEY-789",
        "Invalid Access Token",
    ):
        assert forbidden not in caplog.text
        assert forbidden not in str(excinfo.value)
        