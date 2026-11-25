import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Lock

from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_staff, require_admin
from app.config import ROOT_ENV, router_settings
from app.db.session import get_db
from app.models import AccessPoint, Router
from app.services.network_checks import ping_device, ping_target, read_gateway

router = APIRouter(prefix="/api/network", tags=["Staff"], dependencies=[Depends(current_staff)])


class RouterInventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    identity: str | None
    status: str
    last_synced_at: datetime | None
    hotspot_enabled: bool | None


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


def simulated_checks() -> bool:
    load_dotenv(ROOT_ENV)
    return os.getenv("ROUTER_MODE", "").lower() == "mock" and os.getenv("ENABLE_MOCK_PAYMENTS", "").lower() == "true"


sweep_lock = Lock()


@router.post("/ping-sweep", dependencies=[Depends(require_admin)])
def ping_sweep(db: Session = Depends(get_db)):
    simulated = simulated_checks()
    if not simulated and os.getenv("ROUTER_MODE", "").lower() != "mikrotik":
        raise HTTPException(503, "Choose the isolated MikroTik or simulation before running checks.")
    if not sweep_lock.acquire(blocking=False):
        raise HTTPException(409, "A device sweep is already running.")
    try:
        gateways = db.scalars(select(Router).order_by(Router.id).limit(21)).all()
        points = db.scalars(select(AccessPoint).order_by(AccessPoint.id).limit(21)).all()
        devices = [(f"router-{r.id}", r.name, r.host) for r in gateways[:20]]
        devices.extend((f"access-point-{ap.id}", ap.name, ap.management_ip) for ap in points[:20])
        truncated = len(gateways) > 20 or len(points) > 20
        db.rollback()

        def check(device):
            key, name, address = device
            target = ping_target(address)
            if not address:
                status = "no_address"
            elif not target:
                status = "unsupported_address"
            elif simulated:
                status = "reachable" if key.startswith("router-") else "no_response"
            else:
                status = ping_device(target)
            return {"key": key, "name": name, "result": status}

        with ThreadPoolExecutor(max_workers=6) as workers:
            results = list(workers.map(check, devices))
        return {"simulated": simulated, "checked_at": datetime.now(UTC), "results": results, "truncated": truncated}
    finally:
        sweep_lock.release()


@router.post("/sync-gateway", dependencies=[Depends(require_admin)])
def sync_gateway(db: Session = Depends(get_db)):
    if simulated_checks():
        return {"simulated": True, "identity": "Weza Demo Router", "hotspot_enabled": True,
                "checked_at": datetime.now(UTC)}
    try:
        if os.getenv("ROUTER_MODE", "").lower() != "mikrotik":
            raise RuntimeError("An isolated MikroTik is required")
        host = router_settings()["host"]
    except RuntimeError:
        raise HTTPException(503, "Configure the isolated MikroTik before syncing.") from None
    gateway_id = db.scalar(select(Router.id).where(Router.host == host))
    if gateway_id is None:
        raise HTTPException(409, "Register the configured router in the device inventory before syncing.")
    db.rollback()
    try:
        identity, hotspot_enabled = read_gateway()
    except Exception:
        raise HTTPException(503, "Could not read the configured hotspot. The last successful sync is unchanged.") from None

    gateway = db.get(Router, gateway_id, with_for_update=True)
    if gateway is None or gateway.host != host:
        raise HTTPException(409, "The registered gateway changed during the sync.")
    gateway.identity = identity
    gateway.status = "online"
    gateway.hotspot_enabled = hotspot_enabled
    gateway.last_synced_at = datetime.now(UTC)
    checked_at = gateway.last_synced_at
    db.commit()
    return {"simulated": False, "identity": identity, "hotspot_enabled": hotspot_enabled, "checked_at": checked_at}
