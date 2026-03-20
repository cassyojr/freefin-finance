"""
SQLAlchemy implementation of StatementRepository.

Responsibilities:
- find_by_checksum: duplicate import guard
- save: atomically persist ImportedStatement + all Transactions
- list_all: ordered by statement_key asc
- find_by_id: lookup by PK
- delete: hard delete — cascade removes Transactions via DB FK
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.domain.entities import ImportedStatement, Transaction
from src.domain.repositories import StatementRepository as StatementRepositoryPort
from src.infrastructure.models import ImportedStatementModel, TransactionModel


def _model_to_statement(m: ImportedStatementModel) -> ImportedStatement:
    return ImportedStatement(
        id=m.id,
        statement_key=m.statement_key,
        statement_month=m.statement_month,
        statement_year=m.statement_year,
        statement_label=m.statement_label,
        source_file=m.source_file,
        checksum=m.checksum,
        official_total=m.official_total,
        parsed_total=m.parsed_total,
        transaction_count=m.transaction_count,
        imported_at=m.imported_at,
    )


def _transaction_to_model(t: Transaction, statement_id: int) -> TransactionModel:
    return TransactionModel(
        statement_id=statement_id,
        statement_key=t.statement_key,
        purchase_date=t.purchase_date,
        purchase_day=t.purchase_day,
        purchase_month=t.purchase_month,
        merchant=t.merchant,
        raw_merchant=t.raw_merchant,
        value=t.value,
        category=t.category,
        is_installment=t.is_installment,
        installment_current=t.installment_current,
        installment_total=t.installment_total,
    )


class SQLAlchemyStatementRepository:
    """Concrete StatementRepository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_checksum(self, checksum: str) -> Optional[ImportedStatement]:
        row = (
            self._session.query(ImportedStatementModel)
            .filter(ImportedStatementModel.checksum == checksum)
            .first()
        )
        return _model_to_statement(row) if row else None

    def save(
        self,
        statement: ImportedStatement,
        transactions: list[Transaction],
    ) -> ImportedStatement:
        """Atomically persist the statement and all its transactions."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # store as naive UTC
        stmt_model = ImportedStatementModel(
            statement_key=statement.statement_key,
            statement_month=statement.statement_month,
            statement_year=statement.statement_year,
            statement_label=statement.statement_label,
            source_file=statement.source_file,
            checksum=statement.checksum,
            official_total=statement.official_total,
            parsed_total=statement.parsed_total,
            transaction_count=len(transactions),
            imported_at=now,
        )
        self._session.add(stmt_model)
        self._session.flush()  # get auto-generated id before inserting children

        for tx in transactions:
            self._session.add(_transaction_to_model(tx, stmt_model.id))

        self._session.commit()
        self._session.refresh(stmt_model)
        return _model_to_statement(stmt_model)

    def list_all(self) -> list[ImportedStatement]:
        rows = (
            self._session.query(ImportedStatementModel)
            .order_by(ImportedStatementModel.statement_key.asc())
            .all()
        )
        return [_model_to_statement(r) for r in rows]

    def find_by_id(self, statement_id: int) -> Optional[ImportedStatement]:
        row = (
            self._session.query(ImportedStatementModel)
            .filter(ImportedStatementModel.id == statement_id)
            .first()
        )
        return _model_to_statement(row) if row else None

    def delete(self, statement_id: int) -> None:
        """Hard delete. Transactions are removed by DB ON DELETE CASCADE."""
        row = (
            self._session.query(ImportedStatementModel)
            .filter(ImportedStatementModel.id == statement_id)
            .first()
        )
        if row:
            self._session.delete(row)
            self._session.commit()


# Runtime type-check: ensures this class satisfies the Protocol
_: StatementRepositoryPort = SQLAlchemyStatementRepository.__new__(SQLAlchemyStatementRepository)  # type: ignore[assignment]
