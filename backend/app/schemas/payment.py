"""Request and response schemas for the M-Pesa payment endpoints.

These models are the first line of defence: FastAPI validates every incoming
request against them and answers HTTP 422 before any payment code runs.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Accepts 07XXXXXXXX, 01XXXXXXXX, 2547XXXXXXXX, 2541XXXXXXXX and +254... forms.
# The captured group is the 9 digits after the country code or leading zero.
# We check the shape only; Daraja itself rejects numbers that are not on M-Pesa.
# [0-9] rather than \d: in Python, \d also matches digits from other scripts,
# which would let non-ASCII numbers through into the normalised value.
_KENYAN_MOBILE = re.compile(r"(?:\+?254|0)([17][0-9]{8})")



def normalise_kenyan_mobile(value: str) -> str:
    match = _KENYAN_MOBILE.fullmatch(value.strip().replace(" ", ""))
    if match is None:
        raise ValueError("Enter a valid Kenyan mobile number, e.g. 0712345678.")
    return f"254{match.group(1)}"


class PaymentRequest(BaseModel):
    """Body of the request that starts an M-Pesa payment for a purchase.

    There is deliberately no amount field. The amount is read from the stored
    purchase on the server, so a client can never choose its own price.
    """

    purchase_id: int = Field(gt=0, description="The purchase this payment is for.")
    phone_number: str = Field(description="The customer's M-Pesa number.")

    @field_validator("phone_number")
    @classmethod
    def normalise_phone_number(cls, value: str) -> str:
        """Reject malformed numbers and convert valid ones to 254XXXXXXXXX."""
        try:
            return normalise_kenyan_mobile(value)
        except ValueError:
            raise ValueError("Enter a valid Safaricom mobile number, e.g. 0712345678.") from None

class PaymentInitiated(BaseModel):
    """Response when Daraja accepted the push and the customer was prompted.

    "pending" is the only possible status here: Daraja ACCEPTING the request
    does not mean the customer paid. The portal polls the payment until a
    verified callback or status query settles it. There is deliberately no
    phone number in this response.
    """

    payment_id: int
    purchase_id: int
    amount: int  # whole shillings, from our own database
    status: Literal["pending"]
    message: str
