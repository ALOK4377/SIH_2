"""
ingest_service.py — turn CSV rows (upload or bundled demo data) into a Batch of
MaterialRaw records, upserting the referenced CPSEs.

Accepted columns (header, case-insensitive): local_code, description, uom,
category_raw, price, cpse, sector. `id` and `group_id` are optional; group_id
(ground-truth label) is preserved so the dashboard can report precision/recall.
Only `description` is strictly required.
"""
import csv
import io
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Batch, Cpse, MaterialRaw
from app.services import audit

settings = get_settings()


def _norm_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [_norm_header(h) for h in (reader.fieldnames or [])]
    rows = []
    for r in reader:
        rows.append({_norm_header(k): (v or "").strip() for k, v in r.items()})
    return rows


def _get_or_create_cpse(db: Session, name: str, sector: str | None,
                        cache: dict) -> Cpse | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    cpse = db.scalar(select(Cpse).where(Cpse.name == name))
    if cpse is None:
        cpse = Cpse(name=name, sector=sector or None)
        db.add(cpse)
        db.flush()
    cache[name] = cpse
    return cpse


def create_batch(db: Session, name: str, rows: list[dict],
                 source_file: str | None = None) -> Batch:
    batch = Batch(name=name, source_file=source_file, n_rows=0)
    db.add(batch)
    db.flush()

    cache: dict[str, Cpse] = {}
    n = 0
    for r in rows:
        desc = r.get("description", "")
        if not desc:
            continue
        cpse = _get_or_create_cpse(db, r.get("cpse", ""), r.get("sector"), cache)
        gid = r.get("group_id")
        price = r.get("price")
        db.add(MaterialRaw(
            batch_id=batch.id,
            cpse_id=cpse.id if cpse else None,
            local_code=r.get("local_code") or f"AUTO-{n}",
            description=desc,
            uom=r.get("uom") or None,
            category_raw=r.get("category_raw") or None,
            price=float(price) if price else 0.0,
            source_file=source_file,
            group_id=int(gid) if (gid not in (None, "")) else None,
        ))
        n += 1

    batch.n_rows = n
    audit.record(db, "batch", batch.id, "ingest",
                 after={"name": name, "n_rows": n, "source_file": source_file})
    db.commit()
    db.refresh(batch)
    return batch


def load_synthetic(db: Session) -> Batch:
    """Load the repo's bundled synthetic dataset (+ ground truth if present)."""
    mats = os.path.join(settings.synthetic_dir, "materials.csv")
    gt = os.path.join(settings.synthetic_dir, "ground_truth.csv")
    with open(mats, "rb") as f:
        rows = parse_csv(f.read())

    if os.path.exists(gt):
        with open(gt, "rb") as f:
            truth = {r["id"]: r["group_id"] for r in parse_csv(f.read())}
        for r in rows:
            if r.get("id") in truth:
                r["group_id"] = truth[r["id"]]

    return create_batch(db, name="Synthetic CPSE dataset", rows=rows,
                        source_file="data/synthetic/materials.csv")
