"""Tests for DarajaClient.stk_push().

A scripted fake stands in for Daraja, so no test touches the real network. It
records token requests and push requests separately, which lets tests assert
the most important rule: an STK Push is sent ONCE and never retried, because a
repeat could put a second prompt on the customer's phone.
"""

import json
import logging

import httpx
import pytest

from app.config import ACCOUNT_PAYBILL, DarajaSettings
from app.integrations.mpesa.client import STK_PUSH_PATH, TOKEN_PATH, DarajaClient
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaMalformedResponseError,
    DarajaRejectedError,
    DarajaTimeoutError,
    DarajaUnavailableError,
)
from app.payments.daraja_password import build_password

TIMESTAMP = "20261118120000"
PHONE = "254708374149"

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
PUSH_OK = (
    200,
    {
        "ResponseCode": "0",
        "ResponseDescription": "Success. Request accepted for processing",
        "CheckoutRequestID": "ws_CO_1",
        "MerchantRequestID": "m-1",
    },
)

class FakeDaraja:
    """Replies to token and push requests with scripted outcomes.

    An outcome is an exception to raise, or a (status, body) pair where body is
    a dict or list (sent as JSON) or bytes (sent as-is). Token and push
    requests are recorded separately.
    """
    def __init__(self, push_outcome, token_outcome=OK_TOKEN):
        self.push_outcome=push_outcome
        self.token_outcome = token_outcome
        self.token_requests: list[httpx.Request] = []
        self.push_requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == TOKEN_PATH:
            self.token_requests.append(request)
            return self._respond(self.token_outcome)
        self.push_requests.append(request)
        return self._respond(self.push_outcome)

    @staticmethod
    def _respond(outcome) -> httpx.Response:
        if isinstance(outcome, Exception):
            raise outcome
        status, body=outcome
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)


def make_client(push_outcome, token_outcome=OK_TOKEN):
    """Build a client wired to the fake. Pauses are skipped, not waited on."""
    fake = FakeDaraja(push_outcome, token_outcome)
    client = DarajaClient(
        SETTINGS,
        httpx.Client(transport=httpx.MockTransport(fake)),
        sleep=lambda seconds: None,
    )
    return client, fake

def push(client, **overrides):
    """Call stk_push with valid defaults, changing only what a test overrides."""
    values = {
        "amount": 10,
        "phone_number": PHONE,
        "account_reference": "WEZA-1",
        "description": "Wifi",
        "timestamp": TIMESTAMP,
    }
    values.update(overrides)
    return client.stk_push(**values)

def test_accepted_push_returns_the_request_ids():
    client, fake = make_client(PUSH_OK)
    result = push(client)

    assert result.checkout_request_id == "ws_CO_1"
    assert result.merchant_request_id == "m-1"
    assert len(fake.push_requests) == 1

def test_push_request_is_a_post_with_bearer_token_and_correct_body():
    client, fake = make_client(PUSH_OK)
    push(client)

    request = fake.push_requests[0]
    assert request.method == "POST"
    assert request.url.path == STK_PUSH_PATH
    assert request.headers["authorization"] == "Bearer tok"
    body = json.loads(request.content)
    assert body["Amount"] == 10
    assert body["PartyA"] == PHONE
    assert body["PartyB"] == "174379"
    assert body["TransactionType"] == "CustomerPayBillOnline"
    assert body["Timestamp"] == TIMESTAMP
    # The password must match the SAME timestamp that was sent.
    assert body["Password"] == build_password("174379", "PASSKEY-789", TIMESTAMP)

def test_numeric_response_code_zero_is_accepted():
    # Daraja's docs disagree on string versus number.
    outcome = (200, {**PUSH_OK[1], "ResponseCode": 0})
    client, _ = make_client(outcome)

    assert push(client).checkout_request_id == "ws_CO_1"

def test_timestamp_is_generated_when_not_given():
    client, fake = make_client(PUSH_OK)

    client.stk_push(
        amount=10,
        phone_number=PHONE,
        account_reference="WEZA-1",
        description="Wifi",
    )

    stamp = json.loads(fake.push_requests[0].content)["Timestamp"]
    assert len(stamp) == 14
    assert stamp.isdigit()

def test_second_push_reuses_the_cached_token():
    client, fake = make_client(PUSH_OK)

    push(client)
    push(client)

    assert len(fake.token_requests) == 1
    assert len(fake.push_requests) == 2

def test_timeout_is_unknown_outcome_and_is_never_retried():
    client, fake = make_client(httpx.ReadTimeout("slow"))

    with pytest.raises(DarajaTimeoutError) as info:
        push(client)

    # The prompt may already be on the phone: a retry could charge twice.
    assert len(fake.push_requests) == 1
    assert info.value.outcome_unknown is True

