"""Helpers for keeping personal data out of logs."""

# How many characters stay visible at each end of a masked value.
_VISIBLE_EDGE = 3
# Shorter values would reveal most of the number, so they are fully hidden.
_MIN_MASKABLE_LENGTH = 9


def mask_phone(value: object) -> str:
    """Return a phone number safe to log, e.g. 254******149.

    Anything that is not a string of at least 9 characters is replaced by a
    fixed "***", which also avoids revealing how short the value was.
    """
    if not isinstance(value, str) or len(value) < _MIN_MASKABLE_LENGTH:
        return "***"
    hidden = "*" * (len(value) - 2 * _VISIBLE_EDGE)
    return f"{value[:_VISIBLE_EDGE]}{hidden}{value[-_VISIBLE_EDGE:]}"