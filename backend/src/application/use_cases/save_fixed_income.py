"""
SaveFixedIncomeUseCase

Atomically replaces all fixed income entries.
Caller owns the full list — pass an empty list to clear all entries.
"""
from __future__ import annotations

from src.domain.entities import FixedIncome
from src.domain.repositories import SettingsRepository


class SaveFixedIncomeUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self, income: list[FixedIncome]) -> None:
        self._settings.save_fixed_income(income)