def test_connection_failure_is_unknown_outcome_and_is_never_retried():
    client, fake =make_client(httpx.ConnectError("down"))

    with pytest.raises(DarajaUnavailableError) as info:
        push(client)

    assert not isinstance(info.value, DarajaTimeoutError)
    assert len(fake.push_requests) == 1
    assert info.value.outcome_unknown is True

@pytest.mark.parametrize("status", [500,502,503])
def test_server_errors_are_unknown_outcome_and_never_retried(status):
    client, fake = make_client((status, {}))

    with pytest.raises(DarajaUnavailableError) as info:
        push(client)

    assert len(fake.push_requests) == 1
    assert info.value.outcome_unknown is True

def test_client_errors_are_a_clear_refusal_and_leak_nothing():
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
        push(client)

    error = info.value
    assert error.http_status == 400
    assert error.error_code == "400.002.02"
    assert error.request_id == "req-1"
    assert error.outcome_unknown is False
    assert len(fake.push_requests) == 1
    # Daraja's free text can echo request details, so it is never copied.
    assert "PASSKEY-789" not in str(error)

def test_refusal_with_a_non_json_body_still_raises_a_refusal():
    client, _ = make_client((400, b"<html>bad</html>"))

    with pytest.raises(DarajaRejectedError) as info:
        push(client)

    assert info.value.error_code is None

@pytest.mark.parametrize("status", [401,403])
def test_rejected_token_is_dropped_so_the_next_push_fetches_a_new_one(status):
    client, fake = make_client((status, {"errorCode": "404.001.03"}))

    with pytest.raises(DarajaRejectedError):
        push(client)
    with pytest.raises(DarajaRejectedError):
        push(client)

    assert len(fake.token_requests) == 2
    # The push itself is never retried automatically: one per call.
    assert len(fake.push_requests) == 2

def test_other_client_errors_keep_the_cached_token():
    client, fake = make_client((400, {}))

    with pytest.raises(DarajaRejectedError):
        push(client)
    with pytest.raises(DarajaRejectedError):
        push(client)

    assert len(fake.token_requests) == 1

@pytest.mark.parametrize("response_code", ["1", "00", "0.5", 1, ""])
def test_any_response_code_other_than_zero_is_a_refusal(response_code):
    outcome = (200, {**PUSH_OK[1], "ResponseCode": response_code})
    client, _ = make_client(outcome)

    with pytest.raises(DarajaRejectedError) as info:
        push(client)

    assert info.value.outcome_unknown is False

@pytest.mark.parametrize(
    "outcome",
    [
        (200, b"not json"),     # not JSON
        (200, ["unexpected"]),  # JSON, but not an object
        (200, {}),              # no ResponseCode
    ],
)
def test_unusable_200_replies_are_unknown_outcome(outcome):
    client, _= make_client(outcome)

    with pytest.raises(DarajaMalformedResponseError) as info:
        push(client)

    # The prompt may exist, so this must never be treated as a failed payment.
    assert info.value.outcome_unknown is True


@pytest.mark.parametrize(
    "bad_fields",
    [
        {"CheckoutRequestID": None},   # missing
        {"CheckoutRequestID": ""},     # empty
        {"MerchantRequestID": 123},    # not a string
        {"MerchantRequestID": None},   # missing
    ],
)
def test_accepted_reply_without_usable_ids_is_unknown_outcome(bad_fields):
    body = {**PUSH_OK[1], **bad_fields}
    body = {key: value for key, value in body.items() if value is not None}
    client, _= make_client((200, body))

    with pytest.raises(DarajaMalformedResponseError) as info:
        push(client)

    assert info.value.outcome_unknown is True

@pytest.mark.parametrize("token_outcome", [(401, {}), (503, {})])
def test_token_failure_means_no_push_was_sent(token_outcome):
    client, fake = make_client(PUSH_OK, token_outcome)

    with pytest.raises(DarajaAuthError) as info:
        push(client)

    assert fake.push_requests == []
    # Even when the token error was "outcome unknown", nothing was pushed, so
    # it is safe to tell the customer to try again.
    assert info.value.outcome_unknown is False
    assert "no push was sent" in str(info.value)


def test_invalid_input_raises_and_sends_nothing():
    client, fake = make_client(PUSH_OK)

    with pytest.raises(ValueError, match="amount"):
        push(client, amount=0)

    assert fake.push_requests == []

def test_logs_contain_the_checkout_id_but_no_secrets(caplog):
    caplog.set_level(logging.INFO)
    token_outcome = (200, {"access_token": "TOKEN-SECRET-1", "expires_in": "3599"})
    client, _=make_client(PUSH_OK, token_outcome)

    push(client)

    assert "ws_CO_1" in caplog.text
    assert "TOKEN-SECRET-1" not in caplog.text
    assert PHONE not in caplog.text
    assert "PASSKEY-789" not in caplog.text
    assert build_password("174379", "PASSKEY-789", TIMESTAMP) not in caplog.text
