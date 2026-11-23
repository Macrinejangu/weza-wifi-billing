from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class PaymentEvent(Base):
    """Log of every callback or status query, including duplicates."""

    __tablename__ = "payment_events"
    __table_args__ = (
        CheckConstraint("source IN ('callback', 'query')", name="ck_events_source"),
        CheckConstraint(
            "processing_status IN ('received', 'applied', 'duplicate', 'rejected', 'unmatched')",
            name="ck_events_processing_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    checkout_request_id = Column(String(100), index=True)
    source = Column(String(20), nullable=False)
    result_code = Column(Integer)
    payload = Column(JSONB)
    processing_status = Column(String(20), default="received", nullable=False)
    error_message = Column(String(255))
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))
