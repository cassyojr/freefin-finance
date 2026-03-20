"""
GetFixedIncomeUseCase

Returns all persisted fixed income entries.
"""
from __future__ import annotations

from src.domain.entities import FixedIncome
from src.domain.repositories import SettingsRepository


class GetFixedIncomeUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self) -> list[FixedIncome]:
        return self._settings.get_fixed_income()
