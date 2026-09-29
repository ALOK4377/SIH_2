"""
config.py — application settings.

Everything is env-overridable. The defaults are chosen so the backend RUNS WITH
ZERO CONFIG: SQLite file DB, permissive CORS for the Vite dev server, and the
repo's bundled synthetic dataset as the demo source. Point DATABASE_URL at
Postgres (see docker-compose.yml) for the full pgvector-capable deployment.
"""
from functools import lru_cache
from pathlib import Path

try:                                   # pydantic v2 split settings into a package
    from pydantic_settings import BaseSettings
except ImportError:                    # fallback for older pydantic
    from pydantic import BaseSettings  # type: ignore

# repo root = .../sih2  (this file is backend/app/core/config.py → parents[3])
ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Samanvay"
    api_prefix: str = "/api"

    # SQLite by default → no Docker/Postgres needed to try the API.
    # docker-compose overrides with: postgresql+psycopg://samanvay:...@db:5432/samanvay
    database_url: str = f"sqlite:///{ROOT / 'backend' / 'samanvay.db'}"

    # CORS: Vite dev server + common local origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # Where the bundled demo data + reference dictionaries live.
    data_dir: str = str(ROOT / "data")
    synthetic_dir: str = str(ROOT / "data" / "synthetic")

    # Pipeline operating point (mirrors app.ml.pipeline defaults).
    auto_threshold: float = 0.70
    review_low: float = 0.50

    class Config:
        env_file = ".env"
        env_prefix = "SAMANVAY_"
        extra = "ignore"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
