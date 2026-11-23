"""Turns the raw body of an incoming request into a value safe to store (WEZA-50).

The callback route saves every request body in payment_events.payload (a
PostgreSQL JSONB column) BEFORE it tries to understand it. That audit row must
never be the thing that fails, so this module guarantees that whatever
arrives, even garbage, becomes a small dict that JSONB will accept.

JSONB refuses several inputs a broken or hostile sender can produce:
  * the NUL character,
  * a lone surrogate (half of a Unicode pair, for example from an escape),
  * the non-standard constants NaN and Infinity.
Without this module such a body would make the audit INSERT fail and hide
the very request we wanted to record.
"""
import json
import re
from typing import Any

# A body that parses as a JSON object is stored as it arrived, but only up to
# this size. The route also enforces a body size limit; this is the second,
# storage-side cap.
MAX_JSON_CHARS = 20_000

# Anything else is stored as text, cut to this length.
MAX_RAW_TEXT_CHARS = 8_000

# NUL, or any character in the surrogate range: both are rejected by JSONB.
_UNSTORABLE = re.compile("[\x00\ud800-\udfff]")
_REPLACEMENT = "\ufffd"


def _reject_constant(name: str) -> None:
    """json.loads accepts NaN and Infinity by default; JSONB does not."""
    raise ValueError(f"non-standard JSON constant: {name}")


def _has_unstorable_text(value: Any) -> bool:
    """True if any string, including dictionary keys, JSONB would reject."""
    if isinstance(value, str):
        return _UNSTORABLE.search(value) is not None
    if isinstance(value, dict):
        return any(
            _has_unstorable_text(key) or _has_unstorable_text(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_has_unstorable_text(item) for item in value)
    return False


def build_event_payload(raw_body: bytes) -> dict[str, Any]:
    """Return a JSONB-safe dict for any request body. Never raises.

    A well-formed JSON object under the size cap is returned unchanged.
    Everything else comes back as:
        {"raw_text": <text, cut and cleaned>, "truncated": bool,
         "original_length": <characters before cutting>}
    so staff can still read what was sent.
    """
    # errors="replace" means invalid UTF-8 can never raise here.
    text = raw_body.decode("utf-8", errors="replace")

    if len(text) <= MAX_JSON_CHARS:
        try:
            parsed = json.loads(text, parse_constant=_reject_constant)
            if isinstance(parsed, dict) and not _has_unstorable_text(parsed):
                return parsed
        except (ValueError, RecursionError):
            # Not valid JSON, or nested too deeply to read. Deliberate: the
            # body is stored as plain text below instead of being lost.
            pass

    cleaned = text.replace("\x00", _REPLACEMENT)
    return {
        "raw_text": cleaned[:MAX_RAW_TEXT_CHARS],
        "truncated": len(cleaned) > MAX_RAW_TEXT_CHARS,
        "original_length": len(text),
    }