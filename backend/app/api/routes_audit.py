"""Audit trail viewer (governance): who did what, when."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import AuditLog
from app.schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(entity: str | None = None, limit: int = 100, offset: int = 0,
               db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.id.desc())
    if entity:
        q = q.where(AuditLog.entity == entity)
    return db.scalars(q.limit(limit).offset(offset)).all()
