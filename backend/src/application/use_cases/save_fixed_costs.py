"""
SaveFixedCostsUseCase

Atomically replaces all fixed cost entries.
Caller owns the full list — pass an empty list to clear all entries.
"""
from __future__ import annotations

from src.domain.entities import FixedCost
from src.domain.repositories import SettingsRepository


class SaveFixedCostsUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self, costs: list[FixedCost]) -> None:
        self._settings.save_fixed_costs(costs)
