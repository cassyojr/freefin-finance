"""
Tests for settings category-rules use cases and API endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.use_cases.get_category_rules import GetCategoryRulesUseCase
from src.application.use_cases.save_category_rules import SaveCategoryRulesUseCase
from src.domain.entities import CategoryRule
from src.infrastructure.models import Base
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository


# ── Use case unit tests ───────────────────────────────────────────────────────

def test_get_category_rules_empty(settings_repo: SQLAlchemySettingsRepository):
    rules = GetCategoryRulesUseCase(settings_repo).execute()
    assert rules == []


def test_save_and_get_category_rules(settings_repo: SQLAlchemySettingsRepository):
    rules_in = [
        CategoryRule(keyword="panvel", category="Saúde", priority=0, is_default=False),
        CategoryRule(keyword="ifood", category="Delivery", priority=1, is_default=False),
    ]
    SaveCategoryRulesUseCase(settings_repo).execute(rules_in)

    result = GetCategoryRulesUseCase(settings_repo).execute()
    assert len(result) == 2
    keywords = [r.keyword for r in result]
    assert "panvel" in keywords
    assert "ifood" in keywords


def test_save_replaces_all_rules(settings_repo: SQLAlchemySettingsRepository):
    """Saving a new list should atomically replace any existing rules."""
    SaveCategoryRulesUseCase(settings_repo).execute([
        CategoryRule(keyword="netflix", category="Entretenimento", priority=0, is_default=False),
    ])
    SaveCategoryRulesUseCase(settings_repo).execute([
        CategoryRule(keyword="amazon", category="Compras Online", priority=0, is_default=False),
    ])
    result = GetCategoryRulesUseCase(settings_repo).execute()
    assert len(result) == 1
    assert result[0].keyword == "amazon"


def test_save_empty_list_clears_rules(settings_repo: SQLAlchemySettingsRepository):
    SaveCategoryRulesUseCase(settings_repo).execute([
        CategoryRule(keyword="panvel", category="Saúde", priority=0, is_default=False),
    ])
    SaveCategoryRulesUseCase(settings_repo).execute([])
    assert GetCategoryRulesUseCase(settings_repo).execute() == []


# ── API endpoint tests ────────────────────────────────────────────────────────

@pytest.fixture()
def client() -> TestClient:
    """
    FastAPI test client backed by a fresh in-memory SQLite DB.
    StaticPool ensures create_all() and each request share the same connection.
    """
    from src.infrastructure.database import get_session
    from src.interface.main import app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_session():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_get_category_rules_empty_api(client: TestClient):
    resp = client.get("/api/settings/category-rules")
    assert resp.status_code == 200
    assert resp.json() == []


def test_put_and_get_category_rules_api(client: TestClient):
    payload = [
        {"keyword": "panvel", "category": "Saúde", "priority": 0, "isDefault": False},
        {"keyword": "steam", "category": "Entretenimento", "priority": 1, "isDefault": False},
    ]
    put_resp = client.put("/api/settings/category-rules", json=payload)
    assert put_resp.status_code == 204

    get_resp = client.get("/api/settings/category-rules")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data) == 2
    keywords = {r["keyword"] for r in data}
    assert keywords == {"panvel", "steam"}


def test_put_category_rules_replaces_all_api(client: TestClient):
    client.put("/api/settings/category-rules", json=[
        {"keyword": "netflix", "category": "Entretenimento", "priority": 0, "isDefault": False},
    ])
    client.put("/api/settings/category-rules", json=[
        {"keyword": "amazon", "category": "Compras Online", "priority": 0, "isDefault": False},
    ])
    data = client.get("/api/settings/category-rules").json()
    assert len(data) == 1
    assert data[0]["keyword"] == "amazon"


def test_put_empty_list_clears_rules_api(client: TestClient):
    client.put("/api/settings/category-rules", json=[
        {"keyword": "panvel", "category": "Saúde", "priority": 0, "isDefault": False},
    ])
    resp = client.put("/api/settings/category-rules", json=[])
    assert resp.status_code == 204
    assert client.get("/api/settings/category-rules").json() == []
