"""Material search & explorer: raw + normalized rows with their assigned CNMC."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import MaterialOut
from app.services import read_service
from app.services.common import resolve_job

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialOut])
def list_materials(q: str | None = None, category: str | None = None,
                   cpse: str | None = None, job_id: int | None = None,
                   limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    return read_service.list_materials(db, job.id if job else None, q, category,
                                       cpse, limit, offset)
