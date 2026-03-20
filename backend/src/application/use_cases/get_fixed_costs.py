"""
GetFixedCostsUseCase

Returns all persisted fixed cost entries.
"""
from __future__ import annotations

from src.domain.entities import FixedCost
from src.domain.repositories import SettingsRepository


class GetFixedCostsUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self) -> list[FixedCost]:
        return self._settings.get_fixed_costs()
