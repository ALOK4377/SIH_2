"""
entities.py — SQLAlchemy ORM models (the data model from PROJECT_PLAN §7.2).

The graph, end to end:

  Cpse ─┐
        ├─< MaterialRaw >── MaterialNorm            (ingested + normalized rows)
Batch ─┘         │
                 ├─< ClusterMember >── Cluster       (proposed material families)
                 │                        │
                 │                   CanonicalMaterial (golden record + CNMC)
                 └─< CodeMapping (local_code → CNMC, traceability)
  Job ─ groups one pipeline run's MatchPair / Cluster / Canonical / CodeMapping
  Review + AuditLog ─ human-in-the-loop decisions and governance trail

Embeddings are intentionally NOT stored here: the shipped engine uses a sparse
TF-IDF space (see app/ml/embed.py). The pgvector `embedding vector(384)` column
from the plan is the documented upgrade path once sentence-transformers is on.
All JSON columns use SQLAlchemy's generic JSON type → identical on SQLite/PG.
"""
from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="STEWARD")  # STEWARD|ADMIN|VIEWER


class Cpse(Base):
    __tablename__ = "cpse"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(60), nullable=True)


class Batch(Base):
    """One ingestion of material-master rows (a CSV upload or the demo dataset)."""
    __tablename__ = "batch"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    source_file: Mapped[str | None] = mapped_column(String(300), nullable=True)
    n_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Job(Base):
    """One end-to-end pipeline run over a batch. Holds the operating point + metrics."""
    __tablename__ = "job"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|failed
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MaterialRaw(Base):
    __tablename__ = "material_raw"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"), index=True)
    cpse_id: Mapped[int | None] = mapped_column(ForeignKey("cpse.id"), nullable=True, index=True)
    local_code: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str] = mapped_column(Text)
    uom: Mapped[str | None] = mapped_column(String(30), nullable=True)
    category_raw: Mapped[str | None] = mapped_column(String(60), nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    source_file: Mapped[str | None] = mapped_column(String(300), nullable=True)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ground-truth (if provided)

    cpse: Mapped["Cpse | None"] = relationship(lazy="joined")
    norm: Mapped["MaterialNorm | None"] = relationship(back_populates="raw", uselist=False)


class MaterialNorm(Base):
    __tablename__ = "material_norm"
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("material_raw.id"), unique=True, index=True)
    clean_desc: Mapped[str] = mapped_column(Text)
    uom_std: Mapped[str] = mapped_column(String(30))
    category: Mapped[str] = mapped_column(String(30), index=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)

    raw: Mapped["MaterialRaw"] = relationship(back_populates="norm")


class MatchPair(Base):
    """A scored candidate pair. `needs_review` rows are the ambiguous band."""
    __tablename__ = "match_pair"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    a_raw_id: Mapped[int] = mapped_column(ForeignKey("material_raw.id"), index=True)
    b_raw_id: Mapped[int] = mapped_column(ForeignKey("material_raw.id"), index=True)
    semantic: Mapped[float] = mapped_column(Float)
    lexical: Mapped[float] = mapped_column(Float)
    attr_agree: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Float, index=True)
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|approved|rejected
    features: Mapped[dict] = mapped_column(JSON, default=dict)


class Cluster(Base):
    __tablename__ = "cluster"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)  # proposed|approved|rejected
    size: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    members: Mapped[list["ClusterMember"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan")
    canonical: Mapped["CanonicalMaterial | None"] = relationship(
        back_populates="cluster", uselist=False, cascade="all, delete-orphan")


class ClusterMember(Base):
    __tablename__ = "cluster_member"
    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("cluster.id"), index=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("material_raw.id"), index=True)

    cluster: Mapped["Cluster"] = relationship(back_populates="members")


class CanonicalMaterial(Base):
    __tablename__ = "canonical_material"
    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("cluster.id"), unique=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    cnmc: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    unspsc_code: Mapped[str] = mapped_column(String(10))
    unspsc_title: Mapped[str] = mapped_column(String(120))
    std_description: Mapped[str] = mapped_column(Text)
    uom: Mapped[str] = mapped_column(String(30))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    n_members: Mapped[int] = mapped_column(Integer, default=1)
    n_cpses: Mapped[int] = mapped_column(Integer, default=1)

    cluster: Mapped["Cluster"] = relationship(back_populates="canonical")


class CodeMapping(Base):
    """Traceability: every original (CPSE, local_code) → its assigned CNMC."""
    __tablename__ = "code_mapping"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    cnmc: Mapped[str] = mapped_column(String(30), index=True)
    cpse_id: Mapped[int | None] = mapped_column(ForeignKey("cpse.id"), nullable=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("material_raw.id"), index=True)
    local_code: Mapped[str] = mapped_column(String(60))
    __table_args__ = (UniqueConstraint("job_id", "raw_id", name="uq_mapping_job_raw"),)


class Review(Base):
    __tablename__ = "review"
    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("cluster.id"), nullable=True)
    pair_id: Mapped[int | None] = mapped_column(ForeignKey("match_pair.id"), nullable=True)
    user: Mapped[str] = mapped_column(String(120), default="steward")
    action: Mapped[str] = mapped_column(String(20))  # approve|reject|split
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    user: Mapped[str] = mapped_column(String(120), default="steward")
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
