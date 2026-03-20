"""
FastAPI application entry point.

Start the server:
    cd backend
    ../.venv/Scripts/uvicorn src.interface.main:app --reload --port 8000

Interactive API docs:
    http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.database import init_db
from src.interface.routers.settings import router as settings_router
from src.interface.routers.statements import router as statements_router
from src.interface.routers.transactions import router as transactions_router

app = FastAPI(
    title="Extrato API",
    description="Nubank statement dashboard — backend API",
    version="0.1.0",
)

# Allow the HTML frontend served from any local origin (file://, localhost:*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routes are mounted under /api to match the frontend's BACKEND_URL expectations
app.include_router(statements_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    """Create all DB tables on first run (idempotent)."""
    init_db()


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
