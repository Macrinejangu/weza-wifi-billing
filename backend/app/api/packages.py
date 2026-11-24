from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import current_staff, require_admin
from app.db.session import get_db
from app.models import AdminAuditLog, Package, User
from app.schemas.package import PackageResponse, StaffPackageCreate, StaffPackageUpdate

router = APIRouter(prefix="/packages", tags=["Packages"])


@router.get("/", response_model=list[PackageResponse])
def get_packages(db: Session = Depends(get_db)):
    return db.query(Package).filter_by(is_active=True).order_by(Package.id).all()


@router.get("/staff", response_model=list[PackageResponse], dependencies=[Depends(current_staff)])
def list_staff_packages(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.scalars(select(Package).order_by(Package.id)).all()


def locked_package(db: Session, package_id: int) -> Package:
    package = db.get(Package, package_id, with_for_update=True)
    if package is None:
        raise HTTPException(404, "Package not found")
    return package


def record_package_change(
    db: Session, staff: User, package: Package, action: str, old_values: dict | None = None,
):
    db.add(AdminAuditLog(
        admin_id=staff.id, action=action, entity_type="package", entity_id=package.id,
        old_values=old_values, new_values=PackageResponse.model_validate(package).model_dump(),
    ))


@router.post("/", response_model=PackageResponse)
def add_package(
    data: StaffPackageCreate, staff: User = Depends(require_admin), db: Session = Depends(get_db),
):
    if data.service_type != "hotspot":
        raise HTTPException(422, "New packages must be hotspot packages.")
    package = Package(**data.model_dump())
    db.add(package)
    db.flush()
    record_package_change(db, staff, package, "Created package")
    db.commit()
    return package


@router.put("/{package_id}", response_model=PackageResponse)
def update_package(
    package_id: int, data: StaffPackageUpdate, staff: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    package = locked_package(db, package_id)
    if package.service_type != data.service_type:
        raise HTTPException(422, "The package type cannot be changed.")
    before = PackageResponse.model_validate(package).model_dump()
    changes = data.model_dump()
    if any(before[field] != value for field, value in changes.items()):
        for field, value in changes.items():
            setattr(package, field, value)
        record_package_change(db, staff, package, "Updated package", before)
        db.commit()
    return package


@router.delete("/{package_id}")
def deactivate_package(
    package_id: int, staff: User = Depends(require_admin), db: Session = Depends(get_db),
):
    package = locked_package(db, package_id)
    if package.is_active:
        before = PackageResponse.model_validate(package).model_dump()
        package.is_active = False
        record_package_change(db, staff, package, "Deactivated package", before)
        db.commit()
    return {"message": "Package deactivated"}
