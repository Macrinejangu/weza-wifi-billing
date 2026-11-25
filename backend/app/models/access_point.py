
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class AccessPoint(TimestampMixin, Base):
    """A Wi-Fi access point associated with a router."""

    __tablename__ = "access_points"

    id = Column(Integer, primary_key=True, index=True)

    router_id = Column(
        Integer,
        ForeignKey("routers.id"),
        nullable=True,
        index=True,
    )

    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=True)
    mac_address = Column(String(50), unique=True, nullable=True)
    management_ip = Column(String(45))

    status = Column(
        String(20),
        default="offline",
        nullable=False,
    )

    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    router = relationship("Router", back_populates="access_points")
