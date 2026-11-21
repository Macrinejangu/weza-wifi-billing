
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Payment(TimestampMixin, Base):
    """One M-Pesa payment attempt. A purchase can have several."""

    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'successful', 'failed', 'expired')",
            name="ck_payments_status",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payments_amount",
        ),
        CheckConstraint(
            "phone_number ~ '^254[0-9]{9}$'",
            name="ck_payments_phone",
        ),
        Index(
            "ix_payments_status",
            "status",
        ),
        Index(
            "uq_one_successful_payment",
            "purchase_id",
            unique=True,
            postgresql_where=text("status = 'successful'"),
        ),
        Index(
            "uq_one_pending_payment",
            "purchase_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_payments_pending_initiated_at",
            "initiated_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id = Column(Integer, primary_key=True)

    purchase_id = Column(
        Integer,
        ForeignKey("purchases.id"),
        nullable=False,
    )

    amount = Column(Integer, nullable=False)

    phone_number = Column(String(12), nullable=False)

    payment_method = Column(
        String(30),
        nullable=False,
        default="mpesa",
        server_default="mpesa",
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )

    checkout_request_id = Column(
        String(100),
        unique=True,
    )

    merchant_request_id = Column(String(100))

    mpesa_receipt_number = Column(
        String(50),
        unique=True,
    )

    result_code = Column(Integer)
    result_desc = Column(Text)
    failure_reason = Column(String(255))

    raw_callback = Column(JSONB)

    callback_received_at = Column(DateTime(timezone=True))
    initiated_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))

    idempotency_key = Column(
        String(100),
        unique=True,
    )

    purchase = relationship("Purchase")
