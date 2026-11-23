from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class ActivationAttempt(Base):
    """One try at switching a session on at the router."""

    __tablename__ = "activation_attempts"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number", name="uq_attempt_number"),
        CheckConstraint("status IN ('started', 'succeeded', 'failed')", name="ck_attempts_status"),
    )

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), default="started", nullable=False)
    error_code = Column(String(50))
    error_message = Column(String(255))
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
