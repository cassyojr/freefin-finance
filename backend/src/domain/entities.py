"""
Domain entities for the Extrato dashboard.

Rules:
- Pure Python only — no SQLAlchemy, no FastAPI, no Pydantic.
- Field names use the ubiquitous language defined in ARCHITECTURE.md.
- All entities are plain dataclasses; identity is carried by `id` (None = not yet persisted).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ImportedStatement:
    """
    Represents a single imported PDF statement.
    The PDF binary is NEVER stored — only derived metadata.
    """

    statement_key: str           # YYYY-MM  — canonical period identifier
    statement_month: str         # MM
    statement_year: str          # YYYY
    statement_label: str         # Human label, e.g. "Novembro/2025"
    source_file: str             # Original filename; no binary content
    checksum: str                # SHA-256 of uploaded bytes; enforces import-once
    official_total: float        # "Valor da fatura atual" extracted from PDF
    parsed_total: float          # Sum of all parsed transaction values
    transaction_count: int       # Convenience count
    imported_at: datetime        # UTC timestamp

    id: Optional[int] = field(default=None)

    @property
    def diff(self) -> float:
        """Difference between official total and parsed total (reconciliation aid)."""
        return round(self.official_total - self.parsed_total, 2)


@dataclass
class Transaction:
    """
    A single line item from a statement.
    Positive value = debit; negative value = credit or reversal.
    """

    statement_id: int            # FK → ImportedStatement.id
    statement_key: str           # Denormalised copy for query filters
    purchase_date: str           # DD/MM as-is from PDF
    purchase_day: str            # DD
    purchase_month: str          # MM
    merchant: str                # Cleaned name (installment notation stripped)
    raw_merchant: str            # Original extracted text
    value: float                 # BRL amount
    category: str                # Assigned category label
    is_installment: bool         # True when merchant contained NN/TT pattern
    installment_current: Optional[int]  # e.g. 2 from "02/06"
    installment_total: Optional[int]    # e.g. 6 from "02/06"

    id: Optional[int] = field(default=None)


@dataclass
class CategoryRule:
    """
    Keyword→category mapping rule.
    Custom user rules (is_default=False) have lower priority values and are
    evaluated before default rules.
    First match wins during categorisation.
    """

    keyword: str       # Case-insensitive substring
    category: str      # Target category label
    priority: int      # Lower = evaluated first
    is_default: bool   # False = user-added; True = seeded from DEFAULT_CATEGORY_RULES

    id: Optional[int] = field(default=None)


@dataclass
class FixedCost:
    """A recurring fixed monthly expense entry (mirrors localStorage key)."""

    label: str
    amount: float

    id: Optional[int] = field(default=None)


@dataclass
class FixedIncome:
    """A recurring fixed monthly income entry (mirrors localStorage key)."""

    label: str
    amount: float

    id: Optional[int] = field(default=None)
