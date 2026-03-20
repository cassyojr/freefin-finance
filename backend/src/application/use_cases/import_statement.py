"""
ImportStatementUseCase

Flow:
1. Compute SHA-256 checksum of PDF bytes.
2. Reject with DuplicateStatementError if checksum already exists.
3. Parse PDF via pdf_parser (bytes are never written to disk).
4. Build ImportedStatement entity with computed totals.
5. Atomically persist statement + transactions via StatementRepository.
6. Return the persisted ImportedStatement.
"""
from __future__ import annotations

from src.domain.entities import ImportedStatement
from src.domain.repositories import StatementRepository, SettingsRepository
from src.infrastructure.parser.pdf_parser import (
    DEFAULT_CATEGORY_RULES,
    ParseResult,
    parse_pdf,
)


class DuplicateStatementError(Exception):
    """Raised when the uploaded PDF matches an already-imported checksum."""


class ImportStatementUseCase:
    def __init__(
        self,
        statement_repo: StatementRepository,
        settings_repo: SettingsRepository,
    ) -> None:
        self._statements = statement_repo
        self._settings = settings_repo

    def execute(self, pdf_bytes: bytes, source_file: str) -> ImportedStatement:
        # 1. Parse first to get checksum (parser always computes it)
        rules = self._settings.get_category_rules() or DEFAULT_CATEGORY_RULES
        result: ParseResult = parse_pdf(pdf_bytes, source_file, rules=rules)

        # 2. Duplicate guard
        if self._statements.find_by_checksum(result.checksum):
            raise DuplicateStatementError(
                f"Statement already imported (checksum={result.checksum[:16]}…)"
            )

        # 3. Build entity
        si = result.statement_info
        parsed_total = round(sum(t.value for t in result.transactions), 2)
        from datetime import datetime, timezone

        statement = ImportedStatement(
            statement_key=si.statement_key,
            statement_month=si.statement_month,
            statement_year=si.statement_year,
            statement_label=si.label,
            source_file=source_file,
            checksum=result.checksum,
            official_total=result.official_total,
            parsed_total=parsed_total,
            transaction_count=len(result.transactions),
            imported_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        # 4. Persist atomically
        return self._statements.save(statement, result.transactions)
