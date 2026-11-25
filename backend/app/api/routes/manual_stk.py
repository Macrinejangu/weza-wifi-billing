"""Administrator-assisted M-Pesa prompts for existing purchases."""
import os
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.api.routes.payments import _error_response, _http_status, get_daraja_client
from app.config import ROOT_ENV
from app.db.session import get_db
from app.integrations.mpesa.client import StkPushAccepted
from app.models import Payment, Purchase, User
from app.payments.payment_service_errors import PaymentServiceError
from app.schemas.payment import normalise_kenyan_mobile
from app.services.mpesa_payment_service import initiate_payment

router = APIRouter(
    prefix="/api/staff/manual-stk", tags=["Staff"], dependencies=[Depends(require_admin)],
)


class PromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_id: int = Field(gt=0, le=2_147_483_647)
    phone: str = Field(max_length=32)


class SimulatedPrompt:
    def stk_push(self, *, amount, phone_number, account_reference, description):
        identifier = uuid4().hex
        return StkPushAccepted(f"simulated-stk-{identifier}", f"simulated-merchant-{identifier}")


def manual_mode() -> str:
    load_dotenv(ROOT_ENV)
    sandbox = os.getenv("ENABLE_DARAJA_SANDBOX_PAYMENTS", "").lower() == "true"
    mock = os.getenv("ENABLE_MOCK_PAYMENTS", "").lower() == "true"
    if sandbox and not mock:
        return "sandbox"
    if mock and not sandbox and os.getenv("ROUTER_MODE", "").lower() == "mock":
        return "simulated"
    return "unavailable"


def approved_phone(mode: str) -> str | None:
    if mode != "sandbox":
        return None
    try:
        return normalise_kenyan_mobile(os.getenv("DARAJA_TEST_PHONE", ""))
    except ValueError:
        return None


@router.get("/purchases")
def list_purchases(db: Session = Depends(get_db)):
    mode = manual_mode()
    test_phone = approved_phone(mode)
    if mode == "unavailable" or (mode == "sandbox" and not test_phone):
        return {"mode": "unavailable", "purchases": []}
    query = (
        select(Purchase, User)
        .join(User, User.id == Purchase.user_id)
        .where(Purchase.status == "pending", User.role == "customer", User.status == "active",
               User.phone.is_not(None), ~select(Payment.id).where(
                   Payment.purchase_id == Purchase.id, Payment.status.in_(("pending", "successful")),
               ).exists())
        .order_by(Purchase.id.desc()).limit(50)
    )
    if mode == "sandbox":
        query = query.where(Purchase.device_mac_address.is_not(None), Purchase.device_ip_address.is_not(None))
    options = []
    for purchase, customer in db.execute(query):
        try:
            phone = normalise_kenyan_mobile(customer.phone)
        except ValueError:
            continue
        if mode == "sandbox" and phone != test_phone:
            continue
        options.append({
            "id": purchase.id, "customer": customer.full_name, "phone": phone,
            "amount": purchase.amount, "package": purchase.package_name,
        })
    return {"mode": mode, "purchases": options}


@router.post("", status_code=201)
def send_prompt(data: PromptRequest, staff: User = Depends(require_admin), db: Session = Depends(get_db)):
    mode = manual_mode()
    if mode == "unavailable" or (mode == "sandbox" and not approved_phone(mode)):
        raise HTTPException(503, "Manual test payments are unavailable.")
    row = db.execute(
        select(Purchase, User).join(User, User.id == Purchase.user_id)
        .where(Purchase.id == data.purchase_id, User.role == "customer", User.status == "active")
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Purchase not found.")
    purchase, customer = row
    try:
        phone = normalise_kenyan_mobile(customer.phone or "")
        confirmed_phone = normalise_kenyan_mobile(data.phone)
    except ValueError:
        raise HTTPException(409, "The customer needs a valid saved mobile number.") from None
    if phone != confirmed_phone:
        raise HTTPException(409, "The saved phone changed. Review the purchase again.")
    if mode == "sandbox":
        if phone != approved_phone(mode):
            raise HTTPException(409, "Only the configured test handset is available.")
        if not purchase.device_mac_address or not purchase.device_ip_address:
            raise HTTPException(409, "Verify this customer’s hotspot device before sending a prompt.")
        provider = get_daraja_client()
        if provider is None:
            raise HTTPException(503, "The Daraja test account is unavailable.")
    else:
        provider = SimulatedPrompt()
    try:
        result = initiate_payment(db, provider, purchase.id, phone, staff_id=staff.id)
    except PaymentServiceError as error:
        return _error_response(_http_status(error), error.code, error.message, error.payment_id)
    return {"payment_id": result.payment_id, "status": "pending", "simulated": mode == "simulated"}
