"""Errors raised by the M-Pesa payment service (not by the Daraja client).

Daraja client errors live in app/integrations/mpesa/errors.py and describe
what Safaricom or the network did. These describe what our service tells the
route. The service catches the first kind and raises the second.

The service never knows about HTTP: it raises one of these and the route
turns it into a status code and a body. Each error has:
  * a stable machine-readable `code` the portal can switch on, and
  * a FIXED customer-safe `message`.
Callers cannot pass free text, so an internal detail (a Daraja message, a
token, a phone number) can never leak into a response through an error.

None of these subclass ValueError or LookupError on purpose: main.py turns
those two into generic 400 and 404 responses, which would hide the real
reason and break the response format the portal relies on.
"""


class PaymentServiceError(Exception):
    """Base class for every payment service error."""

    code = "payment_error"
    message = "The payment could not be processed."

    def __init__(self, *, payment_id: int | None = None) -> None:
        # Keyword-only, and the message comes from the class, never the caller.
        super().__init__(self.message)
        self.payment_id = payment_id


class PurchaseNotFound(PaymentServiceError):
    """No purchase has this id. Nothing is recorded."""

    code = "purchase_not_found"
    message = "Purchase not found."


class PurchaseNotPayable(PaymentServiceError):
    """The purchase is not awaiting payment (already paid, failed or expired)."""

    code = "purchase_not_payable"
    message = "This purchase cannot be paid for."


class PaymentAlreadyPending(PaymentServiceError):
    """A payment for this purchase is already waiting for the customer.

    This is the double-tap case, caught by the uq_one_pending_payment index.
    The existing payment id is returned so the portal can keep polling it.
    """

    code = "payment_already_pending"
    message = "A payment for this purchase is already in progress."

    def __init__(self, *, payment_id: int) -> None:
        super().__init__(payment_id=payment_id)


class ProviderRejected(PaymentServiceError):
    """Daraja refused the request, so no prompt was sent.

    The payment is recorded as failed, which frees the pending slot.
    """

    code = "provider_rejected"
    message = "The payment request was not accepted. Please try again."


class ProviderNotReached(PaymentServiceError):
    """We could not get a token, so nothing was sent to the customer.

    The payment is recorded as failed. It is safe to try again.
    """

    code = "provider_not_reached"
    message = "Payments are temporarily unavailable. Please try again shortly."


class OutcomeUnknown(PaymentServiceError):
    """The request may or may not have reached the customer's phone.

    The payment STAYS pending and is never retried automatically, because a
    repeat could prompt or charge the customer twice. The message must never
    say the payment failed, because we do not know that.
    """

    code = "outcome_unknown"
    message = (
        "We could not confirm the payment request. "
        "Please check your phone and wait before trying again."
    )

    def __init__(self, *, payment_id: int | None = None, timed_out: bool = False) -> None:
        super().__init__(payment_id=payment_id)
        # Lets the route answer 504 for a timeout and 502 for other failures.
        self.timed_out = timed_out