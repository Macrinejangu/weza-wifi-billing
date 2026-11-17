from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from app.db.base import Base, TimestampMixin


class Purchase(TimestampMixin, Base):
    # this is just What the customer chose to buy, Payments are attempts to pay for it.

    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'paid', 'failed', 'expired')", name="ck_purchases_status"),
        CheckConstraint("amount > 0", name="ck_purchases_amount"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    amount = Column(Integer, nullable=False)  
    package_name = Column(String, nullable=False)  
    duration_minutes = Column(Integer, nullable=False)
    download_speed_mbps = Column(Integer, nullable=False)
    upload_speed_mbps = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    idempotency_key = Column(String(100), unique=True, nullable=False)
    