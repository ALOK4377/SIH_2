# Samanvay — SIH 2026 (PS 26099)

**AI-Driven Standardization & Harmonization of Material Codes Across CPSEs**
Ministry of Petroleum & Natural Gas → Chennai Petroleum Corporation Limited (CPCL) · Software · Smart Automation

An AI platform that finds duplicate / equivalent materials across many CPSEs' ERP/SAP systems, standardizes them, and assigns **One Nation–One Material Code** while keeping a mapping to each CPSE's original code.

## 📄 Start here
- **[docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md)** — what's built, how to run it, and how to verify it.
- **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** — full plan: solution, AI approach, tech stack, data model, roadmap, demo strategy, risks.
- **[docs/diagrams/flowcharts.html](docs/diagrams/flowcharts.html)** — rendered flowcharts (open in a browser).

## Quickstart

```bash
cp .env.example .env
docker compose up --build      # → http://localhost:5173  (API docs: http://localhost:8000/docs)
```

No Docker? See [BUILD_GUIDE §5](docs/BUILD_GUIDE.md#5-run-it-on-your-machine) for the SQLite + local-dev flow. To see the AI accuracy with zero installs:

```bash
python3 scripts/run_pipeline.py
```

## Measured results (synthetic benchmark)
**1,274** local codes across **10 CPSEs** → **435** national codes (**65.9%** reduction) · precision **90.2%** · recall **80.5%** · F1 **85.1%** — recomputed from ground truth on every run.

## Stack
React + Vite + TypeScript · FastAPI + SQLAlchemy 2.0 · SQLite (default) / PostgreSQL 16 + pgvector · Docker Compose. Heavy ML (sentence-transformers, RapidFuzz, Celery/Redis) slots in via documented upgrade points.

## Status
✅ Full stack built — AI pipeline, CNMC codes, review API, and React UI. Remaining (P4): JWT auth, SAP adapter, demo polish.
