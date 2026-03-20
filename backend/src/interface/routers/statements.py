"""
Statements router — MVP endpoints:
  POST   /statements/import   — upload PDF, parse, persist
  GET    /statements           — list all imported statements
  DELETE /statements/{id}      — hard delete + cascade
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.use_cases.delete_statement import (
    DeleteStatementUseCase,
    StatementNotFoundError,
)
from src.application.use_cases.import_statement import (
    DuplicateStatementError,
    ImportStatementUseCase,
)
from src.application.use_cases.list_statements import ListStatementsUseCase
from src.infrastructure.database import get_session
from src.infrastructure.repositories.settings_repo import SQLAlchemySettingsRepository
from src.infrastructure.repositories.statement_repo import SQLAlchemyStatementRepository

router = APIRouter(prefix="/statements", tags=["statements"])


# ── Response DTOs ─────────────────────────────────────────────────────────────
# Field names are camelCase to match what the JS frontend reads directly.

class StatementOut(BaseModel):
    id: int
    fileName: str        # source_file
    statementKey: str
    label: str           # statement_label
    officialTotal: float
    parsedTotal: float
    diff: float
    transactionCount: int
    importedAt: str


def _to_out(s) -> StatementOut:
    return StatementOut(
        id=s.id,
        fileName=s.source_file,
        statementKey=s.statement_key,
        label=s.statement_label,
        officialTotal=s.official_total,
        parsedTotal=s.parsed_total,
        diff=s.diff,
        transactionCount=s.transaction_count,
        importedAt=s.imported_at.isoformat(),
    )


# ── Dependency helpers ────────────────────────────────────────────────────────

def _statement_repo(session: Session = Depends(get_session)) -> SQLAlchemyStatementRepository:
    return SQLAlchemyStatementRepository(session)


def _settings_repo(session: Session = Depends(get_session)) -> SQLAlchemySettingsRepository:
    return SQLAlchemySettingsRepository(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=StatementOut)
async def import_statement(
    file: UploadFile,
    stmt_repo: SQLAlchemyStatementRepository = Depends(_statement_repo),
    settings_repo: SQLAlchemySettingsRepository = Depends(_settings_repo),
) -> StatementOut:
    """Upload a Nubank PDF. Returns the imported statement summary."""
    pdf_bytes = await file.read()
    use_case = ImportStatementUseCase(stmt_repo, settings_repo)
    try:
        statement = use_case.execute(pdf_bytes, file.filename or "upload.pdf")
    except DuplicateStatementError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return _to_out(statement)


@router.get("", status_code=status.HTTP_200_OK, response_model=list[StatementOut])
def list_statements(
    stmt_repo: SQLAlchemyStatementRepository = Depends(_statement_repo),
) -> list[StatementOut]:
    """List all imported statements ordered by period."""
    use_case = ListStatementsUseCase(stmt_repo)
    return [_to_out(s) for s in use_case.execute()]


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_statement(
    statement_id: int,
    stmt_repo: SQLAlchemyStatementRepository = Depends(_statement_repo),
) -> None:
    """Hard-delete a statement and all its transactions (cascade)."""
    use_case = DeleteStatementUseCase(stmt_repo)
    try:
        use_case.execute(statement_id)
    except StatementNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
