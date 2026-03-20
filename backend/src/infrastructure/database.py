"""
SQLAlchemy engine and session factory.

Usage:
    from src.infrastructure.database import get_session, init_db

- The default DB file lives at backend/data/extrato.db.
- Pass DATABASE_URL as an env var to override (useful in tests with sqlite:///:memory:).
- Call init_db() once at startup to create all tables.
"""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.models import Base

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "extrato.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")

# check_same_thread=False is required for SQLite when using FastAPI's async request cycle
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    """Enable WAL mode and foreign key enforcement for every SQLite connection."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    """Create all tables if they do not exist. Safe to call on every startup."""
    _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and guarantees cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
