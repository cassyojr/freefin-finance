"""
ListTransactionsUseCase

Delegates all filtering, sorting, and pagination to the TransactionRepository
so no large result sets are loaded into memory at the application layer.
"""
from __future__ import annotations

from src.domain.entities import Transaction
from src.domain.repositories import TransactionFilters, TransactionRepository


class ListTransactionsUseCase:
    def __init__(self, transaction_repo: TransactionRepository) -> None:
        self._transactions = transaction_repo

    def execute(self, filters: TransactionFilters) -> list[Transaction]:
        return self._transactions.list_filtered(filters)
