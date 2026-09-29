# Samanvay — Build Guide & Progress Tracker

> **What this document is:** a step-by-step map from the flowchart to the actual
> build, showing exactly which nodes are done and how to run and verify the
> whole thing on your machine.

**Legend:** ✅ done · 🚧 in progress · ⬜ not started · 🔒 needs your local machine (can't run in the build sandbox)

---

## 📍 YOU ARE HERE

```
P0 Foundations ✅ ─► P1 Matching MVP ✅ ─► P2 Codes + Review + API ✅ ─► [P3 Dashboard + UI ✅] ─► P4 Auth + SAP + polish ⬜
                                                                            ▲ full stack is built
```

The AI matching engine, the CNMC code system, the persistence + review API
(FastAPI + SQLAlchemy), and the React dashboard/review/registry UI are all
built. What remains (P4) is authentication, a SAP/ERP adapter, and demo polish.

**Measured accuracy on the synthetic benchmark** (`python3 scripts/run_pipeline.py`,
pure standard-library, no installs):

```
  1,274 raw codes  (10 CPSEs, 350 true item groups)
        ->  435 national codes            (65.9% catalogue reduction)

  precision : 90.2%   (TP 1,758 · FP 190)      default gate 0.70
  recall    : 80.5%   (FN 426)
  F1        : 85.1%
  blocking recall ceiling : 97.9%   (85.4% fewer pairs to score)
  groups recovered exactly: 228 / 350
  873 uncertain pairs routed to human review

  precision-first operating point (gate 0.76): 96.9% precision · 77.5% recall · 86.1% F1
```

Numbers are recomputed from ground truth on every run — they are measured, not claimed.

---

## 1. The AI Pipeline — Flowchart 5B (the core engine)

Every node is a real module under [`backend/app/ml/`](backend/app/ml).

| # | Flowchart node | Module | Status |
|---|----------------|--------|--------|
| 1 | Ingest raw rows | [`pipeline.py`](backend/app/ml/pipeline.py) + [`gen_synthetic_data.py`](scripts/gen_synthetic_data.py) | ✅ |
| 2 | Normalize / UOM / abbreviations / spec extraction | [`normalize.py`](backend/app/ml/normalize.py) | ✅ |
| 3 | Embed (TF-IDF; MiniLM drops in) | [`embed.py`](backend/app/ml/embed.py) | ✅ |
| 4 | Block by category + neighbours | [`block.py`](backend/app/ml/block.py) | ✅ |
| 5 | Score = attribute 0.60 + semantic 0.25 + lexical 0.15, conflict veto | [`score.py`](backend/app/ml/score.py) | ✅ |
| 6 | Threshold → auto / review / discard | [`pipeline.py`](backend/app/ml/pipeline.py) | ✅ |
| 7 | Constraint-aware clustering (cannot-link, strongest-first) | [`cluster.py`](backend/app/ml/cluster.py) | ✅ |
| 8 | Golden record + CNMC `IN-CCCCCC-NNNNNNN-K` (mod-11) | [`canonical.py`](backend/app/ml/canonical.py) | ✅ |
| 9 | Explainable match reason | [`explain.py`](backend/app/ml/explain.py) | ✅ |
| 10 | Metrics: precision / recall / F1 | [`evaluate.py`](backend/app/ml/evaluate.py) | ✅ |

---

## 2. System Architecture — Flowchart 5A (the full product)

| Layer | Component | Status | Notes |
|-------|-----------|--------|-------|
| Data | Synthetic generator + reference dictionaries | ✅ | [`data/`](data) — 1,274 rows, 350 groups, hard negatives |
| ML | Matching pipeline + evaluation | ✅ | offline, zero installs |
| API | FastAPI app — 9 routers, services, DTOs | ✅ | [`backend/app`](backend/app); wraps the pipeline, persists everything |
| DB | SQLAlchemy 2.0 models, auto-create on startup | ✅ | SQLite by default; Postgres 16 + pgvector via env |
| Frontend | React + Vite + TS: dashboard, ingest, review, families, registry, audit | ✅ | [`frontend/src`](frontend/src) |
| Workers | Celery + Redis (async batch matching) | ⬜ | pipeline runs synchronously today; documented scale path |
| Security | JWT auth + role-based access | ⬜ | `User` model exists; auth routes are P4 |
| Integration | SAP/ERP adapter | ⬜ | P4 |
| Ops | Docker / docker-compose | ✅ | [`docker-compose.yml`](docker-compose.yml), backend + frontend Dockerfiles |

---

## 3. Steward Review Workflow — Flowchart 5C (human-in-the-loop)

| Step | Component | Status |
|------|-----------|--------|
| Explanation per decision | [`explain.py`](backend/app/ml/explain.py) | ✅ |
| Review queue (uncertain pairs) | [`review_service.py`](backend/app/services/review_service.py) → `/review/queue` | ✅ |
| Review UI: approve / reject a pair or a family | [`Review.tsx`](frontend/src/pages/Review.tsx), [`Clusters.tsx`](frontend/src/pages/Clusters.tsx) | ✅ |
| Apply decision → merge / split canonical records | [`review_service.py`](backend/app/services/review_service.py) | ✅ |
| Audit log (who / what / when / why) | [`audit.py`](backend/app/services/audit.py) → `/audit` | ✅ |
| Feed confirmed decisions back to model | `Review` rows are the label store | 🚧 (labels captured; retraining is P4) |

---

## 4. Phase Roadmap

- [x] **P0 — Foundations** ✅
- [x] **P1 — Matching MVP** ✅
- [x] **P2 — Golden records + CNMC + review persistence + FastAPI** ✅
- [x] **P3 — Dashboard + review UI + code registry** ✅
- [ ] **P4 — SAP integration + JWT auth + Celery + demo polish** ⬜

---

## 5. Run it on your machine

Two ways. The sandbox this was built in has no pip/npm/Docker, so these are
**for your local machine** — the code is written and syntax-checked, but you run it.

### A. One command — Docker (Postgres + backend + frontend)

```bash
cp .env.example .env
docker compose up --build
```

Then open **http://localhost:5173**. On first boot the backend seeds the
synthetic catalogue and runs the pipeline automatically, so the dashboard has
data immediately. API docs live at **http://localhost:8000/docs**.

### B. No Docker — SQLite + local dev servers

**Backend** (Python 3.11+):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/seed_db.py          # creates backend/samanvay.db, seeds + runs the pipeline
cd backend && uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 20+), in a second terminal:

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

