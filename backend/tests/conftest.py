"""
Shared test fixtures.

All tests use an in-memory SQLite database — no files written to disk.
PRAGMA foreign_keys=ON is enabled so ON DELETE CASCADE is enforced in tests.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.domain.entities import ImportedStatement, Transaction
from src.infrastructure.models import Base
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository
from src.infrastructure.repositories.statement_repo import SQLAlchemyStatementRepository
from src.infrastructure.repositories.transaction_repo import SQLAlchemyTransactionRepository


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def statement_repo(db_session: Session) -> SQLAlchemyStatementRepository:
    return SQLAlchemyStatementRepository(db_session)


@pytest.fixture()
def transaction_repo(db_session: Session) -> SQLAlchemyTransactionRepository:
    return SQLAlchemyTransactionRepository(db_session)


@pytest.fixture()
def settings_repo(db_session: Session) -> SQLAlchemySettingsRepository:
    return SQLAlchemySettingsRepository(db_session)


def make_statement(**overrides) -> ImportedStatement:
    """Factory for ImportedStatement entities with sensible defaults."""
    defaults = dict(
        statement_key="2025-11",
        statement_month="11",
        statement_year="2025",
        statement_label="Novembro/2025",
        source_file="2025-11.pdf",
        checksum="abc123",
        official_total=1000.0,
        parsed_total=1000.0,
        transaction_count=2,
        imported_at=datetime(2025, 11, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    return ImportedStatement(**defaults)


def make_transaction(statement_id: int = 0, **overrides) -> Transaction:
    """Factory for Transaction entities with sensible defaults."""
    defaults = dict(
        statement_id=statement_id,
        statement_key="2025-11",
        purchase_date="15/11",
        purchase_day="15",
        purchase_month="11",
        merchant="PANVEL MATRIZ",
        raw_merchant="PANVEL MATRIZ",
        value=31.98,
        category="Saúde",
        is_installment=False,
        installment_current=None,
        installment_total=None,
    )
    defaults.update(overrides)
    return Transaction(**defaults)
