"""
pipeline_service.py — run the proven ML pipeline for a Batch and persist every
stage to the database, then (if the batch carries ground-truth group_ids)
compute real precision / recall / F1 for the dashboard.

This is the seam between the pure-stdlib engine in app/ml/ (which works in
index space) and the relational store: we pass each raw row's DB primary key in
as its `id`, so the pipeline's canonicals/mappings come back keyed by real IDs.
"""
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ml import evaluate as ev
from app.ml import pipeline as pl
from app.ml.score import score_pair
from app.models import (CanonicalMaterial, Cluster, ClusterMember, CodeMapping,
                        Cpse, Job, MaterialNorm, MaterialRaw, MatchPair)
from app.services import audit


def _raw_rows_for_batch(db: Session, batch_id: int) -> list[dict]:
    rows = db.scalars(
        select(MaterialRaw).where(MaterialRaw.batch_id == batch_id)
        .order_by(MaterialRaw.id)
    ).all()
    cpse_name = {c.id: c.name for c in db.scalars(select(Cpse)).all()}
    return [{
        "id": r.id,
        "cpse": cpse_name.get(r.cpse_id, ""),
        "local_code": r.local_code,
        "description": r.description,
        "uom": r.uom or "",
        "category_raw": r.category_raw or "",
        "price": r.price or 0.0,
        "group_id": r.group_id,
    } for r in rows]


def _clear_previous(db: Session, batch_id: int) -> None:
    """Replace the ENTIRE result set on every run.

    The read path serves only the latest *done* job (see
    ``common.latest_done_job``), so there is exactly one active national
    registry: the most recent resolution. We therefore wipe all prior result
    rows — from every batch, not just this one — before persisting the new run.

    This must be global, not batch-scoped. ``canonical_material.cnmc`` is
    globally unique, but CNMC serials restart at 1 on every run (see
    ``ml/canonical.py``), so any leftover canonical from a *different* batch
    would collide on insert (``UNIQUE constraint failed: canonical_material.cnmc``).
    Ingested raw rows are kept — analytics scopes them by ``batch_id`` — only
    the derived results are replaced, which is what makes "Run resolution"
    (and re-seeding) safe to repeat.
    """
    # Delete children before parents: ClusterMember and CanonicalMaterial both
    # carry a FK to Cluster, so they must go first (matters on Postgres, which
    # enforces FKs; harmless on SQLite).
    db.execute(delete(ClusterMember))
    for model in (CanonicalMaterial, CodeMapping, MatchPair, Cluster):
        db.execute(delete(model))
    # MaterialNorm is unique per raw row; clear this batch's norms so re-running
    # the same rows can't trip that unique constraint on re-persist.
    raw_ids = db.scalars(
        select(MaterialRaw.id).where(MaterialRaw.batch_id == batch_id)).all()
    if raw_ids:
        db.execute(delete(MaterialNorm).where(MaterialNorm.raw_id.in_(raw_ids)))
    db.commit()


def run_pipeline(db: Session, job: Job) -> Job:
    job.status = "running"
    db.commit()
    try:
        _clear_previous(db, job.batch_id)
        raw_rows = _raw_rows_for_batch(db, job.batch_id)
        if not raw_rows:
            raise ValueError("batch has no material rows")

        auto = job.params.get("auto_threshold", pl.AUTO_THRESHOLD)
        review_low = job.params.get("review_low", pl.REVIEW_LOW)
        res = pl.run(raw_rows, auto_threshold=auto, review_low=review_low)

        records, vectors = res["records"], res["vectors"]
        id_of = [r["id"] for r in raw_rows]              # index → raw DB id
        idx_of = {rid: i for i, rid in enumerate(id_of)}
        cpse_id = {c.name: c.id for c in db.scalars(select(Cpse)).all()}

        _persist_norm(db, records, id_of)
        _persist_pairs(db, job.id, res, records, vectors, id_of, auto)
        cluster_conf = _cluster_confidence(res, idx_of)
        _persist_clusters(db, job.id, res, cluster_conf, cpse_id)

        metrics = _metrics(res, raw_rows)
        job.metrics = metrics
        job.status = "done"
        job.finished_at = datetime.utcnow()
        audit.record(db, "job", job.id, "pipeline_run",
                     after={"clusters": len(res["canonicals"]), **metrics})
        db.commit()
    except Exception as exc:                              # noqa: BLE001 — record + resurface
        db.rollback()
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.utcnow()
        db.commit()
        raise
    db.refresh(job)
    return job


