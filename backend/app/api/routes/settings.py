import os
from datetime import datetime, time
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, StringConstraints, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import STAFF_ROLES, current_staff, require_admin
from app.config import ROOT_ENV
from app.db.session import get_db
from app.models import AdminAuditLog, SystemSettings, User

router = APIRouter(prefix="/api/staff/settings", tags=["Staff settings"])


class Preferences(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    maintenance_start: time | None
    maintenance_end: time | None

    @model_validator(mode="after")
    def validate_window(self):
        start, end = self.maintenance_start, self.maintenance_end
        if (start is None) != (end is None):
            raise ValueError("Provide both maintenance times or clear both.")
        if start is not None and (
            start == end or start.tzinfo or end.tzinfo
            or start.second or end.second or start.microsecond or end.microsecond
        ):
            raise ValueError("Use different local maintenance times in hours and minutes.")
        return self


class SettingsRead(BaseModel):
    preferences: Preferences
    role: Literal["admin", "operator"]
    active_staff_by_role: dict[str, int]
    daraja_sandbox_enabled: bool
    mock_payments_enabled: bool
    router_mode: Literal["mock", "mikrotik", "unconfigured"]


class AuditEntry(BaseModel):
    id: int
    created_at: datetime
    actor: str | None
    action: str
    entity_type: str
    entity_id: int | None


def settings_row(db: Session, *, lock: bool = False) -> SystemSettings:
    settings = db.get(SystemSettings, 1, with_for_update=lock)
    if settings is None:
        raise HTTPException(503, "System settings are unavailable")
    return settings


def read_preferences(settings: SystemSettings) -> Preferences:
    return Preferences(
        name=settings.name,
        maintenance_start=settings.maintenance_start,
        maintenance_end=settings.maintenance_end,
    )


@router.get("", response_model=SettingsRead)
def get_settings(
    response: Response, staff: User = Depends(current_staff), db: Session = Depends(get_db),
):
    load_dotenv(ROOT_ENV)
    mode = os.getenv("ROUTER_MODE", "").strip().lower()
    counts = dict(db.execute(
        select(User.role, func.count(User.id))
        .where(User.role.in_(STAFF_ROLES), User.status == "active")
        .group_by(User.role)
    ).all())
    response.headers["Cache-Control"] = "no-store"
    return SettingsRead(
        preferences=read_preferences(settings_row(db)),
        role=staff.role,
        active_staff_by_role={role: counts.get(role, 0) for role in STAFF_ROLES},
        daraja_sandbox_enabled=os.getenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "false").lower() == "true",
        mock_payments_enabled=os.getenv("ENABLE_MOCK_PAYMENTS", "false").lower() == "true",
        router_mode=mode if mode in ("mock", "mikrotik") else "unconfigured",
    )


@router.put("", response_model=Preferences)
def update_settings(
    data: Preferences, staff: User = Depends(require_admin), db: Session = Depends(get_db),
):
    settings = settings_row(db, lock=True)
    before = read_preferences(settings)
    if before != data:
        settings.name = data.name
        settings.maintenance_start = data.maintenance_start
        settings.maintenance_end = data.maintenance_end
        db.add(AdminAuditLog(
            admin_id=staff.id,
            action="Updated system preferences",
            entity_type="system_settings",
            entity_id=settings.id,
            old_values=before.model_dump(mode="json"),
            new_values=data.model_dump(mode="json"),
        ))
        db.commit()
    return data


@router.get("/audit", response_model=list[AuditEntry], dependencies=[Depends(require_admin)])
def list_audit_history(
    response: Response, limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0), db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    rows = db.execute(
        select(
            AdminAuditLog.id, AdminAuditLog.created_at, User.full_name.label("actor"),
            AdminAuditLog.action, AdminAuditLog.entity_type, AdminAuditLog.entity_id,
        )
        .outerjoin(User, User.id == AdminAuditLog.admin_id)
        .order_by(AdminAuditLog.id.desc()).limit(limit).offset(offset)
    ).mappings()
    return [AuditEntry.model_validate(row) for row in rows]
