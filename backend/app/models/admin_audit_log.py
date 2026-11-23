
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class AdminAuditLog(TimestampMixin, Base):
    """Audit record for administrative actions."""

    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True)

    admin_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    action = Column(
        String(100),
        nullable=False,
    )

    entity_type = Column(
        String(100),
        nullable=False,
    )

    entity_id = Column(
        Integer,
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    old_values = Column(
        JSONB,
        nullable=True,
    )

    new_values = Column(
        JSONB,
        nullable=True,
    )

    admin = relationship("User")
