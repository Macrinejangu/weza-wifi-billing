"""M-Pesa payment initiation.

start_payment() is the database half: ONE short transaction that records a
pending payment. initiate_payment() runs it, calls Daraja OUTSIDE any
transaction (a Daraja call can take many seconds and we must not hold a
database lock while waiting), then records the outcome.

Safety rules enforced here:
  * The amount is copied from the stored purchase, never from the client.
  * The purchase row is locked (SELECT ... FOR UPDATE) so two taps, or a tap
    and a callback, cannot interleave.
  * A second pending payment for the same purchase is rejected by the DATABASE
    (the uq_one_pending_payment index), not by a Python check. We only
    translate that rejection into a clear error.
  * An STK Push is sent at most ONCE per payment and is never retried: a repeat
    could prompt or charge the customer twice.
  * Fail closed on uncertainty. Only when we KNOW nothing reached the phone
    (Daraja refused, or we had no token) is the payment marked failed, which
    frees the pending slot. Anything uncertain leaves it pending.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import NoReturn, Protocol

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.mpesa.client import StkPushAccepted
from app.integrations.mpesa.errors import (
    DarajaAuthError,
    DarajaError,
    DarajaRejectedError,
    DarajaTimeoutError,
)
from app.models import Payment, Purchase, User
from app.payments.masking import mask_phone
from app.payments.payment_service_errors import (
    AccessAlreadyReserved,
    OutcomeUnknown,
    PaymentAlreadyPending,
    ProviderNotReached,
    ProviderRejected,
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


def ensure_no_overlapping_payment(db: Session, purchase: Purchase) -> None:
    # Serialize checkout by account and, when available, the verified device.
    db.execute(select(User.id).where(User.id == purchase.user_id).with_for_update())
    overlapping = Purchase.user_id == purchase.user_id
    if purchase.device_mac_address:
        db.execute(select(func.pg_advisory_xact_lock(
            func.hashtext(f"weza-payment-device:{purchase.device_mac_address}")
        )))
        overlapping = or_(overlapping, Purchase.device_mac_address == purchase.device_mac_address)

    access_ends = Payment.paid_at + func.make_interval(0, 0, 0, 0, 0, Purchase.duration_minutes)
    existing = db.scalar(
        select(Payment.id)
        .join(Purchase, Purchase.id == Payment.purchase_id)
        .where(
            Purchase.id != purchase.id,
            overlapping,
            or_(
                Payment.status.in_((PaymentStatus.PENDING.value, PaymentStatus.EXPIRED.value)),
                (Payment.status == PaymentStatus.SUCCESSFUL.value) & (access_ends > datetime.now(timezone.utc)),
            ),
        )
        .limit(1)
    )
    if existing is not None:
        raise AccessAlreadyReserved()


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

    ensure_no_overlapping_payment(db, purchase)

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


# Daraja limits: AccountReference at most 12 characters, TransactionDesc at
# most 13. Alphanumeric only, because the characters Daraja accepts are not
# yet verified. "WEZA" plus an id fits while the id has at most 8 digits.
ACCOUNT_REFERENCE_PREFIX = "WEZA"
TRANSACTION_DESCRIPTION = "WezaWifi"

# Values written to payments.failure_reason. Our own codes, never Daraja text.
REASON_PROVIDER_REJECTED = ProviderRejected.code
REASON_PROVIDER_NOT_REACHED = ProviderNotReached.code
REASON_REQUEST_INVALID = "request_invalid"


class StkPusher(Protocol):
    """The one thing initiate_payment needs from a Daraja client.

    DarajaClient satisfies this. Tests pass a fake, so no test touches the
    network.
    """

    def stk_push(
        self,
        *,
        amount: int,
        phone_number: str,
        account_reference: str,
        description: str,
    ) -> StkPushAccepted: ...


@dataclass(frozen=True)
class InitiatedPayment:
    """What the route needs after Daraja accepted the push.

    Daraja ACCEPTING the request does not mean the customer paid: the payment
    is still pending until a verified callback or status query settles it.
    """

    payment_id: int
    purchase_id: int
    amount: int
    checkout_request_id: str


def _mark_failed(db: Session, payment_id: int, reason: str) -> None:
    """Move a pending payment to failed. Never raises.

    Only a payment that is STILL pending is changed (a conditional UPDATE), so
    this can never overwrite a result a callback saved in the meantime. If the
    database fails here the payment stays pending, which blocks a retry until
    it is resolved. That is safe, and it is logged.
    """
    try:
        result = db.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PaymentStatus.PENDING.value,
            )
            .values(
                status=PaymentStatus.FAILED.value,
                failure_reason=reason,
                updated_at=datetime.now(timezone.utc),
            )
            .execution_options(synchronize_session=False)
        )
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "could not mark payment failed: payment_id=%s reason=%s error=%s",
            payment_id,
            reason,
            type(error).__name__,
        )
        return
    if result.rowcount != 1:
        logger.warning(
            "payment was no longer pending: payment_id=%s reason=%s",
            payment_id,
            reason,
        )


def _record_accepted(
    db: Session, payment_id: int, accepted: StkPushAccepted
) -> bool:
    """Store Daraja's two ids on the payment. True if exactly one row changed.

    The WHERE clause makes this safe: it only fills in ids for a payment that
    is still pending and has none yet, so it cannot overwrite anything.
    """
    result = db.execute(
        update(Payment)
        .where(
            Payment.id == payment_id,
            Payment.status == PaymentStatus.PENDING.value,
            Payment.checkout_request_id.is_(None),
        )
        .values(
            checkout_request_id=accepted.checkout_request_id,
            merchant_request_id=accepted.merchant_request_id,
            updated_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def _raise_for_daraja_error(
    db: Session, payment_id: int, error: DarajaError
) -> NoReturn:
    """Translate a Daraja client error into one of our typed errors.

    Only an error that PROVES nothing reached the phone marks the payment
    failed. An unrecognised error type is treated as unknown, never failed.
    """
    proven_not_sent = not error.outcome_unknown and isinstance(
        error, (DarajaRejectedError, DarajaAuthError)
    )
    if not proven_not_sent:
        logger.warning(
            "Daraja outcome unknown: payment_id=%s error=%s",
            payment_id,
            type(error).__name__,
        )
        raise OutcomeUnknown(
            payment_id=payment_id,
            timed_out=isinstance(error, DarajaTimeoutError),
        ) from None

    if isinstance(error, DarajaRejectedError):
        logger.info(
            "Daraja refused the push: payment_id=%s http_status=%s "
            "error_code=%s request_id=%s",
            payment_id,
            error.http_status,
            error.error_code,
            error.request_id,
        )
        _mark_failed(db, payment_id, REASON_PROVIDER_REJECTED)
        raise ProviderRejected(payment_id=payment_id) from None

    logger.warning("no Daraja token, nothing sent: payment_id=%s", payment_id)
    _mark_failed(db, payment_id, REASON_PROVIDER_NOT_REACHED)
    raise ProviderNotReached(payment_id=payment_id) from None


def initiate_payment(
    db: Session, daraja: StkPusher, purchase_id: int, phone_number: str
) -> InitiatedPayment:
    """Start a payment: record it, ask Daraja to prompt the customer, record
    what happened. Sends ONE push and never retries it.

    Raises PurchaseNotFound, PurchaseNotPayable, PaymentAlreadyPending (from
    start_payment), then ProviderRejected, ProviderNotReached or OutcomeUnknown
    (see the module docstring). A ValueError from the client means our own
    request was malformed: the payment is marked failed and the error re-raised.
    """
    started = start_payment(db, purchase_id, phone_number)
    reference = f"{ACCOUNT_REFERENCE_PREFIX}{started.payment_id}"

    # No transaction is open here: start_payment() committed. Nothing below
    # touches the database until Daraja has answered.
    try:
        accepted = daraja.stk_push(
            amount=started.amount,
            phone_number=started.phone_number,
            account_reference=reference,
            description=TRANSACTION_DESCRIPTION,
        )
    except DarajaError as error:
        _raise_for_daraja_error(db, started.payment_id, error)
    except ValueError:
        # The client validates before sending, so nothing reached the phone.
        _mark_failed(db, started.payment_id, REASON_REQUEST_INVALID)
        raise

    try:
        stored = _record_accepted(db, started.payment_id, accepted)
    except SQLAlchemyError as error:
        db.rollback()
        # The customer HAS a prompt but we could not save its ids. Log the
        # checkout id (not secret) so staff can reconcile it.
        logger.error(
            "could not store Daraja ids: payment_id=%s checkout_request_id=%s "
            "error=%s",
            started.payment_id,
            accepted.checkout_request_id,
            type(error).__name__,
        )
        raise OutcomeUnknown(payment_id=started.payment_id) from None
    if not stored:
        # The payment stopped being pending (for example it was expired)
        # while Daraja was working. Do not guess: report it and let staff see it.
        logger.error(
            "payment changed during the Daraja call: payment_id=%s "
            "checkout_request_id=%s",
            started.payment_id,
            accepted.checkout_request_id,
        )
        raise OutcomeUnknown(payment_id=started.payment_id)

    logger.info(
        "STK Push accepted: payment_id=%s checkout_request_id=%s",
        started.payment_id,
        accepted.checkout_request_id,
    )
    return InitiatedPayment(
        payment_id=started.payment_id,
        purchase_id=started.purchase_id,
        amount=started.amount,
        checkout_request_id=accepted.checkout_request_id,
    )