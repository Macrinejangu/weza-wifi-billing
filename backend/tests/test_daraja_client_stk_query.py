"""Tests for DarajaClient.stk_query().

A scripted fake stands in for Daraja, so no test touches the real network.
The key rules proved here: one request per call (the caller decides when to
ask again), and EVERY failure to get an answer raises, so an outage can never
be read as "paid" or "failed". Only a clear reply gives PAID or FAILED.
"""
import json
import logging

import httpx
import pytest

from app.config import ACCOUNT_PAYBILL, DarajaSettings
from app.integrations.mpesa.client import STK_QUERY_PATH, TOKEN_PATH, DarajaClient
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaRejectedError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.payments.daraja_password import build_password
from app.payments.result_codes import FailureReason

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

OK_TOKEN = (200, {"access_token": "tok", "expires_in": "3599"})
QUERY_OK = (
    200,
    {
        "ResponseCode": "0",
        "ResponseDescription": "The service request has been accepted successfully",
        "MerchantRequestID": "m-1",
        "CheckoutRequestID": CHECKOUT_ID,
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    },
)

class FakeDarajaQuery:
    """Replies to token and query requests with scripted outcomes.

    An outcome is an exception to raise, or a (status, body) pair where body is
    a dict or list (sent as JSON) or bytes (sent as-is).
    """

    def __init__(self, query_outcome, token_outcome=OK_TOKEN):
        self.query_outcome = query_outcome
        self.token_outcome = token_outcome
        self.token_requests: list[httpx.Request] = []
        self.query_requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            self.token_requests.append(request)
            return self._respond(self.token_outcome)
        self.query_requests.append(request)
        return self._respond(self.query_outcome)

    @staticmethod
    def _respond(outcome) -> httpx.Response:
        if isinstance(outcome, Exception):
            raise outcome
        status, body = outcome
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)


def make_client(query_outcome, token_outcome=OK_TOKEN):
    """Build a client wired to the fake. Pauses are skipped, not waited on."""
    fake = FakeDarajaQuery(query_outcome, token_outcome)
    client = DarajaClient(
        SETTINGS,
        httpx.Client(transport=httpx.MockTransport(fake)),
        sleep=lambda seconds: None,
    )
    return client, fake

def query(client, checkout_id=CHECKOUT_ID):
    """Call stk_query with a fixed timestamp so tests can predict the body."""
    return client.stk_query(checkout_id, timestamp=TIMESTAMP)

def with_body(**overrides):
    """A copy of the OK reply with some fields changed."""
    return (200, {**QUERY_OK[1], **overrides})

def test_paid_reply_returns_paid_after_one_request():
    client, fake = make_client(QUERY_OK)

    result = query(client)

    assert result.outcome is StkQueryOutcome.PAID
    assert len(fake.query_requests) == 1


def test_query_is_a_post_with_bearer_token_and_correct_body():
    client, fake = make_client(QUERY_OK)
    query(client)

    request = fake.query_requests[0]
    assert request.method == "POST"
    assert request.url.path == STK_QUERY_PATH
    assert request.headers["authorization"] == "Bearer tok"
    body = json.loads(request.content)
    assert body["BusinessShortCode"] == "174379"
    assert body["CheckoutRequestID"] == CHECKOUT_ID
    assert body["Timestamp"] == TIMESTAMP
    # The password must match the SAME timestamp that was sent.
    assert body["Password"] == build_password("174379", "PASSKEY-789", TIMESTAMP)


def test_non_zero_result_code_returns_failed_with_a_reason():
    client, _ = make_client(with_body(ResultCode="1032"))

    result = query(client)

    assert result.outcome is StkQueryOutcome.FAILED
    assert result.failure_reason is FailureReason.CANCELLED

def test_reply_about_another_payment_is_unknown_not_paid():
    # Proves the client hands OUR ID to the interpreter: the body says
    # ResultCode 0, but for someone else's payment.
    client, _ = make_client(with_body(CheckoutRequestID="ws_CO_OTHER"))

    assert query(client).outcome is StkQueryOutcome.UNKNOWN

@pytest.mark.parametrize(
    "outcome",
    [
        (200, b"not json"),
        (200, ["unexpected"]),
        (200, {}),
    ],
)
def test_unusable_200_replies_are_unknown(outcome):
    client, _ = make_client(outcome)

    assert query(client).outcome is StkQueryOutcome.UNKNOWN

