"""Database session management and initialization."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from proceeds_navigator.db.models import Base

_DATABASE_URL: str | None = None
_engine = None
_SessionLocal: sessionmaker | None = None


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./data/proceeds_navigator.db")
    if url.startswith("sqlite:///./"):
        # Resolve relative SQLite paths to absolute
        data_dir = os.getenv("DATA_DIR", "./data")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        db_path = Path(data_dir) / "proceeds_navigator.db"
        return f"sqlite:///{db_path.resolve()}"
    return url


def get_engine():
    global _engine, _DATABASE_URL
    url = _get_database_url()
    if _engine is None or url != _DATABASE_URL:
        _DATABASE_URL = url
        kwargs = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        # Enable WAL mode for SQLite for better concurrency
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[misc]
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Session:
    """FastAPI dependency: yields a database session."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call multiple times (idempotent)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
