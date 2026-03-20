# Tech Stack

## App Purpose and Scope

Local credit card statement dashboard for Nubank PDF files.  
Single user, offline-first, running on localhost. No authentication, no public exposure.

**Hard scope boundaries:**

- PDF files are **never stored** in the backend — bytes are processed in-memory and discarded after parsing.
- **Import once**: duplicate imports are rejected via SHA-256 checksum of the uploaded file.
- **Hard delete cascade**: deleting an imported statement removes all associated transactions with no recovery path.

---

## Technology Choices

| Concern | Technology | Why for this app |
|---------|-----------|-----------------|
| Backend framework | FastAPI (Python 3.11+) | Async support, auto-generated docs, type safety via Pydantic, excellent testing story |
| Database | SQLite (single local file) | Zero-config, single user, file-portable, sufficient for &lt;50K transactions |
| ORM | SQLAlchemy (ORM + Core) | Isolated in infrastructure layer; enables DB swap without touching domain logic |
| PDF parser | pdfplumber | Column-aware positional text extraction; x/y coordinates match the JS `viewport * 0.57` column split |
| Tests | pytest + pytest-cov | Simple, no boilerplate, de-facto Python standard |
| Frontend (current) | Vanilla HTML/JS + pdf.js + Chart.js + jQuery | Preserved unchanged during migration phases; browser-only rendering |

---

## Architecture Pattern

**Clean Architecture** (Onion variant) with **DDD-lite** and the **Repository Pattern**.

### Layers (inner → outer)

| Layer | Responsibility | Allowed imports |
|-------|---------------|-----------------|
| Domain | Entities, value objects, repository *interfaces* | Pure Python only |
| Application | Use cases orchestrating domain logic via repository interfaces | Domain layer only |
| Infrastructure | SQLAlchemy models, concrete repos, PDF parser | Domain + SQLAlchemy + pdfplumber |
| Interface (HTTP) | FastAPI routers, Pydantic request/response DTOs | Application layer only |

**Stability rule:** Repository *interfaces* live in the domain layer and are the **immovable boundary**.  
SQLAlchemy internals must never leak past the infrastructure layer.

---

## Critical Product Rules

| Rule | Enforcement point |
|------|------------------|
| No raw PDF storage | Parser receives bytes in memory; nothing written to disk or DB |
| Import once | SHA-256 checksum stored on `ImportedStatement`; duplicate check before any write |
| Hard delete cascade | SQLAlchemy `cascade="all, delete-orphan"` + DB-level `ON DELETE CASCADE` FK on `Transaction` |
| App UI language | PT-BR (unchanged throughout migration) |
| Documentation language | en-US (aligned with README.md) |

---

## Code Conventions

- **Naming**: `snake_case` everywhere; entity field names mirror the ubiquitous language.
- **Ubiquitous language**: use `ImportedStatement` (not `File`), `Transaction` (not `Entry`), `checksum` (not `hash`), `cascade delete` (not `wipe`), `statement_key` (not `period`).
- **Repository pattern**: all DB access through interface methods; no raw `session.query()` outside the infrastructure layer.
- **Use cases are imperative**: `ImportStatementUseCase.execute()`, not `create_statement()`.
- **No soft delete**: simplifies the data model and enforces explicit user intent.
- **Pydantic DTOs only in the interface layer**: domain entities are plain Python dataclasses.
- **Pytest fixtures in `conftest.py`**: shared in-memory SQLite session for all repository tests.

---

## Quality Gates (Mandatory)

| Gate | How it is enforced |
|------|-------------------|
| Unit tests | Every use case and repository must have covering tests; run with `pytest backend/tests/` |
| 2025 golden baseline | Legacy JS parser output for all 2025 PDFs is captured as `tests/baseline/golden_2025.json`; backend must match within BRL 0.01 tolerance per period |
| Baseline comparator | `scripts/compare_baseline.py` is the explicit migration acceptance test; migration is **not** complete until it passes |
