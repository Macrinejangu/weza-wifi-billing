from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, TimestampMixin


class SupportFaq(TimestampMixin, Base):
    __tablename__ = "support_faqs"

    id = Column(Integer, primary_key=True)
    question = Column(String(160), nullable=False)
    steps = Column(JSONB, nullable=False)
