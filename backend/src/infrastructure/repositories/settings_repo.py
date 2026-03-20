"""
SQLAlchemy implementation of SettingsRepository.

Manages category rules, fixed costs, and fixed income — all stored in DB
instead of localStorage. Replace-all semantics for each collection: the
caller owns the full list; we delete-and-reinsert atomically.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.entities import CategoryRule, FixedCost, FixedIncome
from src.domain.repositories import SettingsRepository as SettingsRepositoryPort
from src.infrastructure.models import CategoryRuleModel, FixedCostModel, FixedIncomeModel


class SQLAlchemySettingsRepository:
    """Concrete SettingsRepository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Category rules ────────────────────────────────────────────────────────

    def get_category_rules(self) -> list[CategoryRule]:
        rows = (
            self._session.query(CategoryRuleModel)
            .order_by(CategoryRuleModel.priority.asc())
            .all()
        )
        return [
            CategoryRule(
                id=r.id,
                keyword=r.keyword,
                category=r.category,
                priority=r.priority,
                is_default=r.is_default,
            )
            for r in rows
        ]

    def save_category_rules(self, rules: list[CategoryRule]) -> None:
        """Atomically replace all category rules."""
        self._session.query(CategoryRuleModel).delete()
        for rule in rules:
            self._session.add(CategoryRuleModel(
                keyword=rule.keyword,
                category=rule.category,
                priority=rule.priority,
                is_default=rule.is_default,
            ))
        self._session.commit()

    # ── Fixed costs ───────────────────────────────────────────────────────────

    def get_fixed_costs(self) -> list[FixedCost]:
        rows = self._session.query(FixedCostModel).order_by(FixedCostModel.id.asc()).all()
        return [FixedCost(id=r.id, label=r.label, amount=r.amount) for r in rows]

    def save_fixed_costs(self, costs: list[FixedCost]) -> None:
        """Atomically replace all fixed cost entries."""
        self._session.query(FixedCostModel).delete()
        for cost in costs:
            self._session.add(FixedCostModel(label=cost.label, amount=cost.amount))
        self._session.commit()

    # ── Fixed income ──────────────────────────────────────────────────────────

    def get_fixed_income(self) -> list[FixedIncome]:
        rows = self._session.query(FixedIncomeModel).order_by(FixedIncomeModel.id.asc()).all()
        return [FixedIncome(id=r.id, label=r.label, amount=r.amount) for r in rows]

    def save_fixed_income(self, income: list[FixedIncome]) -> None:
        """Atomically replace all fixed income entries."""
        self._session.query(FixedIncomeModel).delete()
        for entry in income:
            self._session.add(FixedIncomeModel(label=entry.label, amount=entry.amount))
        self._session.commit()


# Runtime type-check
_: SettingsRepositoryPort = SQLAlchemySettingsRepository.__new__(SQLAlchemySettingsRepository)  # type: ignore[assignment]
