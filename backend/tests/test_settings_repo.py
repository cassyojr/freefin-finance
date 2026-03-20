"""
Unit tests for SQLAlchemySettingsRepository — fixed costs and fixed income.

Covers: empty list, save-and-list, replace-all semantics, multiple entries.
Category-rules tests are intentionally in a separate file (test_settings_repo.py
would be the natural home, but keep them together here since fixed costs/income
are the new additions).
"""
from __future__ import annotations

import pytest

from src.domain.entities import FixedCost, FixedIncome
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository


# ── Fixed Costs ───────────────────────────────────────────────────────────────

def test_fixed_costs_empty_on_start(settings_repo: SQLAlchemySettingsRepository):
    assert settings_repo.get_fixed_costs() == []


def test_save_and_get_fixed_costs(settings_repo: SQLAlchemySettingsRepository):
    costs = [
        FixedCost(label="Aluguel", amount=1500.0),
        FixedCost(label="Internet", amount=99.90),
    ]
    settings_repo.save_fixed_costs(costs)

    result = settings_repo.get_fixed_costs()

    assert len(result) == 2
    labels = [c.label for c in result]
    assert "Aluguel" in labels
    assert "Internet" in labels


def test_fixed_costs_ids_are_assigned(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_costs([FixedCost(label="Aluguel", amount=1500.0)])
    result = settings_repo.get_fixed_costs()
    assert result[0].id is not None


def test_fixed_costs_replace_all_semantics(settings_repo: SQLAlchemySettingsRepository):
    """Saving a new list must fully replace the previous one (no stale rows)."""
    settings_repo.save_fixed_costs([
        FixedCost(label="Aluguel", amount=1500.0),
        FixedCost(label="Internet", amount=99.90),
    ])

    settings_repo.save_fixed_costs([FixedCost(label="Condomínio", amount=350.0)])

    result = settings_repo.get_fixed_costs()
    assert len(result) == 1
    assert result[0].label == "Condomínio"


def test_save_empty_fixed_costs_clears_all(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_costs([FixedCost(label="Aluguel", amount=1500.0)])
    settings_repo.save_fixed_costs([])
    assert settings_repo.get_fixed_costs() == []


def test_fixed_costs_preserves_amount_precision(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_costs([FixedCost(label="Plano", amount=129.99)])
    result = settings_repo.get_fixed_costs()
    assert abs(result[0].amount - 129.99) < 0.001


# ── Fixed Income ──────────────────────────────────────────────────────────────

def test_fixed_income_empty_on_start(settings_repo: SQLAlchemySettingsRepository):
    assert settings_repo.get_fixed_income() == []


def test_save_and_get_fixed_income(settings_repo: SQLAlchemySettingsRepository):
    income = [
        FixedIncome(label="Salário", amount=5000.0),
        FixedIncome(label="Freelance", amount=800.0),
    ]
    settings_repo.save_fixed_income(income)

    result = settings_repo.get_fixed_income()

    assert len(result) == 2
    labels = [i.label for i in result]
    assert "Salário" in labels
    assert "Freelance" in labels


def test_fixed_income_ids_are_assigned(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_income([FixedIncome(label="Salário", amount=5000.0)])
    result = settings_repo.get_fixed_income()
    assert result[0].id is not None


def test_fixed_income_replace_all_semantics(settings_repo: SQLAlchemySettingsRepository):
    """Saving a new list must fully replace the previous one (no stale rows)."""
    settings_repo.save_fixed_income([
        FixedIncome(label="Salário", amount=5000.0),
        FixedIncome(label="Freelance", amount=800.0),
    ])

    settings_repo.save_fixed_income([FixedIncome(label="Mesada", amount=200.0)])

    result = settings_repo.get_fixed_income()
    assert len(result) == 1
    assert result[0].label == "Mesada"


def test_save_empty_fixed_income_clears_all(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_income([FixedIncome(label="Salário", amount=5000.0)])
    settings_repo.save_fixed_income([])
    assert settings_repo.get_fixed_income() == []


def test_fixed_income_preserves_amount_precision(settings_repo: SQLAlchemySettingsRepository):
    settings_repo.save_fixed_income([FixedIncome(label="Dividendos", amount=1234.56)])
    result = settings_repo.get_fixed_income()
    assert abs(result[0].amount - 1234.56) < 0.001


# ── Isolation: fixed costs and fixed income tables are independent ─────────────

def test_fixed_costs_and_income_are_independent(settings_repo: SQLAlchemySettingsRepository):
    """Clearing one collection must not affect the other."""
    settings_repo.save_fixed_costs([FixedCost(label="Aluguel", amount=1500.0)])
    settings_repo.save_fixed_income([FixedIncome(label="Salário", amount=5000.0)])

    settings_repo.save_fixed_costs([])

    assert settings_repo.get_fixed_costs() == []
    assert len(settings_repo.get_fixed_income()) == 1
