"""Clusters (proposed material families) — list and detail."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Cluster
from app.schemas import ClusterOut
from app.services import read_service
from app.services.common import resolve_job

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterOut])
def list_clusters(status: str | None = None, multi_only: bool = True,
                  job_id: int | None = None, limit: int = 50, offset: int = 0,
                  db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        return []
    return read_service.list_clusters(db, job.id, status, multi_only, limit, offset)


@router.get("/{cluster_id}", response_model=ClusterOut)
def get_cluster(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.get(Cluster, cluster_id)
    if cluster is None:
        raise HTTPException(404, f"cluster {cluster_id} not found")
    return read_service.build_cluster_out(db, cluster)
