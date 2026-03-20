"""
Settings router:
  GET /settings/category-rules  — list all persisted rules ordered by priority
  PUT /settings/category-rules  — atomically replace all rules
  GET /settings/fixed-costs     — list all fixed cost entries
  PUT /settings/fixed-costs     — atomically replace all fixed cost entries
  GET /settings/fixed-income    — list all fixed income entries
  PUT /settings/fixed-income    — atomically replace all fixed income entries
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.use_cases.get_category_rules import GetCategoryRulesUseCase
from src.application.use_cases.get_fixed_costs import GetFixedCostsUseCase
from src.application.use_cases.get_fixed_income import GetFixedIncomeUseCase
from src.application.use_cases.save_category_rules import SaveCategoryRulesUseCase
from src.application.use_cases.save_fixed_costs import SaveFixedCostsUseCase
from src.application.use_cases.save_fixed_income import SaveFixedIncomeUseCase
from src.domain.entities import CategoryRule, FixedCost, FixedIncome
from src.infrastructure.database import get_session
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository

router = APIRouter(prefix="/settings", tags=["settings"])


# ── DTOs ──────────────────────────────────────────────────────────────────────

class CategoryRuleOut(BaseModel):
    id: int | None
    keyword: str
    category: str
    priority: int
    isDefault: bool


class CategoryRuleIn(BaseModel):
    keyword: str
    category: str
    priority: int
    isDefault: bool = False


# ── Dependency ────────────────────────────────────────────────────────────────

def _settings_repo(session: Session = Depends(get_session)) -> SQLAlchemySettingsRepository:
    return SQLAlchemySettingsRepository(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/category-rules",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryRuleOut],
)
def get_category_rules(
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> list[CategoryRuleOut]:
    """Return all category rules ordered by priority ascending."""
    use_case = GetCategoryRulesUseCase(repo)
    return [
        CategoryRuleOut(
            id=r.id,
            keyword=r.keyword,
            category=r.category,
            priority=r.priority,
            isDefault=r.is_default,
        )
        for r in use_case.execute()
    ]


@router.put(
    "/category-rules",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def save_category_rules(
    rules: list[CategoryRuleIn],
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> None:
    """Atomically replace all category rules."""
    use_case = SaveCategoryRulesUseCase(repo)
    use_case.execute([
        CategoryRule(
            keyword=r.keyword,
            category=r.category,
            priority=r.priority,
            is_default=r.isDefault,
        )
        for r in rules
    ])


# ── Fixed costs DTOs & endpoints ──────────────────────────────────────────────

class FixedCostOut(BaseModel):
    id: int | None
    label: str
    amount: float


class FixedCostIn(BaseModel):
    label: str
    amount: float


@router.get(
    "/fixed-costs",
    status_code=status.HTTP_200_OK,
    response_model=list[FixedCostOut],
)
def get_fixed_costs(
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> list[FixedCostOut]:
    """Return all fixed cost entries."""
    use_case = GetFixedCostsUseCase(repo)
    return [FixedCostOut(id=c.id, label=c.label, amount=c.amount) for c in use_case.execute()]


@router.put(
    "/fixed-costs",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def save_fixed_costs(
    costs: list[FixedCostIn],
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> None:
    """Atomically replace all fixed cost entries."""
    use_case = SaveFixedCostsUseCase(repo)
    use_case.execute([FixedCost(label=c.label, amount=c.amount) for c in costs])


# ── Fixed income DTOs & endpoints ─────────────────────────────────────────────

class FixedIncomeOut(BaseModel):
    id: int | None
    label: str
    amount: float


class FixedIncomeIn(BaseModel):
    label: str
    amount: float


@router.get(
    "/fixed-income",
    status_code=status.HTTP_200_OK,
    response_model=list[FixedIncomeOut],
)
def get_fixed_income(
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> list[FixedIncomeOut]:
    """Return all fixed income entries."""
    use_case = GetFixedIncomeUseCase(repo)
    return [FixedIncomeOut(id=i.id, label=i.label, amount=i.amount) for i in use_case.execute()]


@router.put(
    "/fixed-income",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def save_fixed_income(
    income: list[FixedIncomeIn],
    repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> None:
    """Atomically replace all fixed income entries."""
    use_case = SaveFixedIncomeUseCase(repo)
    use_case.execute([FixedIncome(label=i.label, amount=i.amount) for i in income])
