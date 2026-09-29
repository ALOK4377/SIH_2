"""
dto.py — Pydantic request/response schemas (the API's public contract).

Kept separate from ORM models so the wire format can evolve independently.
`from_attributes=True` lets these read straight off SQLAlchemy row objects.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- ingest / jobs -------------------------------------------------------
class BatchOut(_ORM):
    id: int
    name: str
    source_file: str | None
    n_rows: int
    created_at: datetime


class JobOut(_ORM):
    id: int
    batch_id: int
    status: str
    params: dict
    metrics: dict
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class RunRequest(BaseModel):
    batch_id: int
    auto_threshold: float | None = None
    review_low: float | None = None


# ---- materials -----------------------------------------------------------
class MaterialOut(_ORM):
    id: int
    cpse: str | None = None
    local_code: str
    description: str
    uom: str | None = None
    category_raw: str | None = None
    price: float = 0.0
    clean_desc: str | None = None
    uom_std: str | None = None
    category: str | None = None
    attributes: dict = {}
    cnmc: str | None = None


# ---- clusters / canonicals / codes --------------------------------------
class MemberOut(BaseModel):
    raw_id: int
    cpse: str | None = None
    local_code: str
    description: str
    clean_desc: str | None = None
    price: float = 0.0


class CanonicalOut(_ORM):
    id: int
    cluster_id: int
    cnmc: str
    category: str
    unspsc_code: str
    unspsc_title: str
    std_description: str
    uom: str
    attributes: dict = {}
    n_members: int
    n_cpses: int


class ClusterOut(BaseModel):
    id: int
    status: str
    size: int
    confidence: float
    canonical: CanonicalOut | None = None
    members: list[MemberOut] = []


class CodeMappingOut(BaseModel):
    cnmc: str
    cpse: str | None = None
    local_code: str
    description: str
    category: str | None = None


# ---- review --------------------------------------------------------------
class ReviewPairOut(BaseModel):
    pair_id: int
    total: float
    semantic: float
    lexical: float
    attr_agree: int
    attr_expected: int = 3
    conflict: bool
    status: str
    a: MemberOut
    b: MemberOut
    explanation: str


class DecisionIn(BaseModel):
    action: str            # approve | reject
    reason: str | None = None
    user: str = "steward"


# ---- analytics / audit ---------------------------------------------------
class CategoryStat(BaseModel):
    category: str
    raw: int
    canonical: int


class AnalyticsSummary(BaseModel):
    total_raw: int
    total_canonical: int
    duplicate_rows: int
    duplication_rate: float          # fraction of rows that were duplicates
    clusters_multi: int
    clusters_total: int
    review_pending: int
    potential_savings: float         # ₹ estimate from demand aggregation
    by_category: list[CategoryStat]
    by_cpse: dict[str, int]
    metrics: dict = {}               # precision/recall/F1 if ground truth present


class AuditOut(_ORM):
    id: int
    entity: str
    entity_id: int | None
    action: str
    user: str
    created_at: datetime
