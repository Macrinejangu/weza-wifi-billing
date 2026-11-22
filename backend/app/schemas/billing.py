from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CheckoutIn(BaseModel):
    user_id: int
    package_id: int


class PurchaseIn(CheckoutIn):
    device_reference: str | None = Field(default=None, max_length=2048)


class DeviceReferenceOut(BaseModel):
    device_reference: str


class PurchaseOut(Out):
    id: int
    amount: int
    package_name: str
    duration_minutes: int
    status: str


class MockPaymentIn(BaseModel):
    purchase_id: int
    phone_number: str = Field(pattern=r"^254[0-9]{9}$")  # 254XXXXXXXXX
    successful: bool = True


class PaymentOut(Out):
    id: int
    status: str
    mpesa_receipt_number: str | None


class SessionIn(BaseModel):
    payment_id: int
    device_mac_address: str | None = Field(default=None, max_length=17)
    device_ip_address: str | None = Field(default=None, max_length=45)


class SessionOut(Out):
    id: int
    status: str
    activation_status: str
    failure_reason: str | None
    started_at: datetime | None
    expires_at: datetime | None
