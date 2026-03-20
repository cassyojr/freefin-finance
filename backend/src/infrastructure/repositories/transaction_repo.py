"""
SQLAlchemy implementation of TransactionRepository.

Supports server-side filtering, sorting, and pagination matching
the GET /transactions query parameters defined in ARCHITECTURE.md.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.entities import Transaction
from src.domain.repositories import TransactionFilters, TransactionRepository as TransactionRepositoryPort
from src.infrastructure.models import TransactionModel

_SORTABLE_COLUMNS = {
    "purchase_date": TransactionModel.purchase_date,
    "merchant":      TransactionModel.merchant,
    "value":         TransactionModel.value,
    "category":      TransactionModel.category,
}


def _model_to_transaction(m: TransactionModel) -> Transaction:
    return Transaction(
        id=m.id,
        statement_id=m.statement_id,
        statement_key=m.statement_key,
        purchase_date=m.purchase_date,
        purchase_day=m.purchase_day,
        purchase_month=m.purchase_month,
        merchant=m.merchant,
        raw_merchant=m.raw_merchant,
        value=m.value,
        category=m.category,
        is_installment=m.is_installment,
        installment_current=m.installment_current,
        installment_total=m.installment_total,
    )


class SQLAlchemyTransactionRepository:
    """Concrete TransactionRepository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_filtered(self, filters: TransactionFilters) -> list[Transaction]:
        query = self._session.query(TransactionModel)

        if filters.statement_key:
            query = query.filter(TransactionModel.statement_key == filters.statement_key)
        if filters.category:
            query = query.filter(TransactionModel.category == filters.category)
        if filters.purchase_month:
            query = query.filter(TransactionModel.purchase_month == filters.purchase_month)
        if filters.min_value is not None:
            query = query.filter(TransactionModel.value >= filters.min_value)
        if filters.max_value is not None:
            query = query.filter(TransactionModel.value <= filters.max_value)
        if filters.credits_only:
            query = query.filter(TransactionModel.value < 0)

        sort_col = _SORTABLE_COLUMNS.get(filters.sort_col, TransactionModel.purchase_date)
        if filters.sort_dir == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        return [_model_to_transaction(r) for r in query.all()]


# Runtime type-check
_: TransactionRepositoryPort = SQLAlchemyTransactionRepository.__new__(SQLAlchemyTransactionRepository)  # type: ignore[assignment]
