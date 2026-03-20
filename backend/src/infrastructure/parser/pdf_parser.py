"""
PDF parser — Python port of the JS extraction logic in index.html.

Parity rules (mirrors JS exactly):
  - Column split at x = page_width × 0.57
  - Row grouping by Y coordinate, tolerance 2 pt
  - Rows sorted top-to-bottom (descending Y within page)
  - Statement period from "Postagem: DD/MM/YYYY" line
  - Official total from "Valor da fatura atual" row (fallback: "Lançamentos atuais")
  - State machine per column: OPEN on "compras e saques",
      SKIP on "compras parceladas", CLOSE on "encargos cobrados nesta fatura"
  - Transaction regex: ^(DD/MM) (.+?) (-?\\d{1,3}(\\.\\d{3})*,\\d{2})$
  - Tax pass: "repasse de iof" and "total de encargos" (no DD/MM date)
  - Merchant cleaning: replace * and -CT, collapse whitespace
  - Categorisation: custom rules (priority order) → defaults → "Outros"
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

import pdfplumber

from src.domain.entities import CategoryRule, Transaction

# ─────────────────────────────────────────────────────────────
# Column split constant (mirrors viewport.width * 0.57 in JS)
# ─────────────────────────────────────────────────────────────
COLUMN_SPLIT_RATIO = 0.57

# ─────────────────────────────────────────────────────────────
# Default category rules — identical to DEFAULT_CATEGORY_RULES in index.html
# ─────────────────────────────────────────────────────────────
DEFAULT_CATEGORY_RULES: list[CategoryRule] = [
    CategoryRule(keyword="panvel",          category="Saúde",           priority=100, is_default=True),
    CategoryRule(keyword="drogaria",        category="Saúde",           priority=101, is_default=True),
    CategoryRule(keyword="farmacia",        category="Saúde",           priority=102, is_default=True),
    CategoryRule(keyword="amais",           category="Saúde",           priority=103, is_default=True),
    CategoryRule(keyword="vaccine",         category="Saúde",           priority=104, is_default=True),
    CategoryRule(keyword="pague menos",     category="Saúde",           priority=105, is_default=True),
    CategoryRule(keyword="clinica",         category="Saúde",           priority=106, is_default=True),
    CategoryRule(keyword="hospital",        category="Saúde",           priority=107, is_default=True),
    CategoryRule(keyword="atacadao",        category="Alimentação",     priority=108, is_default=True),
    CategoryRule(keyword="festval",         category="Alimentação",     priority=109, is_default=True),
    CategoryRule(keyword="edvilson",        category="Alimentação",     priority=110, is_default=True),
    CategoryRule(keyword="quero cafete",    category="Alimentação",     priority=111, is_default=True),
    CategoryRule(keyword="bd alimentos",    category="Alimentação",     priority=112, is_default=True),
    CategoryRule(keyword="mc donalds",      category="Alimentação",     priority=113, is_default=True),
    CategoryRule(keyword="grossi",          category="Alimentação",     priority=114, is_default=True),
    CategoryRule(keyword="sfiha",           category="Alimentação",     priority=115, is_default=True),
    CategoryRule(keyword="bier hoff",       category="Alimentação",     priority=116, is_default=True),
    CategoryRule(keyword="condor",          category="Alimentação",     priority=117, is_default=True),
    CategoryRule(keyword="bonna",           category="Alimentação",     priority=118, is_default=True),
    CategoryRule(keyword="jardim dos",      category="Alimentação",     priority=119, is_default=True),
    CategoryRule(keyword="ifood",           category="Delivery",        priority=120, is_default=True),
    CategoryRule(keyword="amazon",          category="Compras Online",  priority=121, is_default=True),
    CategoryRule(keyword="mercadolivre",    category="Compras Online",  priority=122, is_default=True),
    CategoryRule(keyword="webcontinent",    category="Compras Online",  priority=123, is_default=True),
    CategoryRule(keyword="havan",           category="Vestuário",       priority=124, is_default=True),
    CategoryRule(keyword="baby chic",       category="Vestuário",       priority=125, is_default=True),
    CategoryRule(keyword="lady lili",       category="Vestuário",       priority=126, is_default=True),
    CategoryRule(keyword="havaianas",       category="Vestuário",       priority=127, is_default=True),
    CategoryRule(keyword="bekos",           category="Vestuário",       priority=128, is_default=True),
    CategoryRule(keyword="damarate",        category="Vestuário",       priority=129, is_default=True),
    CategoryRule(keyword="lupo",            category="Vestuário",       priority=130, is_default=True),
    CategoryRule(keyword="oboticar",        category="Vestuário",       priority=131, is_default=True),
    CategoryRule(keyword="decathlon",       category="Hobby / Esporte", priority=132, is_default=True),
    CategoryRule(keyword="pet shop",        category="Hobby / Esporte", priority=133, is_default=True),
    CategoryRule(keyword="evo pet",         category="Hobby / Esporte", priority=134, is_default=True),
    CategoryRule(keyword="octoshop",        category="Hobby / Esporte", priority=135, is_default=True),
    CategoryRule(keyword="academia",        category="Hobby / Esporte", priority=136, is_default=True),
    CategoryRule(keyword="leroy",           category="Hobby / Esporte", priority=137, is_default=True),
    CategoryRule(keyword="digital foto",    category="Hobby / Esporte", priority=138, is_default=True),
    CategoryRule(keyword="auto posto",      category="Transporte",      priority=139, is_default=True),
    CategoryRule(keyword="petro",           category="Transporte",      priority=140, is_default=True),
    CategoryRule(keyword="estacionamen",    category="Transporte",      priority=141, is_default=True),
    CategoryRule(keyword="estapar",         category="Transporte",      priority=142, is_default=True),
    CategoryRule(keyword="shellbox",        category="Transporte",      priority=143, is_default=True),
    CategoryRule(keyword="posto",           category="Transporte",      priority=144, is_default=True),
    CategoryRule(keyword="netflix",         category="Entretenimento",  priority=145, is_default=True),
    CategoryRule(keyword="steam",           category="Entretenimento",  priority=146, is_default=True),
    CategoryRule(keyword="youtube",         category="Entretenimento",  priority=147, is_default=True),
    CategoryRule(keyword="trademap",        category="Investimentos",   priority=148, is_default=True),
    CategoryRule(keyword="suno",            category="Investimentos",   priority=149, is_default=True),
    CategoryRule(keyword="azul",            category="Viagem",          priority=150, is_default=True),
    CategoryRule(keyword="ton",             category="Serviços",        priority=151, is_default=True),
    CategoryRule(keyword="luiz fabiano",    category="Serviços",        priority=152, is_default=True),
    CategoryRule(keyword="iof",             category="Impostos",        priority=153, is_default=True),
    CategoryRule(keyword="anuidade",        category="Impostos",        priority=154, is_default=True),
    CategoryRule(keyword="imposto",         category="Impostos",        priority=155, is_default=True),
]

_TAX_PATTERNS = [
    {"label": "repasse de iof",      "merchant": "IOF Internacional"},
    {"label": "total de encargos",   "merchant": "Encargos (juros/IOF)"},
]

_TRANSACTION_RE = re.compile(
    r"^(\d{2}/\d{2})\s+(.+?)\s+(-?\s?\d{1,3}(?:\.\d{3})*,\d{2})$"
)
_INSTALLMENT_RE = re.compile(r"(\d{2})/(\d{2})")
_DATE_RE = re.compile(r"^(\d{2}/\d{2})")
_BRL_NUMBER_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
_POSTAGEM_RE = re.compile(r"Postagem[^\d]*(\d{2})/(\d{2})/(\d{4})", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────

@dataclass
class StatementInfo:
    statement_month: str   # MM
    statement_year: str    # YYYY
    statement_key: str     # YYYY-MM
    label: str             # e.g. "Novembro/2025"


@dataclass
class ParseResult:
    statement_info: StatementInfo
    official_total: float
    transactions: list[Transaction]
    checksum: str


# ─────────────────────────────────────────────────────────────
# Text helpers (ports of JS utility functions)
# ─────────────────────────────────────────────────────────────

def normalize_text(value: str) -> str:
    """Lowercase, strip accents, collapse to alphanumeric + space/colon/dash/slash."""
    s = str(value or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip combining marks
    s = re.sub(r"[^a-z0-9\s:/-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_brl(value: str) -> float:
    """Convert Brazilian number string to float. e.g. "1.234,56" → 1234.56"""
    cleaned = re.sub(r"\s+", "", value).replace(".", "").replace(",", ".")
    return float(cleaned)


def clean_merchant(value: str) -> str:
    """Mirror JS cleanMerchant: replace * and -CT, collapse whitespace."""
    s = value.replace("*", " ").replace("-CT", " ")
    return re.sub(r"\s+", " ", s).strip()


# ─────────────────────────────────────────────────────────────
# Categorisation
# ─────────────────────────────────────────────────────────────

def categorize_merchant(merchant: str, rules: list[CategoryRule]) -> str:
    """
    First-match categorisation.
    Rules must already be sorted by priority ascending before calling.
    """
    normalized = normalize_text(merchant)
    for rule in rules:
        if normalize_text(rule.keyword) in normalized:
            return rule.category
    return "Outros"


# ─────────────────────────────────────────────────────────────
# PDF row extraction (ports extractPdfData from JS)
# ─────────────────────────────────────────────────────────────

@dataclass
class _Row:
    y: float
    left: list[dict]   # [{"x": float, "text": str}]
    right: list[dict]


def _extract_rows(pdf_bytes: bytes) -> list[dict]:
    """
    Extract two-column rows from all pages.
    Column split at page_width × COLUMN_SPLIT_RATIO (mirrors viewport.width * 0.57).
    Rows within 2 pt of the same Y are merged.
    Returns list of {"page": int, "left": str, "right": str, "combined": str}.
    """
    rows: list[dict] = []

    with pdfplumber.open(pdf_bytes) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_width = page.width
            midpoint = page_width * COLUMN_SPLIT_RATIO

            raw_rows: list[_Row] = []
            for word in page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False):
                text = str(word.get("text", "")).strip()
                if not text:
                    continue
                x = word["x0"]
                y = word["top"]

                existing = next((r for r in raw_rows if abs(r.y - y) < 2), None)
                if existing is None:
                    existing = _Row(y=y, left=[], right=[])
                    raw_rows.append(existing)

                bucket = existing.left if x < midpoint else existing.right
                bucket.append({"x": x, "text": text})

            # Sort rows top-to-bottom (ascending top = descending Y in PDF coords)
            raw_rows.sort(key=lambda r: r.y)

            for row in raw_rows:
                left_text = " ".join(
                    item["text"] for item in sorted(row.left, key=lambda i: i["x"])
                ).strip()
                right_text = " ".join(
                    item["text"] for item in sorted(row.right, key=lambda i: i["x"])
                ).strip()
                left_text = re.sub(r"\s+", " ", left_text)
                right_text = re.sub(r"\s+", " ", right_text)

                rows.append({
                    "page": page_number,
                    "left": left_text,
                    "right": right_text,
                    "combined": f"{left_text} {right_text}".strip(),
                })

    return rows


# ─────────────────────────────────────────────────────────────
# Statement period detection (ports extractStatementInfoFromRows)
# ─────────────────────────────────────────────────────────────

_MONTH_LABELS = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",    "04": "Abril",
    "05": "Maio",    "06": "Junho",     "07": "Julho",    "08": "Agosto",
    "09": "Setembro","10": "Outubro",   "11": "Novembro", "12": "Dezembro",
}


def _extract_statement_info(rows: list[dict], source_file: str) -> StatementInfo:
    """
    Detect statement period from "Postagem: DD/MM/YYYY" row.
    Falls back to parsing source_file name (YYYY-MM.pdf pattern).
    """
    for row in rows:
        m = _POSTAGEM_RE.search(row["combined"])
        if m:
            month = m.group(2).zfill(2)
            year = m.group(3)
            label = f"{_MONTH_LABELS.get(month, month)}/{year}"
            return StatementInfo(
                statement_month=month,
                statement_year=year,
                statement_key=f"{year}-{month}",
                label=label,
            )

    # Fallback: parse from filename e.g. "2025-11.pdf"
    fm = re.search(r"(\d{4})-(\d{2})", source_file)
    if fm:
        year, month = fm.group(1), fm.group(2)
    else:
        year, month = "0000", "00"
    label = f"{_MONTH_LABELS.get(month, month)}/{year}"
    return StatementInfo(
        statement_month=month,
        statement_year=year,
        statement_key=f"{year}-{month}",
        label=label,
    )


# ─────────────────────────────────────────────────────────────
# Official total extraction (ports extractOfficialTotal)
# ─────────────────────────────────────────────────────────────

def _extract_official_total(rows: list[dict]) -> float:
    """
    Read "Valor da fatura atual" (preferred) or "Lançamentos atuais" (fallback).
    """
    for label in ("valor da fatura atual", "lancamentos atuais"):
        for row in rows:
            if label not in normalize_text(row["combined"]):
                continue
            numbers = _BRL_NUMBER_RE.findall(row["combined"])
            if not numbers:
                continue
            candidate = parse_brl(numbers[-1])
            if candidate > 100:
                return candidate
    return 0.0


# ─────────────────────────────────────────────────────────────
# Transaction line extraction (ports extractTransactionLines)
# ─────────────────────────────────────────────────────────────

def _extract_transaction_lines(rows: list[dict]) -> list[str]:
    """
    State machine per column — identical logic to JS extractTransactionLines.
    """
    left_in_section = False
    right_in_section = False
    left_in_future = False
    right_in_future = False
    result: list[str] = []

    for row in rows:
        for side, text in (("left", row.get("left", "")), ("right", row.get("right", ""))):
            text = (text or "").strip()
            if not text:
                continue

            is_left = side == "left"
            normalized = normalize_text(text)
            starts_with_date = bool(_DATE_RE.match(text))

            if "compras e saques" in normalized:
                if is_left:
                    left_in_section = True
                else:
                    right_in_section = True
                continue

            if "compras parceladas" in normalized:
                if is_left:
                    left_in_future = True
                else:
                    right_in_future = True
                continue

            if "encargos cobrados nesta fatura" in normalized:
                if is_left:
                    left_in_section = False
                    left_in_future = False
                else:
                    right_in_section = False
                    right_in_future = False
                continue

            active_section = left_in_section if is_left else right_in_section
            active_future  = left_in_future  if is_left else right_in_future

            if not active_section or active_future or not starts_with_date:
                continue

            result.append(re.sub(r"\s+", " ", text).strip())

    return result


# ─────────────────────────────────────────────────────────────
# Transaction parsing (ports parseTransactions)
# ─────────────────────────────────────────────────────────────

def _parse_transactions(
    lines: list[str],
    statement_info: StatementInfo,
    source_file: str,
    rules: list[CategoryRule],
    statement_id: int = 0,
) -> list[Transaction]:
    parsed: list[Transaction] = []

    for line in lines:
        clean_line = re.sub(r"\s+", " ", line).strip()
        m = _TRANSACTION_RE.match(clean_line)
        if not m:
            continue

        purchase_date = m.group(1)
        raw_merchant = clean_merchant(m.group(2))
        try:
            value = parse_brl(m.group(3))
        except ValueError:
            continue

        inst_m = _INSTALLMENT_RE.search(raw_merchant)
        installment_current = int(inst_m.group(1)) if inst_m else None
        installment_total   = int(inst_m.group(2)) if inst_m else None
        merchant = clean_merchant(_INSTALLMENT_RE.sub(" ", raw_merchant, count=1))

        parsed.append(Transaction(
            statement_id=statement_id,
            statement_key=statement_info.statement_key,
            purchase_date=purchase_date,
            purchase_day=purchase_date[:2],
            purchase_month=purchase_date[3:5],
            merchant=merchant,
            raw_merchant=raw_merchant,
            value=value,
            category=categorize_merchant(merchant, rules),
            is_installment=bool(inst_m),
            installment_current=installment_current,
            installment_total=installment_total,
        ))

    return parsed


# ─────────────────────────────────────────────────────────────
# Tax extraction (ports extractTaxTransactions)
# ─────────────────────────────────────────────────────────────

def _extract_tax_transactions(
    rows: list[dict],
    statement_info: StatementInfo,
    source_file: str,
    statement_id: int = 0,
) -> list[Transaction]:
    result: list[Transaction] = []
    last_date = f"01/{statement_info.statement_month}"

    for row in rows:
        date_m = _DATE_RE.match(row.get("left", "")) or _DATE_RE.match(row.get("right", ""))
        if date_m:
            last_date = date_m.group(0)

        for col_text in (row.get("left", ""), row.get("right", "")):
            if not col_text:
                continue
            col_norm = normalize_text(col_text)
            for pattern in _TAX_PATTERNS:
                if pattern["label"] not in col_norm:
                    continue
                numbers = _BRL_NUMBER_RE.findall(col_text)
                values = [
                    v for raw in numbers
                    for v in (parse_brl(raw),)
                    if not (v != v) and v > 0 and v < 10000  # NaN guard + range
                ]
                for v in values:
                    result.append(Transaction(
                        statement_id=statement_id,
                        statement_key=statement_info.statement_key,
                        purchase_date=last_date,
                        purchase_day=last_date[:2],
                        purchase_month=last_date[3:5],
                        merchant=pattern["merchant"],
                        raw_merchant=pattern["merchant"],
                        value=v,
                        category="Impostos",
                        is_installment=False,
                        installment_current=None,
                        installment_total=None,
                    ))
                break

    return result


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def parse_pdf(
    pdf_bytes: bytes,
    source_file: str,
    rules: Optional[list[CategoryRule]] = None,
    statement_id: int = 0,
) -> ParseResult:
    """
    Parse a Nubank PDF statement from raw bytes.

    Args:
        pdf_bytes:    Raw PDF content (never stored).
        source_file:  Original filename for metadata only.
        rules:        Category rules sorted by priority ascending.
                      Defaults to DEFAULT_CATEGORY_RULES.
        statement_id: FK value to stamp on each Transaction (0 = not yet persisted).

    Returns:
        ParseResult with statement_info, official_total, transactions list, checksum.
    """
    if rules is None:
        rules = DEFAULT_CATEGORY_RULES

    checksum = hashlib.sha256(pdf_bytes).hexdigest()

    import io
    rows = _extract_rows(io.BytesIO(pdf_bytes))  # pdfplumber.open accepts file-like objects

    statement_info = _extract_statement_info(rows, source_file)
    official_total = _extract_official_total(rows)
    lines = _extract_transaction_lines(rows)

    transactions = _parse_transactions(lines, statement_info, source_file, rules, statement_id)
    tax_transactions = _extract_tax_transactions(rows, statement_info, source_file, statement_id)

    all_transactions = transactions + tax_transactions

    return ParseResult(
        statement_info=statement_info,
        official_total=official_total,
        transactions=all_transactions,
        checksum=checksum,
    )
