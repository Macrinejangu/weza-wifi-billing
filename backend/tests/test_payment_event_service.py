"""Tests for the payment event audit trail: sanitising and committing."""
import pytest

from app.models import PaymentEvent
from app.services.payment_event_service import (
    EventOutcome,
    EventSource,
    record_received_event,
    safe_checkout_request_id,
    safe_result_code,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ws_CO_123", "ws_CO_123"),
        ("x" * 100, "x" * 100),  # exactly at the limit is allowed
        ("x" * 101, None),  # one over the column size
        (None, None),
        (123, None),
        ("", None),
        ("   ", None),
        ("a\x00b", None),  # NUL is rejected by PostgreSQL
        ("a\ud800b", None),  # lone surrogate
    ],
)
def test_safe_checkout_request_id(value, expected):
    assert safe_checkout_request_id(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (1032, 1032),
        (-1, -1),
        (2**31 - 1, 2**31 - 1),  # largest value the column holds
        (2**31, None),  # one over: would break the INSERT
        (-(2**31) - 1, None),
        (True, None),  # a bool must not be recorded as the number 1
        ("0", None),  # strings are not converted here
        (1.5, None),
        (None, None),
    ],
)
def test_safe_result_code(value, expected):
    assert safe_result_code(value) == expected


def test_records_a_received_row_with_the_given_values(db):
    payload = {"Body": {"stkCallback": {"ResultCode": 0}}}

    event_id = record_received_event(
        db,
        source=EventSource.CALLBACK,
        payload=payload,
        checkout_request_id="ws_CO_1",
        result_code=0,
    )

    db.expire_all()
    row = db.get(PaymentEvent, event_id)
    assert row.source == "callback"
    assert row.processing_status == EventOutcome.RECEIVED.value
    assert row.checkout_request_id == "ws_CO_1"
    assert row.result_code == 0
    assert row.payload == payload
    assert row.payment_id is None  # matching a payment happens in a later step


def test_hostile_values_are_stored_as_null_but_the_body_is_kept(db):
    payload = {"raw_text": "x" * 50, "truncated": False, "original_length": 50}

    event_id = record_received_event(
        db,
        source=EventSource.CALLBACK,
        payload=payload,
        checkout_request_id="x" * 500,
        result_code=2**40,
    )

    db.expire_all()
    row = db.get(PaymentEvent, event_id)
    assert row.checkout_request_id is None
    assert row.result_code is None
    assert row.payload == payload  # the evidence is still there


def test_the_row_is_committed_so_it_survives_a_rollback(db):
    event_id = record_received_event(
        db, source=EventSource.CALLBACK, payload={"a": 1}
    )

    db.rollback()  # simulates a later step failing and rolling back

    assert db.get(PaymentEvent, event_id) is not None


def test_a_status_query_event_uses_the_query_source(db):
    event_id = record_received_event(
        db, source=EventSource.QUERY, payload={"a": 1}
    )

    db.expire_all()
    assert db.get(PaymentEvent, event_id).source == "query"