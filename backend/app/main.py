"""
main.py — Samanvay FastAPI application.

    uvicorn app.main:app --reload            # from the backend/ directory

Auto-creates tables on startup (SQLite by default → no external services
needed). Interactive API docs at /docs. All routes are mounted under /api.

Quick demo, once running:
    curl -X POST localhost:8000/api/ingest/load-synthetic
    curl -X POST localhost:8000/api/pipeline/run -H 'content-type: application/json' -d '{"batch_id":1}'
    curl localhost:8000/api/analytics/summary
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (routes_analytics, routes_audit, routes_clusters,
                     routes_codes, routes_health, routes_ingest,
                     routes_materials, routes_pipeline, routes_review)
from app.core.config import get_settings
from app.core.db import init_db

settings = get_settings()

app = FastAPI(
    title=f"{settings.app_name} API",
    description="AI-driven standardization & de-duplication of CPSE material "
                "codes → one Common National Material Code (CNMC) per item, "
                "with full traceability and human-in-the-loop review.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", tags=["health"])
def root():
    return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}


_P = settings.api_prefix
for module in (routes_health, routes_ingest, routes_pipeline, routes_materials,
               routes_clusters, routes_codes, routes_review, routes_analytics,
               routes_audit):
    app.include_router(module.router, prefix=_P)
