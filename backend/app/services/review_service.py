"""
review_service.py — the human-in-the-loop.

Two decision surfaces:

* **cluster** (approve / reject a proposed material family)
* **pair** (the ambiguous-band queue: approving MERGES the two rows' families
  and re-points every member's CNMC to the surviving golden record)

Every decision writes a `Review` row (which is also the label store for the
active-learning upgrade in PROJECT_PLAN §3.8) and an `AuditLog` entry, so a
governance reviewer can always answer "who merged these two codes, and why?".

Merges keep the *lower* CNMC serial as the survivor — codes are never reused,
and the absorbed code is retired rather than deleted from history (its audit
entry records it).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.canonical import UNSPSC, make_cnmc
from app.ml.explain import explain
from app.models import (CanonicalMaterial, Cluster, ClusterMember, CodeMapping,
                        MaterialNorm, MaterialRaw, MatchPair, Review)
from app.services import audit
from app.services.common import member_dict


def _norm_map(db: Session, raw_ids: list[int]) -> dict[int, MaterialNorm]:
    if not raw_ids:
        return {}
    rows = db.scalars(select(MaterialNorm)
                      .where(MaterialNorm.raw_id.in_(raw_ids))).all()
    return {n.raw_id: n for n in rows}


def _as_record(raw: MaterialRaw, norm: MaterialNorm | None) -> dict:
    """Rebuild the minimal normalized-record shape that explain() expects."""
    return {
        "clean_desc": norm.clean_desc if norm else raw.description,
        "uom_std": norm.uom_std if norm else (raw.uom or "EACH"),
        "category": norm.category if norm else "OTHER",
        "attributes": (norm.attributes if norm else {}) or {},
        "tokens": (norm.clean_desc if norm else raw.description).split(),
    }


def _features(pair: MatchPair) -> dict:
    """Reconstitute the score_pair feature dict from the persisted columns."""
    extra = pair.features or {}
    return {
        "semantic": pair.semantic,
        "lexical": pair.lexical,
        "attr_agree": pair.attr_agree,
        "attr_expected": extra.get("attr_expected", 3),
        "attr_matches": [tuple(m) for m in extra.get("attr_matches", [])],
        "attr_conflicts": [tuple(c) for c in extra.get("attr_conflicts", [])],
        "uom_match": extra.get("uom_match", True),
        "conflict": pair.conflict,
        "total": pair.total_score,
    }


def review_queue(db: Session, job_id: int, limit: int = 50, offset: int = 0,
                 status: str = "open") -> list[dict]:
    pairs = db.scalars(
        select(MatchPair)
        .where(MatchPair.job_id == job_id,
               MatchPair.needs_review.is_(True),
               MatchPair.status == status)
        .order_by(MatchPair.total_score.desc())
        .limit(limit).offset(offset)).all()

    raw_ids = [p.a_raw_id for p in pairs] + [p.b_raw_id for p in pairs]
    raws = {r.id: r for r in db.scalars(
        select(MaterialRaw).where(MaterialRaw.id.in_(raw_ids))).all()} if raw_ids else {}
    norms = _norm_map(db, raw_ids)

    out = []
    for p in pairs:
        ra, rb = raws.get(p.a_raw_id), raws.get(p.b_raw_id)
        if ra is None or rb is None:
            continue
        na, nb = norms.get(ra.id), norms.get(rb.id)
        f = _features(p)
        out.append({
            "pair_id": p.id, "total": p.total_score, "semantic": p.semantic,
            "lexical": p.lexical, "attr_agree": p.attr_agree,
            "attr_expected": f["attr_expected"],
            "conflict": p.conflict, "status": p.status,
            "a": member_dict(ra, na), "b": member_dict(rb, nb),
            "explanation": explain(_as_record(ra, na), _as_record(rb, nb), f),
        })
    return out


def _cluster_of_raw(db: Session, job_id: int, raw_id: int) -> Cluster | None:
    return db.scalars(
        select(Cluster).join(ClusterMember, ClusterMember.cluster_id == Cluster.id)
        .where(Cluster.job_id == job_id, ClusterMember.raw_id == raw_id)
        .limit(1)).first()


def decide_pair(db: Session, pair_id: int, action: str, reason: str | None,
                user: str) -> dict:
    pair = db.get(MatchPair, pair_id)
    if pair is None:
        raise ValueError(f"match pair {pair_id} not found")
    if pair.status != "open":
        raise ValueError(f"pair {pair_id} already {pair.status}")

    before = {"status": pair.status}
    pair.status = "approved" if action == "approve" else "rejected"
    db.add(Review(pair_id=pair.id, user=user, action=action, reason=reason))

    merged_into = None
    if action == "approve":
        ca = _cluster_of_raw(db, pair.job_id, pair.a_raw_id)
        cb = _cluster_of_raw(db, pair.job_id, pair.b_raw_id)
        if ca and cb and ca.id != cb.id:
            merged_into = merge_clusters(db, ca, cb, user=user)

    audit.record(db, "match_pair", pair.id, f"review_{action}", user=user,
                 before=before,
                 after={"status": pair.status, "reason": reason,
                        "merged_into_cnmc": merged_into})
    db.commit()
    return {"pair_id": pair.id, "status": pair.status,
            "merged_into_cnmc": merged_into}


def merge_clusters(db: Session, ca: Cluster, cb: Cluster, user: str) -> str | None:
    """Fold cb into ca (survivor = lower CNMC serial). Returns surviving CNMC."""
    ka = db.scalar(select(CanonicalMaterial)
                   .where(CanonicalMaterial.cluster_id == ca.id))
    kb = db.scalar(select(CanonicalMaterial)
                   .where(CanonicalMaterial.cluster_id == cb.id))
    if ka and kb and kb.cnmc < ka.cnmc:
        ca, cb, ka, kb = cb, ca, kb, ka          # keep the older code

    moved = db.scalars(select(ClusterMember)
                       .where(ClusterMember.cluster_id == cb.id)).all()
    for m in moved:
        m.cluster_id = ca.id
    ca.size = (ca.size or 0) + len(moved)
    ca.status = "approved"

    retired = kb.cnmc if kb else None
    if ka:
        moved_ids = [m.raw_id for m in moved]
        if moved_ids:
            for cm in db.scalars(select(CodeMapping)
                                 .where(CodeMapping.job_id == ca.job_id,
                                        CodeMapping.raw_id.in_(moved_ids))).all():
                cm.cnmc = ka.cnmc
        ka.n_members = ca.size
        ka.n_cpses = len({r for (r,) in db.execute(
            select(MaterialRaw.cpse_id)
            .join(ClusterMember, ClusterMember.raw_id == MaterialRaw.id)
            .where(ClusterMember.cluster_id == ca.id)).all() if r is not None})

    if kb:
        db.delete(kb)
    db.delete(cb)
    audit.record(db, "cluster", ca.id, "merge", user=user,
                 before={"retired_cnmc": retired},
                 after={"surviving_cnmc": ka.cnmc if ka else None,
                        "size": ca.size})
    return ka.cnmc if ka else None


def decide_cluster(db: Session, cluster_id: int, action: str,
                   reason: str | None, user: str) -> dict:
    cluster = db.get(Cluster, cluster_id)
    if cluster is None:
        raise ValueError(f"cluster {cluster_id} not found")

    before = {"status": cluster.status}
    cluster.status = "approved" if action == "approve" else "rejected"
    db.add(Review(cluster_id=cluster.id, user=user, action=action, reason=reason))
    audit.record(db, "cluster", cluster.id, f"review_{action}", user=user,
                 before=before, after={"status": cluster.status, "reason": reason})
    db.commit()
    return {"cluster_id": cluster.id, "status": cluster.status}


def _next_serial(db: Session, job_id: int, unspsc_code: str) -> int:
    """Next unused serial within a UNSPSC class (codes are never reused)."""
    used = db.scalars(
        select(CanonicalMaterial.cnmc)
        .where(CanonicalMaterial.job_id == job_id,
               CanonicalMaterial.unspsc_code == unspsc_code)).all()
    top = 0
    for code in used:
        parts = code.split("-")
        if len(parts) == 4 and parts[2].isdigit():
            top = max(top, int(parts[2]))
    return top + 1


def split_member(db: Session, cluster_id: int, raw_id: int, reason: str | None,
                 user: str) -> dict:
    """Pull one wrongly-merged row out into its own cluster with a FRESH CNMC."""
    member = db.scalar(select(ClusterMember)
                       .where(ClusterMember.cluster_id == cluster_id,
                              ClusterMember.raw_id == raw_id))
    if member is None:
        raise ValueError(f"row {raw_id} is not a member of cluster {cluster_id}")
    src = db.get(Cluster, cluster_id)

    new = Cluster(job_id=src.job_id, status="approved", size=1, confidence=1.0)
    db.add(new)
    db.flush()
    member.cluster_id = new.id
    src.size = max(1, (src.size or 1) - 1)

    ka = db.scalar(select(CanonicalMaterial)
                   .where(CanonicalMaterial.cluster_id == src.id))
    if ka:
        ka.n_members = src.size

    # the split-out row needs its own golden record + code, or its mapping
    # would still point at the family it was just removed from.
    raw = db.get(MaterialRaw, raw_id)
    norm = db.scalar(select(MaterialNorm).where(MaterialNorm.raw_id == raw_id))
    category = norm.category if norm else "OTHER"
    info = UNSPSC.get(category, UNSPSC["OTHER"])
    serial = _next_serial(db, src.job_id, info["code"])
    new_cnmc = make_cnmc(info["code"], serial)
    db.add(CanonicalMaterial(
        cluster_id=new.id, job_id=src.job_id, cnmc=new_cnmc, category=category,
        unspsc_code=info["code"], unspsc_title=info["title"],
        std_description=norm.clean_desc if norm else raw.description,
        uom=norm.uom_std if norm else (raw.uom or "EACH"),
        attributes=(norm.attributes if norm else {}) or {},
        n_members=1, n_cpses=1 if raw.cpse_id else 0))
    mapping = db.scalar(select(CodeMapping)
                        .where(CodeMapping.job_id == src.job_id,
                               CodeMapping.raw_id == raw_id))
    if mapping:
        mapping.cnmc = new_cnmc

    db.add(Review(cluster_id=cluster_id, user=user, action="split", reason=reason))
    audit.record(db, "cluster", cluster_id, "split", user=user,
                 after={"raw_id": raw_id, "new_cluster_id": new.id,
                        "new_cnmc": new_cnmc, "reason": reason})
    db.commit()
    return {"cluster_id": cluster_id, "split_raw_id": raw_id,
            "new_cluster_id": new.id, "new_cnmc": new_cnmc}
