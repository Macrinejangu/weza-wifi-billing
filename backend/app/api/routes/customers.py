from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/api/customers", tags=["Staff"], dependencies=[Depends(current_staff)])


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str | None
    status: Literal["active", "inactive", "suspended"]
    created_at: datetime


@router.get("", response_model=list[CustomerRead])
def list_customers(
    status: Literal["active", "inactive", "suspended"] | None = None,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter_by(role="customer")
    if status:
        query = query.filter_by(status=status)

    term = (q or "").strip()
    if term:
        matches = [
            User.full_name.icontains(term, autoescape=True),
            User.phone.icontains(term, autoescape=True),
        ]
        if term.isascii() and term.isdecimal() and len(term) <= 10:
            customer_id = int(term)
            if customer_id <= 2**31 - 1:
                matches.append(User.id == customer_id)
        query = query.filter(or_(*matches))

    return query.order_by(User.id.desc()).offset(offset).limit(limit).all()
