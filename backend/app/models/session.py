
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class WiFiSession(TimestampMixin, Base):
    """
    Internet access associated with a payment.

    status tracks the session lifecycle.
    activation_status tracks the router activation result.
    """

    __tablename__ = "sessions"

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'PENDING_PAYMENT', "
            "'PAYMENT_CONFIRMED', "
            "'ACTIVATING', "
            "'ACTIVE', "
            "'EXPIRED', "
            "'FAILED', "
            "'CANCELLED'"
            ")",
            name="ck_sessions_status",
        ),
        CheckConstraint(
            "activation_status IN ("
            "'not_started', "
            "'waiting', "
            "'succeeded', "
            "'failed'"
            ")",
            name="ck_sessions_activation_status",
        ),
        CheckConstraint(
            "activation_status = 'succeeded' "
            "OR (started_at IS NULL AND expires_at IS NULL)",
            name="ck_sessions_timer_needs_activation",
        ),
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    package_id = Column(
        Integer,
        ForeignKey("packages.id"),
        nullable=False,
    )

    access_point_id = Column(
        Integer,
        ForeignKey("access_points.id"),
        nullable=True,
    )

    router_id = Column(
        Integer,
        ForeignKey("routers.id"),
        nullable=True,
        index=True,
    )

    payment_id = Column(
        Integer,
        ForeignKey("payments.id"),
        nullable=False,
        unique=True,
    )

    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), unique=True)

    device_mac_address = Column(String(17))
    device_ip_address = Column(String(45))

    status = Column(
        String(30),
        default="PENDING_PAYMENT",
        nullable=False,
    )

    activation_status = Column(
        String(20),
        default="not_started",
        nullable=False,
        index=True,
    )

    activation_requested_at = Column(
        DateTime(timezone=True),
    )

    failure_reason = Column(String(255))

    started_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    payment = relationship("Payment")
    subscription = relationship("Subscription")

    attempts = relationship("ActivationAttempt")

    router = relationship(
        "Router",
        back_populates="sessions",
    )
