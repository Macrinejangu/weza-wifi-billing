
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Integer,
    String,
)

from app.db.base import Base, TimestampMixin


class Package(TimestampMixin, Base):
    """An internet package available for purchase."""

    __tablename__ = "packages"

    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_packages_price",
        ),
        CheckConstraint(
            "duration_minutes > 0",
            name="ck_packages_duration",
        ),
        CheckConstraint(
            "download_speed_mbps > 0",
            name="ck_packages_download_speed",
        ),
        CheckConstraint(
            "upload_speed_mbps > 0",
            name="ck_packages_upload_speed",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    service_type = Column(String, nullable=False)

    price = Column(Integer, nullable=False)

    duration_minutes = Column(Integer, nullable=False)

    download_speed_mbps = Column(Integer, nullable=False)

    upload_speed_mbps = Column(Integer, nullable=False)

    description = Column(String, nullable=True)

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
