"""
Unit tests for ImportStatementUseCase.

The PDF parser is mocked — no real PDFs needed.
Covers: success path, duplicate rejection, parsed_total calculation.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.application.use_cases.import_statement import (
    DuplicateStatementError,
    ImportStatementUseCase,
)
from src.infrastructure.parser.pdf_parser import ParseResult, StatementInfo
from tests.conftest import make_transaction


def _make_parse_result(checksum: str = "fresh-cksum", tx_count: int = 3) -> ParseResult:
    si = StatementInfo(
        statement_month="11",
        statement_year="2025",
        statement_key="2025-11",
        label="Novembro/2025",
    )
    # Vary merchant so each transaction is distinct
    txs = [make_transaction(value=100.0, merchant=f"MERCHANT-{i}") for i in range(tx_count)]
    return ParseResult(
        statement_info=si,
        official_total=300.0,
        transactions=txs,
        checksum=checksum,
    )


@patch("src.application.use_cases.import_statement.parse_pdf")
def test_import_success(mock_parse, statement_repo, settings_repo):
    mock_parse.return_value = _make_parse_result(checksum="cksum-new")

    use_case = ImportStatementUseCase(statement_repo, settings_repo)
    result = use_case.execute(b"fake-pdf-bytes", "2025-11.pdf")

    assert result.id is not None
    assert result.statement_key == "2025-11"
    assert result.transaction_count == 3
    assert result.parsed_total == 300.0
    assert result.official_total == 300.0


@patch("src.application.use_cases.import_statement.parse_pdf")
def test_import_duplicate_raises(mock_parse, statement_repo, settings_repo):
    """Uploading the same PDF twice must raise DuplicateStatementError."""
    mock_parse.return_value = _make_parse_result(checksum="dup-cksum")

    use_case = ImportStatementUseCase(statement_repo, settings_repo)
    use_case.execute(b"fake-pdf-bytes", "2025-11.pdf")

    with pytest.raises(DuplicateStatementError):
        use_case.execute(b"fake-pdf-bytes", "2025-11.pdf")


@patch("src.application.use_cases.import_statement.parse_pdf")
def test_import_parsed_total_is_sum_of_transactions(mock_parse, statement_repo, settings_repo):
    txs = [make_transaction(value=v) for v in [100.0, 200.50, -50.0]]
    si = StatementInfo("11", "2025", "2025-11", "Novembro/2025")
    mock_parse.return_value = ParseResult(
        statement_info=si,
        official_total=500.0,
        transactions=txs,
        checksum="cksum-sum",
    )

    use_case = ImportStatementUseCase(statement_repo, settings_repo)
    result = use_case.execute(b"bytes", "2025-11.pdf")

    assert result.parsed_total == round(100.0 + 200.50 + (-50.0), 2)
