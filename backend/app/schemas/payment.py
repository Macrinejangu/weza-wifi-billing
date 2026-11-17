"""Request and response schemas for the M-Pesa payment endpoints.

These models are the first line of defence: FastAPI validates every incoming
request against them and answers HTTP 422 before any payment code runs.
"""

import re
from pydantic import BaseModel, Field, field_validator

# Accepts 07XXXXXXXX, 01XXXXXXXX, 2547XXXXXXXX, 2541XXXXXXXX and +254... forms.
# The captured group is the 9 digits after the country code or leading zero.
# We check the shape only; Daraja itself rejects numbers that are not on M-Pesa.
# [0-9] rather than \d: in Python, \d also matches digits from other scripts,
# which would let non-ASCII numbers through into the normalised value.
_KENYAN_MOBILE = re.compile(r"(?:\+?254|0)([17][0-9]{8})")


class PaymentRequest(BaseModel):
   """Body of the request that starts an M-Pesa payment for a purchase.

    There is deliberately no amount field. The amount is read from the stored
    purchase on the server, so a client can never choose its own price.
    """

   purchase_id: int =Field(gt=0, description="The purchase this payment is for.")
   phone_number: str=Field(description="The customer's M-Pesa number.")

   @field_validator("phone_number")
   @classmethod
   def normalise_phone_number(cls,value:str)->str:
      """Reject malformed numbers and convert valid ones to 254XXXXXXXXX."""
      cleaned = value.strip().replace(" ","")
      match = _KENYAN_MOBILE.fullmatch(cleaned)
      if match is None:
         raise ValueError("Enter a valid Safaricom mobile number, e.g. 0712345678.")
      return f"254{match.group(1)}"