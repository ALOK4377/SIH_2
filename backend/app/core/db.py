"""
db.py — SQLAlchemy 2.0 engine, session factory, and declarative Base.

Works against SQLite (default) or PostgreSQL (docker-compose) with the same
models. `check_same_thread=False` is only needed for SQLite under the threaded
FastAPI server. Tables are created on startup via `init_db()` (Alembic is the
documented upgrade path for real migrations — see docs/PROJECT_PLAN §6).
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, echo=False, future=True,
                       connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False,
                            class_=Session)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables. Import models first so they register on Base.metadata."""
    from app import models  # noqa: F401  (side-effect: registers mappers)
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
