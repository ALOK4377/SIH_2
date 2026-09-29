"""
analytics_service.py — dashboard numbers.

The headline business metric is the **duplication rate**: how many of the
ingested rows were redundant codes for an item another row already describes
(`raw_rows − canonical_codes` / `raw_rows`). Fewer codes = less duplicated
inventory and a shot at aggregated procurement.

`potential_savings` is a deliberately conservative, explainable estimate: for
each material family bought by more than one CPSE, assume the aggregated demand
can be sourced at the family's **lowest observed unit price**. The saving is the
sum over members of (their price − the best price). No hidden multipliers —
a judge can recompute it from the mapping table.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (CanonicalMaterial, Cluster, ClusterMember, CodeMapping,
                        Cpse, Job, MaterialNorm, MaterialRaw, MatchPair)


def summary(db: Session, job: Job | None) -> dict:
    if job is None:
        return {
            "total_raw": 0, "total_canonical": 0, "duplicate_rows": 0,
            "duplication_rate": 0.0, "clusters_multi": 0, "clusters_total": 0,
            "review_pending": 0, "potential_savings": 0.0,
            "by_category": [], "by_cpse": {}, "metrics": {},
        }

    total_raw = db.scalar(select(func.count(MaterialRaw.id))
                          .where(MaterialRaw.batch_id == job.batch_id)) or 0
    total_canonical = db.scalar(select(func.count(CanonicalMaterial.id))
                                .where(CanonicalMaterial.job_id == job.id)) or 0
    clusters_total = db.scalar(select(func.count(Cluster.id))
                               .where(Cluster.job_id == job.id)) or 0
    clusters_multi = db.scalar(select(func.count(Cluster.id))
                               .where(Cluster.job_id == job.id, Cluster.size > 1)) or 0
    review_pending = db.scalar(
        select(func.count(MatchPair.id)).where(MatchPair.job_id == job.id,
                                               MatchPair.needs_review.is_(True),
                                               MatchPair.status == "open")) or 0

    duplicate_rows = max(0, total_raw - total_canonical)
    duplication_rate = (duplicate_rows / total_raw) if total_raw else 0.0

    # ---- category spread: raw rows vs canonical codes per category
    raw_by_cat = dict(db.execute(
        select(MaterialNorm.category, func.count(MaterialNorm.id))
        .join(MaterialRaw, MaterialRaw.id == MaterialNorm.raw_id)
        .where(MaterialRaw.batch_id == job.batch_id)
        .group_by(MaterialNorm.category)).all())
    canon_by_cat = dict(db.execute(
        select(CanonicalMaterial.category, func.count(CanonicalMaterial.id))
        .where(CanonicalMaterial.job_id == job.id)
        .group_by(CanonicalMaterial.category)).all())
    by_category = [
        {"category": cat, "raw": raw_by_cat.get(cat, 0),
         "canonical": canon_by_cat.get(cat, 0)}
        for cat in sorted(set(raw_by_cat) | set(canon_by_cat))
    ]

    by_cpse = {name: n for name, n in db.execute(
        select(Cpse.name, func.count(MaterialRaw.id))
        .join(MaterialRaw, MaterialRaw.cpse_id == Cpse.id)
        .where(MaterialRaw.batch_id == job.batch_id)
        .group_by(Cpse.name).order_by(func.count(MaterialRaw.id).desc())).all()}

    return {
        "total_raw": total_raw,
        "total_canonical": total_canonical,
        "duplicate_rows": duplicate_rows,
        "duplication_rate": round(duplication_rate, 4),
        "clusters_multi": clusters_multi,
        "clusters_total": clusters_total,
        "review_pending": review_pending,
        "potential_savings": round(potential_savings(db, job), 2),
        "by_category": by_category,
        "by_cpse": by_cpse,
        "metrics": job.metrics or {},
    }


def potential_savings(db: Session, job: Job) -> float:
    """Σ over multi-CPSE families of (member price − family best price)."""
    rows = db.execute(
        select(CodeMapping.cnmc, MaterialRaw.price, MaterialRaw.cpse_id)
        .join(MaterialRaw, MaterialRaw.id == CodeMapping.raw_id)
        .where(CodeMapping.job_id == job.id)).all()

    families: dict[str, list[tuple[float, int | None]]] = {}
    for cnmc, price, cpse in rows:
        families.setdefault(cnmc, []).append((price or 0.0, cpse))

    total = 0.0
    for members in families.values():
        prices = [p for p, _c in members if p > 0]
        cpses = {c for _p, c in members if c is not None}
        if len(prices) < 2 or len(cpses) < 2:
            continue                       # no aggregation opportunity
        best = min(prices)
        total += sum(p - best for p in prices)
    return total


def top_duplicated(db: Session, job: Job, limit: int = 10) -> list[dict]:
    """Biggest wins: the families unifying the most local codes."""
    rows = db.scalars(
        select(CanonicalMaterial)
        .where(CanonicalMaterial.job_id == job.id)
        .order_by(CanonicalMaterial.n_members.desc(),
                  CanonicalMaterial.n_cpses.desc())
        .limit(limit)).all()
    return [{
        "cnmc": c.cnmc, "category": c.category,
        "std_description": c.std_description,
        "n_members": c.n_members, "n_cpses": c.n_cpses,
    } for c in rows]


def cluster_member_ids(db: Session, cluster_id: int) -> list[int]:
    return list(db.scalars(select(ClusterMember.raw_id)
                           .where(ClusterMember.cluster_id == cluster_id)).all())
