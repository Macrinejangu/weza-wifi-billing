
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class SupportTicket(TimestampMixin, Base):
    """A customer support request."""

    __tablename__ = "support_tickets"

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_support_tickets_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_support_tickets_priority",
        ),
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
    )

    priority = Column(
        String(20),
        nullable=False,
        default="medium",
        server_default="medium",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    assigned_staff = relationship(
        "User",
        foreign_keys=[assigned_to],
    )
