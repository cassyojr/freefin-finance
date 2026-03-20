"""
SQLAlchemy ORM models.

Rules:
- This module is INFRASTRUCTURE only — domain layer must never import from here.
- Every model maps to one domain entity.
- Transaction has an ON DELETE CASCADE FK to ImportedStatement.
- checksum is UNIQUE to enforce import-once at the DB level.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ImportedStatementModel(Base):
    __tablename__ = "imported_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statement_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    statement_month: Mapped[str] = mapped_column(String(2), nullable=False)
    statement_year: Mapped[str] = mapped_column(String(4), nullable=False)
    statement_label: Mapped[str] = mapped_column(String, nullable=False)
    source_file: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    official_total: Mapped[float] = mapped_column(Float, nullable=False)
    parsed_total: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # cascade="all, delete-orphan" means deleting a statement removes all its transactions
    transactions: Mapped[list[TransactionModel]] = relationship(
        "TransactionModel",
        back_populates="statement",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TransactionModel(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ondelete="CASCADE" adds the DB-level FK cascade alongside the ORM cascade above
    statement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("imported_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    purchase_date: Mapped[str] = mapped_column(String(5), nullable=False)
    purchase_day: Mapped[str] = mapped_column(String(2), nullable=False)
    purchase_month: Mapped[str] = mapped_column(String(2), nullable=False)
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    raw_merchant: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    is_installment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    installment_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installment_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    statement: Mapped[ImportedStatementModel] = relationship(
        "ImportedStatementModel",
        back_populates="transactions",
    )


class CategoryRuleModel(Base):
    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FixedCostModel(Base):
    __tablename__ = "fixed_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)


class FixedIncomeModel(Base):
    __tablename__ = "fixed_income"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