def test_timestamp_is_generated_when_not_given():
    client, fake = make_client(QUERY_OK)

    client.stk_query(CHECKOUT_ID)

    stamp = json.loads(fake.query_requests[0].content)["Timestamp"]
    assert len(stamp) == 14
    assert stamp.isdigit()


def test_second_query_reuses_the_cached_token():
    client, fake = make_client(QUERY_OK)

    query(client)
    query(client)

    assert len(fake.token_requests) == 1
    assert len(fake.query_requests) == 2

def test_timeout_raises_and_is_not_retried():
    client, fake = make_client(httpx.ReadTimeout("slow"))

    with pytest.raises(DarajaTimeoutError):
        query(client)

    assert len(fake.query_requests) == 1

def test_connection_failure_raises_and_is_not_retried():
    client, fake = make_client(httpx.ConnectError("down"))

    with pytest.raises(DarajaUnavailableError) as info:
        query(client)

    assert not isinstance(info.value, DarajaTimeoutError)
    assert len(fake.query_requests) == 1

@pytest.mark.parametrize(
    "outcome",
    [
        (500, {}),
        (502, {}),
        (503, {}),
        # Wording of Daraja's "still being processed" reply is UNVERIFIED;
        # the rule is that ANY 5xx is "no answer", whatever the body says.
        (500, {"errorCode": "500.001.1001", "errorMessage": "being processed"}),
    ],
)
def test_server_errors_raise_and_are_not_retried(outcome):
    client, fake = make_client(outcome)

    with pytest.raises(DarajaUnavailableError) as info:
        query(client)

    assert len(fake.query_requests) == 1
    assert info.value.outcome_unknown is True

def test_client_errors_are_a_refusal_and_leak_nothing():
    outcome = (
        400,
        {
            "requestId": "req-1",
            "errorCode": "400.002.02",
            "errorMessage": "Invalid PASSKEY-789 value",
        },
    )
    client, fake = make_client(outcome)

    with pytest.raises(DarajaRejectedError) as info:
        query(client)

    error = info.value
    assert error.http_status == 400
    assert error.error_code == "400.002.02"
    assert error.request_id == "req-1"
    assert len(fake.query_requests) == 1
    # Daraja's free text can echo request details, so it is never copied.
    assert "PASSKEY-789" not in str(error)

def test_refusal_with_a_non_json_body_still_raises_a_refusal():
    client, _ = make_client((400, b"<html>bad</html>"))

    with pytest.raises(DarajaRejectedError) as info:
        query(client)

    assert info.value.error_code is None

@pytest.mark.parametrize("status", [401, 403])
def test_rejected_token_is_dropped_so_the_next_query_fetches_a_new_one(status):
    client, fake = make_client((status, {"errorCode": "404.001.03"}))

    with pytest.raises(DarajaRejectedError):
        query(client)
    with pytest.raises(DarajaRejectedError):
        query(client)

    assert len(fake.token_requests) == 2
    # The query itself is never retried automatically: one per call.
    assert len(fake.query_requests) == 2

def test_other_client_errors_keep_the_cached_token():
    client, fake = make_client((400, {}))

    with pytest.raises(DarajaRejectedError):
        query(client)
    with pytest.raises(DarajaRejectedError):
        query(client)

    assert len(fake.token_requests) == 1

@pytest.mark.parametrize("token_outcome", [(401, {}), (503, {})])
def test_token_failure_means_no_query_was_sent(token_outcome):
    client, fake = make_client(QUERY_OK, token_outcome)

    with pytest.raises(DarajaAuthError) as info:
        query(client)

    assert fake.query_requests == []
    assert "no query was sent" in str(info.value)

@pytest.mark.parametrize("bad_id", ["", None, 5])
def test_invalid_checkout_id_raises_before_any_request(bad_id):
    client, fake = make_client(QUERY_OK)

    with pytest.raises(ValueError):
        query(client, checkout_id=bad_id)

    # Our own bug must not cost a token request or reach Daraja.
    assert fake.token_requests == []
    assert fake.query_requests == []

def test_logs_contain_the_checkout_id_and_outcome_but_no_secrets(caplog):
    caplog.set_level(logging.INFO)
    token_outcome = (200, {"access_token": "TOKEN-SECRET-1", "expires_in": "3599"})
    client, _ = make_client(QUERY_OK, token_outcome)

    query(client)

    assert CHECKOUT_ID in caplog.text
    assert "paid" in caplog.text
    assert "TOKEN-SECRET-1" not in caplog.text
    assert PHONE not in caplog.text
    assert "PASSKEY-789" not in caplog.text
    assert build_password("174379", "PASSKEY-789", TIMESTAMP) not in caplog.text