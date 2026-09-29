"""
Common National Material Codes (CNMC) registry: browse the golden records,
inspect the local codes each one unifies, and export the full mapping table as
CSV (the artifact a CPSE would load to migrate its ERP material master).
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import CanonicalMaterial
from app.schemas import CanonicalOut, CodeMappingOut
from app.services import read_service
from app.services.common import resolve_job

router = APIRouter(prefix="/codes", tags=["codes"])


@router.get("", response_model=list[CanonicalOut])
def list_codes(q: str | None = None, category: str | None = None,
               multi_only: bool = False, job_id: int | None = None,
               limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        return []
    return read_service.list_codes(db, job.id, q, category, multi_only, limit, offset)


@router.get("/export.csv")
def export_csv(job_id: int | None = None, db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        raise HTTPException(404, "no completed job to export")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["cnmc", "cpse", "local_code", "original_description",
                "standardized_description", "unspsc_code"])
    for row in read_service.all_mappings(db, job.id):
        w.writerow(list(row))
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cnmc_code_mapping.csv"})


@router.get("/{cnmc}", response_model=CanonicalOut)
def get_code(cnmc: str, job_id: int | None = None, db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    canon = db.scalar(select(CanonicalMaterial).where(
        CanonicalMaterial.cnmc == cnmc,
        *( [CanonicalMaterial.job_id == job.id] if job else [] )))
    if canon is None:
        raise HTTPException(404, f"CNMC {cnmc} not found")
    return canon


@router.get("/{cnmc}/mappings", response_model=list[CodeMappingOut])
def get_code_mappings(cnmc: str, job_id: int | None = None,
                      db: Session = Depends(get_db)):
    job = resolve_job(db, job_id)
    if job is None:
        return []
    return read_service.mappings_for_cnmc(db, job.id, cnmc)
