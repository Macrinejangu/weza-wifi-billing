from pydantic import BaseModel, ConfigDict, Field


class PackageCreate(BaseModel):
    name: str
    service_type: str
    price: int = Field(gt=0)  # whole shillings
    duration_minutes: int = Field(gt=0)
    download_speed_mbps: int = Field(gt=0)
    upload_speed_mbps: int = Field(gt=0)
    description: str | None = None


class PackageUpdate(PackageCreate):
    is_active: bool


class PackageResponse(PackageCreate):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
    