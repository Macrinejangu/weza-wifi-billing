from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import CustomerRegistration, create_customer_account, current_staff, require_admin
from app.db.session import get_db
from app.models import AdminAuditLog, User
from app.schemas.payment import normalise_kenyan_mobile

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
    registered_on: date | None = None,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter_by(role="customer")
    if status:
        query = query.filter_by(status=status)

    if registered_on:
        start = datetime.combine(registered_on, time.min, tzinfo=ZoneInfo("Africa/Nairobi"))
        query = query.filter(User.created_at >= start, User.created_at < start + timedelta(days=1))

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


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    phone: Annotated[str, StringConstraints(max_length=32)] | None


@router.post("", response_model=CustomerRead, status_code=201)
def add_customer(
    data: CustomerRegistration, staff: User = Depends(require_admin), db: Session = Depends(get_db),
):
    return create_customer_account(data, db, staff_id=staff.id)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int, data: CustomerUpdate, staff: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    customer = db.scalar(select(User).where(User.id == customer_id, User.role == "customer").with_for_update())
    if customer is None:
        raise HTTPException(404, "Customer not found")
    try:
        phone = normalise_kenyan_mobile(data.phone) if data.phone and data.phone.strip() else None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    old = {"full_name": customer.full_name, "phone": customer.phone}
    if old == {"full_name": data.full_name, "phone": phone}:
        return customer
    if phone and db.scalar(select(User.id).where(
        User.id != customer.id,
        func.replace(func.trim(User.phone), " ", "").in_((phone, f"+{phone}", f"0{phone[3:]}")),
    ).limit(1)) is not None:
        raise HTTPException(409, "Another account already uses this phone number.")
    customer.full_name, customer.phone = data.full_name, phone
    db.add(AdminAuditLog(
        admin_id=staff.id, action="Updated customer", entity_type="customer", entity_id=customer.id,
    ))
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) != "23505":
            raise
        raise HTTPException(409, "Another account already uses this phone number.") from None
    return customer
