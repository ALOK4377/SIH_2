#!/usr/bin/env python3
"""
seed_db.py — one-shot: load the bundled synthetic dataset and run the pipeline,
so the API/UI have data to show immediately.

    python scripts/seed_db.py                 # uses SAMANVAY_DATABASE_URL or SQLite

Idempotent-ish: it always creates a fresh batch + job. Safe to re-run.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.db import SessionLocal, init_db      # noqa: E402
from app.models import Job                          # noqa: E402
from app.services import ingest_service             # noqa: E402
from app.services import pipeline_service           # noqa: E402


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print("Loading synthetic dataset …")
        batch = ingest_service.load_synthetic(db)
        print(f"  batch #{batch.id}: {batch.n_rows} rows")

        job = Job(batch_id=batch.id, status="pending",
                  params={"auto_threshold": 0.70, "review_low": 0.50})
        db.add(job)
        db.commit()
        db.refresh(job)

        print("Running pipeline (normalize → embed → block → score → cluster → CNMC) …")
        job = pipeline_service.run_pipeline(db, job)

        m = job.metrics or {}
        print(f"  job #{job.id}: {job.status}")
        if m.get("has_ground_truth"):
            print(f"  precision {m['precision']:.1%}  recall {m['recall']:.1%}  "
                  f"F1 {m['f1']:.1%}  ·  {m['groups_recovered_exactly']}/"
                  f"{m['truth_groups']} groups recovered exactly")
        print("\nDone. Start the API with:  uvicorn app.main:app --reload  (from backend/)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
