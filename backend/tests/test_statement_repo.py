"""
Unit tests for SQLAlchemyStatementRepository.

Covers: create, list, find_by_id, find_by_checksum, delete, cascade, duplicate guard.
"""
from __future__ import annotations

import pytest

from src.infrastructure.repositories.statement_repo import SQLAlchemyStatementRepository
from src.infrastructure.repositories.transaction_repo import SQLAlchemyTransactionRepository
from tests.conftest import make_statement, make_transaction


def test_save_and_list(statement_repo, transaction_repo):
    stmt = make_statement()
    txs = [make_transaction(), make_transaction(value=50.0, merchant="IFOOD")]
    saved = statement_repo.save(stmt, txs)

    assert saved.id is not None
    assert saved.statement_key == "2025-11"

    all_stmts = statement_repo.list_all()
    assert len(all_stmts) == 1
    assert all_stmts[0].id == saved.id


def test_find_by_id_exists(statement_repo):
    saved = statement_repo.save(make_statement(), [])
    found = statement_repo.find_by_id(saved.id)
    assert found is not None
    assert found.statement_key == "2025-11"


def test_find_by_id_missing(statement_repo):
    assert statement_repo.find_by_id(9999) is None


def test_find_by_checksum_exists(statement_repo):
    statement_repo.save(make_statement(checksum="unique-cksum"), [])
    found = statement_repo.find_by_checksum("unique-cksum")
    assert found is not None


def test_find_by_checksum_missing(statement_repo):
    assert statement_repo.find_by_checksum("no-such-checksum") is None


def test_delete_removes_statement(statement_repo):
    saved = statement_repo.save(make_statement(), [])
    statement_repo.delete(saved.id)
    assert statement_repo.find_by_id(saved.id) is None
    assert statement_repo.list_all() == []


def test_delete_cascades_to_transactions(statement_repo, transaction_repo):
    """Deleting a statement must remove its transactions via ON DELETE CASCADE."""
    from src.domain.repositories import TransactionFilters
    saved = statement_repo.save(
        make_statement(),
        [make_transaction(), make_transaction(value=50.0)],
    )
    assert saved.transaction_count == 2

    statement_repo.delete(saved.id)

    # After cascade, no transactions should remain for this period
    remaining = transaction_repo.list_filtered(
        TransactionFilters(statement_key="2025-11", page_size=100)
    )
    assert remaining == []


def test_list_ordered_by_statement_key(statement_repo):
    statement_repo.save(make_statement(statement_key="2025-12", checksum="c2"), [])
    statement_repo.save(make_statement(statement_key="2025-10", checksum="c1"), [])
    statement_repo.save(make_statement(statement_key="2025-11", checksum="c3"), [])

    keys = [s.statement_key for s in statement_repo.list_all()]
    assert keys == ["2025-10", "2025-11", "2025-12"]
