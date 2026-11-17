from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import WiFiSession
from app.schemas.billing import SessionIn, SessionOut
from app.services.session_service import activate_session, create_session

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post("", response_model=SessionOut, status_code=201)
def new_session(data: SessionIn, db: Session = Depends(get_db)):
    return create_session(db, data.payment_id, data.device_mac_address, data.device_ip_address)


@router.post("/{session_id}/activate", response_model=SessionOut)
def activate(session_id: int, db: Session = Depends(get_db)):
    session = activate_session(db, session_id)
    if session.activation_status == "failed":
        raise HTTPException(502, f"Router activation failed: {session.failure_reason}")
    return session


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(WiFiSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session