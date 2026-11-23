from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, read_token, verify_password
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["Staff login"])
bearer = HTTPBearer(auto_error=False)
STAFF_ROLES = ("admin", "operator")
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


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == data.email.strip().lower()).first()
    password_ok = verify_password(data.password, user.password_hash if user else _FAKE_HASH)
    if not (user and password_ok and user.status == "active" and user.role in STAFF_ROLES):
        raise HTTPException(401, "Invalid email or password")  # same message for every failure
    return {"access_token": create_token(user.id), "token_type": "bearer"}


@router.get("/me")
def me(staff: User = Depends(current_staff)):
    return {"id": staff.id, "full_name": staff.full_name, "email": staff.email, "role": staff.role}
