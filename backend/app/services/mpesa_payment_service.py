"""M-Pesa payment initiation: the database half.

start_payment() runs ONE short transaction that records a pending payment for
a purchase. It never calls Daraja: the caller does that afterwards, outside
any transaction, because a Daraja call can take many seconds and we must not
hold a database lock while waiting for it.

Safety rules enforced here:
  * The amount is copied from the stored purchase, never from the client.
  * The purchase row is locked (SELECT ... FOR UPDATE) so two taps, or a tap
    and a callback, cannot interleave.
  * A second pending payment for the same purchase is rejected by the DATABASE
    (the uq_one_pending_payment index), not by a Python check. We only
    translate that rejection into a clear error.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, Purchase
from app.payments.masking import mask_phone
from app.payments.payment_service_errors import (
    PaymentAlreadyPending,
    PurchaseNotFound,
    PurchaseNotPayable,
)
from app.payments.statuses import PaymentStatus

logger = logging.getLogger(__name__)

# The purchase status that means "awaiting payment" (see models/purchase.py).
PURCHASE_PENDING = "pending"

# The shape PaymentRequest normalises to. Checked again here because this
# function must stay safe even if it is called from somewhere else.
_NORMALISED_PHONE = re.compile(r"254[17][0-9]{8}")


@dataclass(frozen=True)
class StartedPayment:
    """What the caller needs after the pending payment is saved.

    Plain values, not a database object: after commit() SQLAlchemy expires
    loaded objects, and reading one later would trigger another query.
    """

    payment_id: int
    purchase_id: int
    amount: int  # whole shillings, copied from the purchase
    # repr=False keeps the phone number out of logs and tracebacks.
    phone_number: str = field(repr=False)


def start_payment(db: Session, purchase_id: int, phone_number: str) -> StartedPayment:
    """Record a pending payment for a purchase, or raise a typed error.

    Raises ValueError for malformed arguments (our own bug, nothing touched),
    PurchaseNotFound, PurchaseNotPayable, or PaymentAlreadyPending.
    """
    if isinstance(purchase_id, bool) or not isinstance(purchase_id, int) or purchase_id < 1:
        raise ValueError("purchase_id must be a positive integer")
    if not isinstance(phone_number, str) or _NORMALISED_PHONE.fullmatch(phone_number) is None:
        raise ValueError("phone_number must be normalised to 254XXXXXXXXX")

    # Lock the purchase row until we commit or roll back. populate_existing
    # makes the read reflect the database even if this session already holds
    # an older copy of the row.
    purchase = db.execute(
        select(Purchase)
        .where(Purchase.id == purchase_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()

    if purchase is None:
        db.rollback()  # releases the lock
        raise PurchaseNotFound()
    if purchase.status != PURCHASE_PENDING:
        db.rollback()
        raise PurchaseNotPayable()

    # Read what we need now: commit() expires the object.
    amount = purchase.amount

    payment = Payment(
        purchase_id=purchase_id,
        amount=amount,
        phone_number=phone_number,
        status=PaymentStatus.PENDING.value,
        initiated_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    try:
        db.flush()  # sends the INSERT, so the database can reject it now
    except IntegrityError:
        db.rollback()  # required after a failed flush; also releases the lock
        existing_id = db.scalar(
            select(Payment.id).where(
                Payment.purchase_id == purchase_id,
                Payment.status == PaymentStatus.PENDING.value,
            )
        )
        if existing_id is None:
            # Not the double-tap case, or that payment was settled in the
            # meantime. We do not guess: let it surface as a server error.
            raise
        logger.info(
            "payment already pending: payment_id=%s purchase_id=%s",
            existing_id,
            purchase_id,
        )
        raise PaymentAlreadyPending(payment_id=existing_id) from None

    payment_id = payment.id
    db.commit()
    logger.info(
        "payment initiated: payment_id=%s purchase_id=%s phone=%s",
        payment_id,
        purchase_id,
        mask_phone(phone_number),
    )
    return StartedPayment(
        payment_id=payment_id,
        purchase_id=purchase_id,
        amount=amount,
        phone_number=phone_number,
    )