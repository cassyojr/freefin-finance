"""
Repository interfaces (Protocols) for the domain layer.

Rules:
- Live in the domain layer — no SQLAlchemy, no FastAPI imports here.
- Concrete implementations belong exclusively in infrastructure/repositories/.
- Use cases import only from this module, never from infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from src.domain.entities import (
    CategoryRule,
    FixedCost,
    FixedIncome,
    ImportedStatement,
    Transaction,
)


@dataclass
class TransactionFilters:
    """Value object carrying all optional query constraints for transaction listing."""

    statement_key: Optional[str] = None    # Filter to a single YYYY-MM period
    category: Optional[str] = None         # Exact category match
    purchase_month: Optional[str] = None   # MM filter (cross-period)
    min_value: Optional[float] = None      # Inclusive lower bound (BRL)
    max_value: Optional[float] = None      # Inclusive upper bound (BRL)
    credits_only: bool = False             # Negative values only
    sort_col: str = "purchase_date"        # Field name to sort by
    sort_dir: str = "desc"                 # "asc" | "desc"
    page: int = 1
    page_size: int = 20


class StatementRepository(Protocol):
    """Port for statement persistence."""

    def find_by_checksum(self, checksum: str) -> Optional[ImportedStatement]:
        """Return the statement whose checksum matches, or None."""
        ...

    def save(
        self,
        statement: ImportedStatement,
        transactions: list[Transaction],
    ) -> ImportedStatement:
        """
        Atomically persist a statement and all its transactions.
        Returns the statement with its assigned `id`.
        """
        ...

    def list_all(self) -> list[ImportedStatement]:
        """Return all statements ordered by statement_key ascending."""
        ...

    def find_by_id(self, statement_id: int) -> Optional[ImportedStatement]:
        """Return the statement with the given id, or None."""
        ...

    def delete(self, statement_id: int) -> None:
        """
        Hard-delete the statement.
        Associated Transaction rows are removed via DB cascade — no separate
        transaction deletion step is needed here.
        """
        ...


class TransactionRepository(Protocol):
    """Port for transaction querying."""

    def list_filtered(self, filters: TransactionFilters) -> list[Transaction]:
        """Return transactions matching the given filters."""
        ...


class SettingsRepository(Protocol):
    """Port for user-configurable settings (mirrors localStorage categories)."""

    def get_category_rules(self) -> list[CategoryRule]:
        """Return rules ordered by priority ascending (lower value = higher priority)."""
        ...

    def save_category_rules(self, rules: list[CategoryRule]) -> None:
        """Replace all category rules atomically."""
        ...

    def get_fixed_costs(self) -> list[FixedCost]:
        """Return all fixed cost entries."""
        ...

    def save_fixed_costs(self, costs: list[FixedCost]) -> None:
        """Replace all fixed cost entries atomically."""
        ...

    def get_fixed_income(self) -> list[FixedIncome]:
        """Return all fixed income entries."""
        ...

    def save_fixed_income(self, income: list[FixedIncome]) -> None:
        """Replace all fixed income entries atomically."""
        ...
