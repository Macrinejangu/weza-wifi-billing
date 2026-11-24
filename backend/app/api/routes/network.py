from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_staff
from app.db.session import get_db
from app.models import AccessPoint, Router

router = APIRouter(prefix="/api/network", tags=["Staff"], dependencies=[Depends(current_staff)])


class RouterInventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    identity: str | None
    status: str


class AccessPointInventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    router_id: int | None
    location: str | None
    mac_address: str | None
    status: str
    last_seen_at: datetime | None


class DeviceInventoryRead(BaseModel):
    routers: list[RouterInventoryRead]
    access_points: list[AccessPointInventoryRead]


@router.get("/devices", response_model=DeviceInventoryRead)
def list_devices(db: Session = Depends(get_db)):
    return {
        "routers": db.scalars(select(Router).order_by(Router.name, Router.id)).all(),
        "access_points": db.scalars(select(AccessPoint).order_by(AccessPoint.name, AccessPoint.id)).all(),
    }
