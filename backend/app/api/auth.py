from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, read_token, verify_password
from app.db.session import get_db
from app.models import AdminAuditLog, User
from app.schemas.payment import normalise_kenyan_mobile

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)
STAFF_ROLES = ("admin", "operator")
CUSTOMER_AUDIENCE = "customer-portal"
_FAKE_HASH = hash_password("unused")  # so an unknown email takes as long as a wrong password


class LoginIn(BaseModel):
    email: str
    password: str


def current_staff(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                  db: Session = Depends(get_db)) -> User:
    """Use as a dependency on any operator-only route."""
    user_id = read_token(credentials.credentials) if credentials else None
    user = db.get(User, user_id) if user_id else None
    if user is None or user.status != "active":
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if user.role not in STAFF_ROLES:
        raise HTTPException(403, "Staff only")
    return user


def require_admin(staff: User = Depends(current_staff)) -> User:
    if staff.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return staff


def authenticate_user(db: Session, data: LoginIn, roles: tuple[str, ...]) -> User:
    user = db.query(User).filter(func.lower(User.email) == data.email.strip().lower()).first()
    password_ok = verify_password(data.password, user.password_hash if user else _FAKE_HASH)
    if not (user and password_ok and user.status == "active" and user.role in roles):
        raise HTTPException(401, "Invalid email or password")
    return user


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    staff = authenticate_user(db, data, STAFF_ROLES)
    return {"access_token": create_token(staff.id), "token_type": "bearer"}


@router.get("/me")
def me(staff: User = Depends(current_staff)):
    return {"id": staff.id, "full_name": staff.full_name, "email": staff.email, "role": staff.role}


class CustomerLoginIn(LoginIn):
    email: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=128)


class CustomerRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: Annotated[str, StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )]
    phone: str = Field(max_length=32)
    password: SecretStr


class CustomerProfile(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None


def current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = read_token(credentials.credentials, audience=CUSTOMER_AUDIENCE) if credentials else None
    user = db.get(User, user_id) if user_id else None
    if user is None or user.status != "active" or user.role != "customer":
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user


@router.post("/customer/register", response_model=CustomerProfile, status_code=201)
def register_customer(data: CustomerRegistration, db: Session = Depends(get_db)):
    customer = create_customer_account(data, db)
    return CustomerProfile(id=customer.id, full_name=customer.full_name, email=customer.email, phone=customer.phone)


def create_customer_account(data: CustomerRegistration, db: Session, *, staff_id: int | None = None) -> User:
    password = data.password.get_secret_value()
    if not 8 <= len(password) <= 128 or not password.strip():
        raise HTTPException(422, "Use a password with 8 to 128 characters.")
    try:
        phone = normalise_kenyan_mobile(data.phone)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None

    conflict_message = "An account already uses these details. Sign in or contact support."
    phone_forms = (phone, f"+{phone}", f"0{phone[3:]}")
    existing = db.scalar(select(User.id).where(or_(
        func.lower(User.email) == data.email,
        func.replace(func.trim(User.phone), " ", "").in_(phone_forms),
    )).limit(1))
    if existing is not None:
        raise HTTPException(409, conflict_message)

    customer = User(
        full_name=data.full_name, email=data.email, phone=phone,
        password_hash=hash_password(password), role="customer", status="active",
    )
    db.add(customer)
    try:
        if staff_id is not None:
            db.flush()
            db.add(AdminAuditLog(
                admin_id=staff_id, action="Registered customer",
                entity_type="customer", entity_id=customer.id,
            ))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) != "23505":
            raise
        raise HTTPException(409, conflict_message) from None
    db.refresh(customer)
    return customer


@router.post("/customer/login")
def customer_login(data: CustomerLoginIn, db: Session = Depends(get_db)):
    customer = authenticate_user(db, data, ("customer",))
    token = create_token(customer.id, audience=CUSTOMER_AUDIENCE)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/customer/me", response_model=CustomerProfile)
def customer_me(customer: User = Depends(current_customer)):
    return CustomerProfile(
        id=customer.id, full_name=customer.full_name, email=customer.email, phone=customer.phone,
    )