The frontend reads the API base from `VITE_API_BASE` (defaults to
`http://localhost:8000/api`).

### What still runs with zero installs

```bash
python3 scripts/gen_synthetic_data.py   # regenerate the dirty dataset
python3 scripts/run_pipeline.py          # run matching + print REAL metrics
```

---

## 6. How to verify it works

1. **Metrics are real.** `python3 scripts/run_pipeline.py` prints precision /
   recall / F1 recomputed from ground truth, plus a threshold sweep. No DB or
   installs needed.
2. **API is live.** With the backend running, open `http://localhost:8000/docs`
   and try `GET /api/analytics/summary` — it returns the duplication rate and
   the P/R/F1 for the seeded job.
3. **UI is wired end-to-end.** At `http://localhost:5173`: the **Dashboard**
   shows 1,274 → 435 with the quality numbers; **Ingest & Run** re-runs the
   pipeline on demand; **Review Queue** shows explained borderline pairs you can
   approve/reject; **Families** and **Code Registry** browse the golden records
   and the local-code crosswalk; **Export CSV** downloads the full mapping
   table; **Audit Trail** logs every decision.
4. **De-duplication is honest.** Open any multi-CPSE family — e.g. bearing
   `6205` and `6206` stay in *separate* codes, and `150#` vs `300#` gaskets are
   never merged, because the attribute veto blocks physically-different items.

---

## 7. Where the heavy libraries plug in (documented upgrades)

| Today (offline, proven) | Production upgrade | Touch point |
|-------------------------|--------------------|-------------|
| TF-IDF char-n-gram vectors | `sentence-transformers` MiniLM | [`embed.py`](backend/app/ml/embed.py) |
| Exact category blocking | pgvector ANN | [`block.py`](backend/app/ml/block.py) |
| `difflib` lexical ratio | RapidFuzz | [`score.py`](backend/app/ml/score.py) |
| Fixed score weights | classifier trained on review labels | [`score.py`](backend/app/ml/score.py) |
| Synchronous run | Celery + Redis | [`pipeline_service.py`](backend/app/services/pipeline_service.py) |
| SQLite | Postgres 16 + pgvector | `SAMANVAY_DATABASE_URL` env |
