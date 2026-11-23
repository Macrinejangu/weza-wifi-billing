"""Tests for build_event_payload: any body must become something JSONB accepts."""
import json
import re
from typing import Any

import pytest

from app.payments.event_payload import (
    MAX_JSON_CHARS,
    MAX_RAW_TEXT_CHARS,
    build_event_payload,
)

WRAPPED_KEYS = {"raw_text", "truncated", "original_length"}
_BAD = re.compile("[\x00\ud800-\udfff]")


def is_storable(value: Any) -> bool:
    """Independent check, written separately from the code under test.

    The tests must not trust the module's own helper to judge itself.
    """
    if isinstance(value, str):
        return _BAD.search(value) is None
    if isinstance(value, dict):
        return all(is_storable(k) and is_storable(v) for k, v in value.items())
    if isinstance(value, list):
        return all(is_storable(item) for item in value)
    return True


def test_valid_json_object_is_stored_as_it_arrived():
    body = {"Body": {"stkCallback": {"ResultCode": 0, "CheckoutRequestID": "ws_1"}}}

    assert build_event_payload(json.dumps(body).encode()) == body


@pytest.mark.parametrize(
    "raw",
    [
        b"not json at all",
        b"",
        b"[1, 2, 3]",
        b"42",
        b'"just text"',
        b"null",
        b"{broken",
    ],
)
def test_anything_that_is_not_a_json_object_is_wrapped_as_text(raw):
    result = build_event_payload(raw)

    assert set(result) == WRAPPED_KEYS
    assert result["raw_text"] == raw.decode("utf-8", errors="replace")
    assert result["truncated"] is False
    assert result["original_length"] == len(raw)
    assert is_storable(result)


def test_invalid_utf8_does_not_crash():
    result = build_event_payload(b"\xff\xfe junk")

    assert set(result) == WRAPPED_KEYS
    assert result["raw_text"].endswith(" junk")
    assert is_storable(result)


def test_a_nul_byte_is_replaced_in_the_stored_text():
    result = build_event_payload(b"ab\x00cd")

    assert result["raw_text"] == "ab\ufffdcd"
    assert is_storable(result)


@pytest.mark.parametrize(
    "raw",
    [b'{"Amount": NaN}', b'{"Amount": Infinity}', b'{"Amount": -Infinity}'],
)
def test_nan_and_infinity_are_not_stored_as_numbers(raw):
    result = build_event_payload(raw)

    assert "raw_text" in result  # wrapped, not kept as a parsed dict
    assert is_storable(result)


def test_a_json_escaped_nul_is_wrapped():
    raw = json.dumps({"a": "x\x00y"}).encode()  # contains the six characters \u0000

    result = build_event_payload(raw)

    assert "raw_text" in result
    assert is_storable(result)


def test_a_lone_surrogate_escape_is_wrapped():
    raw = b'{"a": "\\ud800"}'  # valid JSON text, but not storable in JSONB

    result = build_event_payload(raw)

    assert "raw_text" in result
    assert is_storable(result)


def test_an_oversized_body_is_cut_and_marked_truncated():
    raw = json.dumps({"a": "x" * (MAX_JSON_CHARS + 10)}).encode()

    result = build_event_payload(raw)

    assert set(result) == WRAPPED_KEYS
    assert result["truncated"] is True
    assert len(result["raw_text"]) == MAX_RAW_TEXT_CHARS
    assert result["original_length"] == len(raw)


def test_absurdly_deep_nesting_does_not_crash():
    raw = b"[" * 9_000 + b"]" * 9_000  # under the size cap, but too deep to parse

    result = build_event_payload(raw)

    assert "raw_text" in result
    assert is_storable(result)