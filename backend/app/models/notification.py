
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Notification(TimestampMixin, Base):
    """A notification associated with a user."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title = Column(String(150), nullable=False)

    message = Column(Text, nullable=False)

    notification_type = Column(
        String(50),
        nullable=False,
    )

    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    read_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship("User")
