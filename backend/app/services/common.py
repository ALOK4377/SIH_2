"""common.py — small shared query helpers used across routers/services."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, MaterialNorm, MaterialRaw


def latest_done_job(db: Session) -> Job | None:
    return db.scalars(
        select(Job).where(Job.status == "done").order_by(Job.id.desc()).limit(1)
    ).first()


def resolve_job(db: Session, job_id: int | None) -> Job | None:
    if job_id is not None:
        return db.get(Job, job_id)
    return latest_done_job(db)


def member_dict(raw: MaterialRaw, norm: MaterialNorm | None) -> dict:
    return {
        "raw_id": raw.id,
        "cpse": raw.cpse.name if raw.cpse else None,
        "local_code": raw.local_code,
        "description": raw.description,
        "clean_desc": norm.clean_desc if norm else None,
        "price": raw.price or 0.0,
    }
