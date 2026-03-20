"""
ListStatementsUseCase

Returns all imported statements ordered by statement_key ascending.
Includes the reconciliation diff (official_total - parsed_total) via
the ImportedStatement.diff property.
"""
from __future__ import annotations

from src.domain.entities import ImportedStatement
from src.domain.repositories import StatementRepository


class ListStatementsUseCase:
    def __init__(self, statement_repo: StatementRepository) -> None:
        self._statements = statement_repo

    def execute(self) -> list[ImportedStatement]:
        return self._statements.list_all()
