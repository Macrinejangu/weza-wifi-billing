from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import AdminAuditLog, SupportFaq, User

router = APIRouter(prefix="/api/support/faqs", tags=["Customer support"])

SupportStep = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class SupportFaqUpdate(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    steps: list[SupportStep] = Field(min_length=1, max_length=8)


class SupportFaqRead(SupportFaqUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int


@router.get("", response_model=list[SupportFaqRead])
def list_faqs(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.scalars(select(SupportFaq).order_by(SupportFaq.id)).all()


@router.put("/{faq_id}", response_model=SupportFaqRead)
def update_faq(
    faq_id: int, data: SupportFaqUpdate, staff: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    faq = db.get(SupportFaq, faq_id, with_for_update=True)
    if faq is None:
        raise HTTPException(404, "Support answer not found")
    before = {"question": faq.question, "steps": faq.steps}
    after = data.model_dump()
    if before != after:
        faq.question = data.question
        faq.steps = data.steps
        db.add(AdminAuditLog(
            admin_id=staff.id, action="Updated support answer", entity_type="support_faq",
            entity_id=faq.id, old_values=before, new_values=after,
        ))
        db.commit()
    return faq
