# Architecture

## Overview

The migration is **incremental** — the existing single-page HTML app continues working at every phase.  
The FastAPI backend is introduced alongside it and absorbs responsibilities one layer at a time.

---

## Layer Diagram

```
┌──────────────────────────────────────────────────────────┐
│  Interface (HTTP)                                        │
│  FastAPI routers · Pydantic request/response DTOs        │
│  Translates HTTP ↔ use cases; knows nothing about SQL    │
├──────────────────────────────────────────────────────────┤
│  Application                                             │
│  Use cases orchestrate domain logic                      │
│  ImportStatementUseCase · DeleteStatementUseCase         │
│  ListStatementsUseCase · ListTransactionsUseCase         │
├──────────────────────────────────────────────────────────┤
│  Domain                                                  │
│  Entities · Repository Interfaces (Protocols)            │
│  ImportedStatement · Transaction                         │
│  CategoryRule · FixedCost · FixedIncome                  │
├──────────────────────────────────────────────────────────┤
│  Infrastructure                                          │
│  SQLAlchemy ORM models (with CASCADE FK)                 │
│  Concrete repository implementations                     │
│  PDF parser (pdfplumber — ports JS extraction logic)     │
└──────────────────────────────────────────────────────────┘
```

---

## Domain Entities

### `ImportedStatement`

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | PK, auto-increment |
| `statement_key` | str | `YYYY-MM` — canonical period identifier |
| `statement_month` | str | `MM` (e.g. `"11"`) |
| `statement_year` | str | `YYYY` |
| `statement_label` | str | Human-readable label (e.g. `"Novembro/2025"`) |
| `source_file` | str | Original filename; **no binary content stored** |
| `checksum` | str | SHA-256 of uploaded PDF bytes; unique constraint enforces import-once |
| `official_total` | float | `Valor da fatura atual` extracted from PDF |
| `parsed_total` | float | Sum of all parsed transaction values |
| `transaction_count` | int | Row count convenience field |
| `imported_at` | datetime | UTC timestamp |

### `Transaction`

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | PK |
| `statement_id` | int | FK → `ImportedStatement.id` with `ON DELETE CASCADE` |
| `statement_key` | str | Denormalised copy for query filters |
| `purchase_date` | str | `DD/MM` as-is from PDF |
| `purchase_day` | str | `DD` |
| `purchase_month` | str | `MM` |
| `merchant` | str | Cleaned merchant name (installment notation stripped) |
| `raw_merchant` | str | Original extracted text |
| `value` | float | Positive = debit; negative = credit or reversal |
| `category` | str | Assigned category |
| `is_installment` | bool | True when merchant contains `NN/TT` pattern |
| `installment_current` | int? | e.g. `2` from `02/06` |
| `installment_total` | int? | e.g. `6` from `02/06` |

### `CategoryRule`

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | PK |
| `keyword` | str | Case-insensitive substring match |
| `category` | str | Target category label |
| `priority` | int | Lower value = higher priority; custom rules precede defaults |
| `is_default` | bool | `False` = user-added; `True` = seeded from `DEFAULT_CATEGORY_RULES` |

### `FixedCost` / `FixedIncome`

| Field | Type |
|-------|------|
| `id` | int |
| `label` | str |
| `amount` | float |

---

## Repository Interfaces

Interfaces live in the **domain layer** as `typing.Protocol` classes.  
Concrete implementations live in the **infrastructure layer** only.

```python
# domain/repositories.py (simplified)

class StatementRepository(Protocol):
    def find_by_checksum(self, checksum: str) -> Optional[ImportedStatement]: ...
    def save(self, statement: ImportedStatement, transactions: list[Transaction]) -> ImportedStatement: ...
    def list_all(self) -> list[ImportedStatement]: ...
    def find_by_id(self, statement_id: int) -> Optional[ImportedStatement]: ...
    def delete(self, statement_id: int) -> None: ...

class TransactionRepository(Protocol):
    def list_filtered(self, filters: TransactionFilters) -> list[Transaction]: ...

class SettingsRepository(Protocol):
    def get_category_rules(self) -> list[CategoryRule]: ...
    def save_category_rules(self, rules: list[CategoryRule]) -> None: ...
    def get_fixed_costs(self) -> list[FixedCost]: ...
    def save_fixed_costs(self, costs: list[FixedCost]) -> None: ...
    def get_fixed_income(self) -> list[FixedIncome]: ...
    def save_fixed_income(self, income: list[FixedIncome]) -> None: ...
```

