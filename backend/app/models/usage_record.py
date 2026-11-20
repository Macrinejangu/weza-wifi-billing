
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class UsageRecord(TimestampMixin, Base):
    """Network usage recorded for a Wi-Fi session."""

    __tablename__ = "usage_records"

    __table_args__ = (
        CheckConstraint(
            "upload_bytes >= 0",
            name="ck_usage_records_upload_bytes",
        ),
        CheckConstraint(
            "download_bytes >= 0",
            name="ck_usage_records_download_bytes",
        ),
    )

    id = Column(Integer, primary_key=True)

    session_id = Column(
        Integer,
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )

    upload_bytes = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    download_bytes = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    session = relationship("WiFiSession")
