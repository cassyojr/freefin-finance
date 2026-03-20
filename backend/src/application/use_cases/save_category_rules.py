"""
SaveCategoryRulesUseCase

Atomically replaces all category rules (custom + defaults).
Caller is responsible for assembling the full ordered list.
"""
from __future__ import annotations

from src.domain.entities import CategoryRule
from src.domain.repositories import SettingsRepository


class SaveCategoryRulesUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self, rules: list[CategoryRule]) -> None:
        self._settings.save_category_rules(rules)
