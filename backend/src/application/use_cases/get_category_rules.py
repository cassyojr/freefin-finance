"""
GetCategoryRulesUseCase

Returns all persisted category rules ordered by priority ascending.
"""
from __future__ import annotations

from src.domain.entities import CategoryRule
from src.domain.repositories import SettingsRepository


class GetCategoryRulesUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self) -> list[CategoryRule]:
        return self._settings.get_category_rules()
