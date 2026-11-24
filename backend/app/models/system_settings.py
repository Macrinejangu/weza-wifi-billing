from sqlalchemy import CheckConstraint, Column, Integer, String, Time

from app.db.base import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_system_settings_singleton"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(60), nullable=False)
    maintenance_start = Column(Time())
    maintenance_end = Column(Time())
