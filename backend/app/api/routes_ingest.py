"""Ingestion: upload a CPSE material-master CSV, or load the bundled demo data."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Batch
from app.schemas import BatchOut
from app.services import ingest_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/upload", response_model=BatchOut)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(400, "please upload a .csv file")
    content = await file.read()
    rows = ingest_service.parse_csv(content)
    if not rows:
        raise HTTPException(400, "no rows found in file")
    batch = ingest_service.create_batch(db, name=file.filename, rows=rows,
                                        source_file=file.filename)
    return batch


@router.post("/load-synthetic", response_model=BatchOut)
def load_synthetic(db: Session = Depends(get_db)):
    return ingest_service.load_synthetic(db)


@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)):
    return db.scalars(select(Batch).order_by(Batch.id.desc())).all()
