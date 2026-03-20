"""
Transactions router — MVP endpoint:
  GET /transactions — filtered, sorted, paginated transaction list

Response fields are camelCase to match what the JS frontend reads directly.
The endpoint JOINs with ImportedStatement to include sourceFile and statementLabel.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.infrastructure.database import get_session
from src.infrastructure.models import ImportedStatementModel, TransactionModel

router = APIRouter(prefix="/transactions", tags=["transactions"])

_SORTABLE = {
    "purchase_date": TransactionModel.purchase_date,
    "merchant":      TransactionModel.merchant,
    "value":         TransactionModel.value,
    "category":      TransactionModel.category,
}


# ── Response DTO (camelCase — consumed directly by JS as transaction objects) ─

class TransactionOut(BaseModel):
    id: int
    statementId: int
    statementKey: str
    statementMonth: str
    statementYear: str
    statementLabel: str
    sourceFile: str
    purchaseDate: str
    purchaseDay: str
    purchaseMonth: str
    merchant: str
    rawMerchant: str
    value: float
    category: str
    isInstallment: bool
    installmentCurrent: Optional[int]
    installmentTotal: Optional[int]


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("", status_code=status.HTTP_200_OK, response_model=list[TransactionOut])
def list_transactions(
    statement_key: Optional[str] = None,
    category: Optional[str] = None,
    purchase_month: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    credits_only: bool = False,
    sort_col: str = "purchase_date",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 10000,   # default to all — frontend filters client-side
    session: Session = Depends(get_session),
) -> list[TransactionOut]:
    """Return transactions with enriched statement info (JOIN)."""
    query = (
        session.query(TransactionModel, ImportedStatementModel.source_file, ImportedStatementModel.statement_label)
        .join(ImportedStatementModel, TransactionModel.statement_id == ImportedStatementModel.id)
    )

    if statement_key:
        query = query.filter(TransactionModel.statement_key == statement_key)
    if category:
        query = query.filter(TransactionModel.category == category)
    if purchase_month:
        query = query.filter(TransactionModel.purchase_month == purchase_month)
    if min_value is not None:
        query = query.filter(TransactionModel.value >= min_value)
    if max_value is not None:
        query = query.filter(TransactionModel.value <= max_value)
    if credits_only:
        query = query.filter(TransactionModel.value < 0)

    sort_column = _SORTABLE.get(sort_col, TransactionModel.purchase_date)
    query = query.order_by(sort_column.asc() if sort_dir == "asc" else sort_column.desc())

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    return [
        TransactionOut(
            id=tx.id,
            statementId=tx.statement_id,
            statementKey=tx.statement_key,
            statementMonth=tx.statement_key[5:7],
            statementYear=tx.statement_key[:4],
            statementLabel=stmt_label,
            sourceFile=src_file,
            purchaseDate=tx.purchase_date,
            purchaseDay=tx.purchase_day,
            purchaseMonth=tx.purchase_month,
            merchant=tx.merchant,
            rawMerchant=tx.raw_merchant,
            value=tx.value,
            category=tx.category,
            isInstallment=tx.is_installment,
            installmentCurrent=tx.installment_current,
            installmentTotal=tx.installment_total,
        )
        for tx, src_file, stmt_label in query.all()
    ]
