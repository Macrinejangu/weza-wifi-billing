"""Tests for the payment request schema.

These cover the rules that protect the payment endpoint: only well-formed
purchase IDs and Kenyan mobile numbers get through, and every accepted
number is converted to the 254XXXXXXXXX form that Daraja expects.
"""
import pytest
from pydantic import ValidationError

from app.schemas.payment import PaymentRequest


@pytest.mark.parametrize(
   "raw_number",
   [
      "0712345678",     # local format
      "0712 345 678",   # spaces typed by the customer
      "254712345678",   # international without plus
      "+254712345678",  # international with plus
   ],
)

def test_valid_numbers_are_normalised(raw_number):
    request = PaymentRequest(purchase_id=1, phone_number=raw_number)

    # Whatever the customer typed, downstream code sees one canonical form.
    assert request.phone_number == "254712345678"


def test_01_prefixed_numbers_are_accepted():
    request = PaymentRequest(purchase_id=1, phone_number="0112345678")

    assert request.phone_number == "254112345678"
    

@pytest.mark.parametrize(
   "bad_number",
   [
      "12345",             # too short
      "0212345678",        # 02 is not a mobile prefix
      "07123456789",       # one digit too many
      "0712345678abc",     # trailing characters must not slip through
      "",                  # empty
      "07\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668",  # non-ASCII digits
   ],
)

def test_invalid_numbers_are_rejected(bad_number):
   with pytest.raises(ValidationError):
      PaymentRequest(purchase_id=1, phone_number=bad_number)


@pytest.mark.parametrize("bad_id", [0,-1,"abc"])
def test_invalid_purchase_ids_are_rejected(bad_id):
   with pytest.raises(ValidationError):
      PaymentRequest(purchase_id=bad_id, phone_number="0712345678")