"""
read_service.py — query builders for the read-side endpoints (materials search,
cluster detail, the CNMC registry). Keeps routers thin and the joins in one place.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (CanonicalMaterial, Cluster, ClusterMember, CodeMapping,
                        Cpse, MaterialNorm, MaterialRaw)
from app.services.common import member_dict


def cnmc_by_raw(db: Session, job_id: int, raw_ids: list[int] | None = None) -> dict:
    q = select(CodeMapping.raw_id, CodeMapping.cnmc).where(CodeMapping.job_id == job_id)
    if raw_ids is not None:
        if not raw_ids:
            return {}
        q = q.where(CodeMapping.raw_id.in_(raw_ids))
    return {rid: cnmc for rid, cnmc in db.execute(q).all()}


def list_materials(db: Session, job_id: int | None, q: str | None,
                   category: str | None, cpse: str | None,
                   limit: int, offset: int) -> list[dict]:
    stmt = (select(MaterialRaw, MaterialNorm)
            .join(MaterialNorm, MaterialNorm.raw_id == MaterialRaw.id, isouter=True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(MaterialRaw.description.ilike(like),
                              MaterialNorm.clean_desc.ilike(like),
                              MaterialRaw.local_code.ilike(like)))
    if category:
        stmt = stmt.where(MaterialNorm.category == category)
    if cpse:
        stmt = stmt.join(Cpse, Cpse.id == MaterialRaw.cpse_id).where(Cpse.name == cpse)
    stmt = stmt.order_by(MaterialRaw.id).limit(limit).offset(offset)

    rows = db.execute(stmt).all()
    raw_ids = [r.MaterialRaw.id for r in rows]
    cnmc = cnmc_by_raw(db, job_id, raw_ids) if job_id else {}
    out = []
    for r in rows:
        raw, norm = r.MaterialRaw, r.MaterialNorm
        out.append({
            "id": raw.id,
            "cpse": raw.cpse.name if raw.cpse else None,
            "local_code": raw.local_code,
            "description": raw.description,
            "uom": raw.uom,
            "category_raw": raw.category_raw,
            "price": raw.price or 0.0,
            "clean_desc": norm.clean_desc if norm else None,
            "uom_std": norm.uom_std if norm else None,
            "category": norm.category if norm else None,
            "attributes": (norm.attributes if norm else {}) or {},
            "cnmc": cnmc.get(raw.id),
        })
    return out


def _members_of(db: Session, cluster_id: int) -> list[dict]:
    rows = db.execute(
        select(MaterialRaw, MaterialNorm)
        .join(ClusterMember, ClusterMember.raw_id == MaterialRaw.id)
        .join(MaterialNorm, MaterialNorm.raw_id == MaterialRaw.id, isouter=True)
        .where(ClusterMember.cluster_id == cluster_id)
        .order_by(MaterialRaw.id)).all()
    return [member_dict(r.MaterialRaw, r.MaterialNorm) for r in rows]


def build_cluster_out(db: Session, cluster: Cluster, with_members: bool = True) -> dict:
    canon = db.scalar(select(CanonicalMaterial)
                      .where(CanonicalMaterial.cluster_id == cluster.id))
    return {
        "id": cluster.id,
        "status": cluster.status,
        "size": cluster.size,
        "confidence": cluster.confidence,
        "canonical": canon,
        "members": _members_of(db, cluster.id) if with_members else [],
    }


def list_clusters(db: Session, job_id: int, status: str | None, multi_only: bool,
                  limit: int, offset: int) -> list[dict]:
    stmt = select(Cluster).where(Cluster.job_id == job_id)
    if status:
        stmt = stmt.where(Cluster.status == status)
    if multi_only:
        stmt = stmt.where(Cluster.size > 1)
    stmt = stmt.order_by(Cluster.size.desc(), Cluster.id).limit(limit).offset(offset)
    return [build_cluster_out(db, c) for c in db.scalars(stmt).all()]


def list_codes(db: Session, job_id: int, q: str | None, category: str | None,
               multi_only: bool, limit: int, offset: int) -> list[CanonicalMaterial]:
    stmt = select(CanonicalMaterial).where(CanonicalMaterial.job_id == job_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(CanonicalMaterial.cnmc.ilike(like),
                              CanonicalMaterial.std_description.ilike(like)))
    if category:
        stmt = stmt.where(CanonicalMaterial.category == category)
    if multi_only:
        stmt = stmt.where(CanonicalMaterial.n_members > 1)
    stmt = stmt.order_by(CanonicalMaterial.n_members.desc(),
                         CanonicalMaterial.cnmc).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def mappings_for_cnmc(db: Session, job_id: int, cnmc: str) -> list[dict]:
    rows = db.execute(
        select(CodeMapping, MaterialRaw, Cpse, CanonicalMaterial.category)
        .join(MaterialRaw, MaterialRaw.id == CodeMapping.raw_id)
        .join(Cpse, Cpse.id == MaterialRaw.cpse_id, isouter=True)
        .join(CanonicalMaterial, CanonicalMaterial.cnmc == CodeMapping.cnmc, isouter=True)
        .where(CodeMapping.job_id == job_id, CodeMapping.cnmc == cnmc)).all()
    return [{
        "cnmc": r.CodeMapping.cnmc,
        "cpse": r.Cpse.name if r.Cpse else None,
        "local_code": r.CodeMapping.local_code,
        "description": r.MaterialRaw.description,
        "category": r.category,
    } for r in rows]


def all_mappings(db: Session, job_id: int):
    """Full code-mapping table (for CSV export / ERP migration)."""
    return db.execute(
        select(CodeMapping.cnmc, Cpse.name, CodeMapping.local_code,
               MaterialRaw.description, CanonicalMaterial.std_description,
               CanonicalMaterial.unspsc_code)
        .join(MaterialRaw, MaterialRaw.id == CodeMapping.raw_id)
        .join(Cpse, Cpse.id == MaterialRaw.cpse_id, isouter=True)
        .join(CanonicalMaterial, CanonicalMaterial.cnmc == CodeMapping.cnmc, isouter=True)
        .where(CodeMapping.job_id == job_id)
        .order_by(CodeMapping.cnmc)).all()
