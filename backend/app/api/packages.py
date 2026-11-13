from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.package import Package
from app.schemas.package import PackageCreate, PackageUpdate, PackageResponse

router = APIRouter(prefix="/packages", tags=["Packages"])

@router.get("/", response_model=list[PackageResponse])
def get_packages(db: Session = Depends(get_db)):
    return db.query(Package).all()

@router.post("/", response_model=PackageResponse)
def add_package(data: PackageCreate, db: Session = Depends(get_db)):
    package = Package(**data.model_dump())
    db.add(package)
    db.commit()
    db.refresh(package)
    return package

@router.put("/{package_id}", response_model=PackageResponse)
def update_package(package_id: int, data: PackageUpdate, db: Session = Depends(get_db)):
    package = db.query(Package).filter(Package.id == package_id).first()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    for key, value in data.model_dump().items():
        setattr(package, key, value)

    db.commit()
    db.refresh(package)
    return package

@router.delete("/{package_id}")
def deactivate_package(package_id: int, db: Session = Depends(get_db)):
    package = db.query(Package).filter(Package.id == package_id).first()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    package.is_active = False
    db.commit()
    return {"message": "Package deactivated"}
