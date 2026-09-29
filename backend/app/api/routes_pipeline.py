"""Pipeline runs: kick off matching for a batch and inspect job status/metrics."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Batch, Job
from app.schemas import JobOut, RunRequest
from app.services import pipeline_service

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
settings = get_settings()


@router.post("/run", response_model=JobOut)
def run(req: RunRequest, db: Session = Depends(get_db)):
    batch = db.get(Batch, req.batch_id)
    if batch is None:
        raise HTTPException(404, f"batch {req.batch_id} not found")
    job = Job(batch_id=batch.id, status="pending", params={
        "auto_threshold": req.auto_threshold if req.auto_threshold is not None
        else settings.auto_threshold,
        "review_low": req.review_low if req.review_low is not None
        else settings.review_low,
    })
    db.add(job)
    db.commit()
    db.refresh(job)
    # synchronous run — the demo dataset is small; swap for Celery at scale.
    return pipeline_service.run_pipeline(db, job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(Job).order_by(Job.id.desc())).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, f"job {job_id} not found")
    return job
