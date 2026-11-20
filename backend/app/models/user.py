from sqlalchemy import CheckConstraint, Column, Integer, String
from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'admin', 'operator')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'suspended', 'inactive')", name="ck_users_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="customer", nullable=False)
    status = Column(String(20), default="active", server_default="active", nullable=False)
