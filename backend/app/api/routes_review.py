"""
Review / validation: the human-in-the-loop surface.

* GET  /review/queue                  — ambiguous-band pairs with explanations
* POST /review/pairs/{id}/decision    — approve (merges families) / reject
* POST /review/clusters/{id}/decision — approve / reject a proposed family
* POST /review/clusters/{id}/split    — pull a wrongly-merged row out
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import DecisionIn, ReviewPairOut
from app.services import review_service
from app.services.common import resolve_job

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[ReviewPairOut])
def queue(job_id: int | None = None, status: str = "open",
          limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        return []
    return review_service.review_queue(db, job.id, limit, offset, status)


@router.post("/pairs/{pair_id}/decision")
def decide_pair(pair_id: int, body: DecisionIn, db: Session = Depends(get_db)):
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    try:
        return review_service.decide_pair(db, pair_id, body.action, body.reason,
                                          body.user)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/clusters/{cluster_id}/decision")
def decide_cluster(cluster_id: int, body: DecisionIn, db: Session = Depends(get_db)):
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    try:
        return review_service.decide_cluster(db, cluster_id, body.action,
                                             body.reason, body.user)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/clusters/{cluster_id}/split")
def split_member(cluster_id: int, raw_id: int, reason: str | None = None,
                 user: str = "steward", db: Session = Depends(get_db)):
    try:
        return review_service.split_member(db, cluster_id, raw_id, reason, user)
    except ValueError as e:
        raise HTTPException(400, str(e))