---

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/statements/import` | **MVP** | Upload PDF bytes; compute checksum, parse, persist atomically. Returns statement summary + tx count. |
| `GET` | `/statements` | **MVP** | List all imported statements with `official_total`, `parsed_total`, `diff`, `transaction_count`. |
| `DELETE` | `/statements/{id}` | **MVP** | Hard delete statement + all its transactions via DB cascade. Returns 204. |
| `GET` | `/transactions` | **MVP** | Filtered, sorted, paginated transaction list. Query params: `statement_key`, `category`, `purchase_month`, `min_value`, `max_value`, `credits_only`, `page`, `page_size`, `sort_col`, `sort_dir`. |
| `GET` | `/settings/category-rules` | **MVP** | Active rules ordered by priority (custom first, then defaults). |
| `PUT` | `/settings/category-rules` | **MVP** | Replace full category rules list. |
| `GET` | `/settings/fixed-costs` | **MVP** | Fixed costs list (migrated from localStorage). |
| `PUT` | `/settings/fixed-costs` | **MVP** | Replace fixed costs. |
| `GET` | `/settings/fixed-income` | **MVP** | Fixed income entries. |
| `PUT` | `/settings/fixed-income` | **MVP** | Replace fixed income. |
| `POST` | `/statements/{id}/reprocess` | **Next Phase** | Re-categorise all transactions using the current active rules set. |
| `POST` | `/statements/{id}/replace` | **Next Phase** | Upload replacement PDF for an existing period; atomically replace all transactions. |
| `GET` | `/statements/{id}/audit` | **Future** | History of reprocessing events and category changes. |
| `GET` | `/analytics/averages` | **Future** | Cost-of-living averages (monthly / annual) computed server-side. |

---

## HTTP Status Codes

| Code | Meaning in this API |
|------|---------------------|
| 200 | OK — list or get |
| 201 | Created — successful import |
| 204 | No Content — successful delete |
| 409 | Conflict — duplicate PDF (checksum already exists) |
| 404 | Not Found — statement id does not exist |
| 422 | Unprocessable Entity — Pydantic validation failure |
| 500 | Internal Server Error — parser failure or unexpected DB error |

---

## Key Flows

### Import Flow

```
POST /statements/import  (multipart PDF upload)
  │
  ├─ Compute SHA-256 of PDF bytes
  ├─ StatementRepository.find_by_checksum() → 409 Conflict if already imported
  │
  ├─ PDF Parser (pdfplumber)
  │   ├─ For each page: collect items with (x, y, text)
  │   ├─ Column split at x = page_width × 0.57
  │   │     left column  → x < split
  │   │     right column → x ≥ split
  │   ├─ Group items by Y coordinate (tolerance: 2 pt)
  │   ├─ Sort rows top-to-bottom (descending Y within page)
  │   ├─ Detect statement period from "Postagem: DD/MM/YYYY" line
  │   ├─ Extract official total from "Valor da fatura atual" line
  │   ├─ State machine per column:
  │   │     OPEN  on "Compras e saques"
  │   │     SKIP  on "Compras parceladas" (future instalments)
  │   │     CLOSE on "Encargos cobrados nesta fatura"
  │   ├─ Regex parse kept lines:
  │   │     ^(\d{2}\/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})$
  │   └─ Separate pass: IOF / tax lines without DD/MM date
  │
  ├─ Categorise each transaction
  │     custom rules (priority order) → default rules → "Outros"
  │
  ├─ StatementRepository.save()  [atomic: statement + all transactions]
  └─ Return 201 with ImportedStatement summary DTO
```

### Delete Flow

```
DELETE /statements/{id}
  │
  ├─ StatementRepository.find_by_id() → 404 if not found
  ├─ StatementRepository.delete()
  │   └─ DB CASCADE: Transaction rows removed automatically (ON DELETE CASCADE FK)
  └─ Return 204 No Content
```

### Categorisation Rules

- Custom user rules take **priority** over defaults (lower `priority` value = higher rank).
- First match wins; rules are evaluated in order.
- Comparison: lowercase + whitespace-normalised merchant name vs keyword.
- Backend seeds `DEFAULT_CATEGORY_RULES` at startup if the table is empty.

---

## Testing Strategy

### Unit tests (mandatory)

| File | Coverage target |
|------|----------------|
| `tests/test_import_use_case.py` | Success path, duplicate rejection (409), parser failure, DB rollback |
| `tests/test_delete_use_case.py` | Success, not-found 404, cascade confirmed (no orphan transactions) |
| `tests/test_statement_repo.py` | Create, list, delete, duplicate checksum guard |

All tests use an in-memory SQLite session via a shared `conftest.py` fixture.

### Golden baseline gate (mandatory)

| Step | Script |
|------|--------|
| Capture legacy output | `scripts/capture_baseline.py` — runs JS-equivalent parser on all 2025 PDFs, writes `tests/baseline/golden_2025.json` |
| Compare backend output | `scripts/compare_baseline.py` — runs backend pipeline on same files, diffs per-period totals, per-category totals, transaction counts |
| Tolerance | BRL 0.01 per compared value |
| Pass criterion | Zero divergences beyond tolerance; migration is **not** complete until this passes |

---

## Migration Phases

| Phase | Backend change | Frontend change |
|-------|---------------|-----------------|
| 1 — Backend MVP | Scaffold, parser, import/list/delete endpoints, unit tests, 2025 baseline capture | **None** — HTML app still works standalone |
| 2 — Settings persistence | Category rules, fixed costs, fixed income backed by DB | Settings tab calls API; localStorage ignored except `dashboard-theme` |
| 3 — Import via API | Frontend drops pdf.js import path; uses `POST /statements/import` | Arquivos tab redesigned; upload via `<form>` to API |
| 4 — Full API-driven frontend | Transactions fetched from `GET /transactions`; in-memory JS state removed | All filtering, sorting, pagination driven by API query params |

---

## Architectural Decision Records

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | SQLite over PostgreSQL | Single-user local app; zero infrastructure overhead |
| 2 | SQLAlchemy isolated to infrastructure layer | Domain stays framework-free; future DB swap is a single layer change |
| 3 | No soft delete | Simplifies schema; destruction is explicit user intent |
| 4 | pdfplumber over PyMuPDF | Column-aware positional extraction matches the JS `viewport.width × 0.57` behaviour |
| 5 | SHA-256 checksum for import dedup | Deterministic, content-based; robust to file renames |
| 6 | DDD-lite over full DDD | Scope does not justify bounded contexts, domain events, or full aggregates |
| 7 | Pydantic DTOs in interface layer only | Prevents framework coupling inside domain and application layers |
| 8 | 2025 golden baseline as acceptance gate | Ensures Python parser is numerically equivalent to JS parser before any frontend cutover |
