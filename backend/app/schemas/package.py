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


class StaffPackageCreate(PackageCreate):
    name: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, le=2_147_483_647)
    duration_minutes: int = Field(gt=0, le=2_147_483_647)
    download_speed_mbps: int = Field(gt=0, le=2_147_483_647)
    upload_speed_mbps: int = Field(gt=0, le=2_147_483_647)
    description: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True)


class StaffPackageUpdate(StaffPackageCreate):
    is_active: bool
