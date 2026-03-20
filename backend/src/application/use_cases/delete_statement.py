"""
DeleteStatementUseCase

Flow:
1. Verify the statement exists — raise StatementNotFoundError if not.
2. Hard-delete via StatementRepository.delete().
   DB ON DELETE CASCADE removes all associated Transaction rows automatically.
"""
from __future__ import annotations

from src.domain.repositories import StatementRepository


class StatementNotFoundError(Exception):
    """Raised when the requested statement id does not exist."""


class DeleteStatementUseCase:
    def __init__(self, statement_repo: StatementRepository) -> None:
        self._statements = statement_repo

    def execute(self, statement_id: int) -> None:
        if not self._statements.find_by_id(statement_id):
            raise StatementNotFoundError(f"Statement id={statement_id} not found.")
        self._statements.delete(statement_id)