def _persist_norm(db: Session, records, id_of) -> None:
    db.add_all([
        MaterialNorm(raw_id=id_of[i], clean_desc=r["clean_desc"],
                     uom_std=r["uom_std"], category=r["category"],
                     attributes=r["attributes"])
        for i, r in enumerate(records)
    ])
    db.flush()


def _persist_pairs(db, job_id, res, records, vectors, id_of, auto) -> None:
    """Accepted (merge) edges + the ambiguous-band review queue."""
    def mk(i, j, f, needs_review):
        return MatchPair(
            job_id=job_id, a_raw_id=id_of[i], b_raw_id=id_of[j],
            semantic=f["semantic"], lexical=f["lexical"],
            attr_agree=f["attr_agree"], total_score=f["total"],
            conflict=f["conflict"], needs_review=needs_review,
            status="open", features={
                "attr_matches": f["attr_matches"],
                "attr_conflicts": f["attr_conflicts"],
                "uom_match": f["uom_match"],
                "attr_expected": f["attr_expected"],
            })

    batch = []
    for i, j, _t in res["accepted_edges"]:
        f = score_pair(records[i], records[j], vectors[i], vectors[j])
        batch.append(mk(i, j, f, needs_review=False))
    for i, j, f in res["review_queue"]:
        batch.append(mk(i, j, f, needs_review=True))
    db.add_all(batch)
    db.flush()


def _cluster_confidence(res, idx_of) -> dict:
    """Mean accepted-edge score per cluster label (weakest→1.0 for singletons)."""
    label_of = res["label_of"]
    sums, counts = {}, {}
    for i, j, t in res["accepted_edges"]:
        lab = label_of[i]
        if label_of[j] != lab:
            continue
        sums[lab] = sums.get(lab, 0.0) + t
        counts[lab] = counts.get(lab, 0) + 1
    return {lab: round(sums[lab] / counts[lab], 3) for lab in sums}


def _persist_clusters(db, job_id, res, cluster_conf, cpse_id) -> None:
    label_of = res["label_of"]
    # map raw DB id → record index to look up the cluster label of a canonical
    idx_of = {rid: i for i, rid in enumerate(r["id"] for r in res["raw_rows"])}

    for c in res["canonicals"]:
        first_idx = idx_of[c["member_ids"][0]]
        label = label_of[first_idx]
        conf = cluster_conf.get(label, 1.0)
        status = "proposed" if c["n_members"] > 1 else "approved"
        cluster = Cluster(job_id=job_id, status=status, size=c["n_members"],
                          confidence=conf)
        db.add(cluster)
        db.flush()
        db.add_all([ClusterMember(cluster_id=cluster.id, raw_id=rid)
                    for rid in c["member_ids"]])
        db.add(CanonicalMaterial(
            cluster_id=cluster.id, job_id=job_id, cnmc=c["cnmc"],
            category=c["category"], unspsc_code=c["unspsc_code"],
            unspsc_title=c["unspsc_title"], std_description=c["canonical_desc"],
            uom=c["uom"], attributes=c["attributes"],
            n_members=c["n_members"], n_cpses=c["n_cpses"]))

    db.add_all([
        CodeMapping(job_id=job_id, cnmc=m["cnmc"],
                    cpse_id=cpse_id.get(m["cpse"]), raw_id=m["id"],
                    local_code=m["local_code"])
        for m in res["mappings"]
    ])
    db.flush()


def _metrics(res, raw_rows) -> dict:
    group_of = [r.get("group_id") for r in raw_rows]
    if any(g is None for g in group_of):
        return {"has_ground_truth": False}

    truth = ev.truth_pairs(group_of)
    pred = ev.cluster_pairs(res["clusters"])
    m = ev.prf(pred, truth)
    q = ev.cluster_quality(res["clusters"], group_of)
    br = ev.blocking_recall([(i, j) for (i, j, _t, _c) in res["edges_all"]], truth)
    return {
        "has_ground_truth": True,
        "precision": round(m["precision"], 4),
        "recall": round(m["recall"], 4),
        "f1": round(m["f1"], 4),
        "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
        "blocking_recall": round(br, 4),
        "pure_fraction": round(q["pure_fraction"], 4),
        "groups_recovered_exactly": q["groups_recovered_exactly"],
        "truth_groups": q["truth_groups"],
    }
