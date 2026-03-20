"""
Unit tests for DeleteStatementUseCase.

Covers: success path, not-found error, cascade confirmed.
"""
from __future__ import annotations

import pytest

from src.application.use_cases.delete_statement import (
    DeleteStatementUseCase,
    StatementNotFoundError,
)
from src.domain.repositories import TransactionFilters
from tests.conftest import make_statement, make_transaction


def test_delete_success(statement_repo):
    saved = statement_repo.save(make_statement(), [])

    use_case = DeleteStatementUseCase(statement_repo)
    use_case.execute(saved.id)

    assert statement_repo.find_by_id(saved.id) is None


def test_delete_not_found_raises(statement_repo):
    use_case = DeleteStatementUseCase(statement_repo)
    with pytest.raises(StatementNotFoundError):
        use_case.execute(9999)


def test_delete_cascade_confirmed(statement_repo, transaction_repo):
    """Deleting a statement via use case must cascade-delete all transactions."""
    saved = statement_repo.save(
        make_statement(),
        [make_transaction(value=10.0), make_transaction(value=20.0)],
    )

    use_case = DeleteStatementUseCase(statement_repo)
    use_case.execute(saved.id)

    remaining = transaction_repo.list_filtered(
        TransactionFilters(statement_key="2025-11", page_size=100)
    )
    assert remaining == []
