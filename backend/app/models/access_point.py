from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class AccessPoint(Base):
    __tablename__ = "access_points"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=True)
    mac_address = Column(String(50), unique=True, nullable=True)
    status = Column(String(20), default="offline", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    