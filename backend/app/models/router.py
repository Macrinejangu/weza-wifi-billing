
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Router(TimestampMixin, Base):
    """A MikroTik router registered in the Weza system."""

    __tablename__ = "routers"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), nullable=False)

    host = Column(String(255), nullable=False, unique=True)

    identity = Column(String(100), nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="offline",
        server_default="offline",
    )

    access_points = relationship("AccessPoint", back_populates="router")

    sessions = relationship("WiFiSession", back_populates="router")
