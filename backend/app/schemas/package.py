from pydantic import BaseModel, ConfigDict
from decimal import Decimal

class PackageCreate(BaseModel):
    name: str
    service_type: str
    price: Decimal
    duration_minutes: int
    description: str | None = None

class PackageUpdate(PackageCreate):
    is_active: bool

class PackageResponse(PackageCreate):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
    