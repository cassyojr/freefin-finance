"""
Unit tests for fixed costs and fixed income use cases.

Tests exercise the full application layer with a real in-memory DB, validating
that use cases correctly delegate to the repository.
"""
from __future__ import annotations

import pytest

from src.application.use_cases.get_fixed_costs import GetFixedCostsUseCase
from src.application.use_cases.get_fixed_income import GetFixedIncomeUseCase
from src.application.use_cases.save_fixed_costs import SaveFixedCostsUseCase
from src.application.use_cases.save_fixed_income import SaveFixedIncomeUseCase
from src.domain.entities import FixedCost, FixedIncome
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository


# ── Fixed Costs use cases ─────────────────────────────────────────────────────

def test_get_fixed_costs_returns_empty(settings_repo: SQLAlchemySettingsRepository):
    result = GetFixedCostsUseCase(settings_repo).execute()
    assert result == []


def test_save_then_get_fixed_costs(settings_repo: SQLAlchemySettingsRepository):
    costs = [FixedCost(label="Aluguel", amount=1500.0), FixedCost(label="Internet", amount=99.0)]
    SaveFixedCostsUseCase(settings_repo).execute(costs)

    result = GetFixedCostsUseCase(settings_repo).execute()

    assert len(result) == 2
    assert {c.label for c in result} == {"Aluguel", "Internet"}


def test_save_fixed_costs_replaces_previous(settings_repo: SQLAlchemySettingsRepository):
    SaveFixedCostsUseCase(settings_repo).execute([FixedCost(label="Old", amount=100.0)])
    SaveFixedCostsUseCase(settings_repo).execute([FixedCost(label="New", amount=200.0)])

    result = GetFixedCostsUseCase(settings_repo).execute()

    assert len(result) == 1
    assert result[0].label == "New"


def test_save_fixed_costs_empty_list_clears(settings_repo: SQLAlchemySettingsRepository):
    SaveFixedCostsUseCase(settings_repo).execute([FixedCost(label="X", amount=1.0)])
    SaveFixedCostsUseCase(settings_repo).execute([])

    assert GetFixedCostsUseCase(settings_repo).execute() == []


# ── Fixed Income use cases ────────────────────────────────────────────────────

def test_get_fixed_income_returns_empty(settings_repo: SQLAlchemySettingsRepository):
    result = GetFixedIncomeUseCase(settings_repo).execute()
    assert result == []


def test_save_then_get_fixed_income(settings_repo: SQLAlchemySettingsRepository):
    income = [FixedIncome(label="Salário", amount=5000.0), FixedIncome(label="Freelance", amount=800.0)]
    SaveFixedIncomeUseCase(settings_repo).execute(income)

    result = GetFixedIncomeUseCase(settings_repo).execute()

    assert len(result) == 2
    assert {i.label for i in result} == {"Salário", "Freelance"}


def test_save_fixed_income_replaces_previous(settings_repo: SQLAlchemySettingsRepository):
    SaveFixedIncomeUseCase(settings_repo).execute([FixedIncome(label="Old", amount=1000.0)])
    SaveFixedIncomeUseCase(settings_repo).execute([FixedIncome(label="New", amount=2000.0)])

    result = GetFixedIncomeUseCase(settings_repo).execute()

    assert len(result) == 1
    assert result[0].label == "New"


def test_save_fixed_income_empty_list_clears(settings_repo: SQLAlchemySettingsRepository):
    SaveFixedIncomeUseCase(settings_repo).execute([FixedIncome(label="X", amount=1.0)])
    SaveFixedIncomeUseCase(settings_repo).execute([])

    assert GetFixedIncomeUseCase(settings_repo).execute() == []
