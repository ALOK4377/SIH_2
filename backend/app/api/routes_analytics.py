"""Dashboard analytics: duplication rate, savings, category/CPSE spread, metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import AnalyticsSummary
from app.services import analytics_service
from app.services.common import resolve_job

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(job_id: int | None = None, db: Session = Depends(get_db)):
    return analytics_service.summary(db, resolve_job(db, job_id))


@router.get("/top")
def top_duplicated(job_id: int | None = None, limit: int = 10,
                   db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        return []
    return analytics_service.top_duplicated(db, job, limit=limit)
