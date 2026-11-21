"""Tests for log-masking helpers."""
import pytest

from app.payments.masking import mask_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("254708374149", "254******149"),
        ("0712345678", "071****678"),
        ("+254712345678", "+25*******678"),
        ("123456789", "123***789"),  # the shortest length we mask
    ],
)
def test_long_numbers_keep_only_their_edges(raw, expected):
    result = mask_phone(raw)

    assert result == expected
    assert raw not in result


@pytest.mark.parametrize(
    "raw",
    [None, 5, "", "12345", "12345678", b"254708374149"],
)
def test_anything_short_or_not_text_is_fully_hidden(raw):
    assert mask_phone(raw) == "***"