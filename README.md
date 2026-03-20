# Freefin Finance

> A local-first personal finance dashboard for analysing Nubank credit card statements — no cloud, no tracking, no nonsense.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003b57?logo=sqlite&logoColor=white)
![Vanilla JS](https://img.shields.io/badge/Frontend-Vanilla%20JS-f7df1e?logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

---

## Overview

Freefin Finance parses your bank (Itau only so far) monthly PDF statements, stores the transactions in a local SQLite database, and gives you an interactive dashboard to explore your spending — by category, by month, or across all time.

Everything runs on `localhost`. Your PDF files are never stored on disk; bytes are processed in memory and discarded after parsing. No account, no subscription, no data leaves your machine.

It only works with credit card bills that are already closed.

---

## AI Learning Project Notice

This repository is an AI-only coding experiment built to learn how to design, implement, and iterate software using AI tools and agents.

All code was generated with AI assistance (no manual coding), and the result is a working, practical and useful application.

No line of code in this project was written by hand.

---

## Features

- **File upload import** — upload PDFs via the Arquivos tab; the backend parses the bytes in memory and stores transactions in SQLite
- **Auto-seed from `pdfs/`** — on first run with an empty database, the app fetches any `YYYY-MM.pdf` files it finds in the `pdfs/` folder and imports them automatically (also used as fallback when the backend is offline)
- **Reconciliation** — parsed transaction totals are compared against the printed statement total to surface any parsing gaps
- **Dark / light theme** — preference persisted in `localStorage`
- **REST API** — FastAPI backend with auto-generated docs at `http://localhost:8000/docs`

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Architecture](#architecture)
- [License](#license)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| pip | latest |

> A `.venv/` virtual environment must be created at the project root before running the app.

---

## Quick Start

### Option 1: VS Code Task (recommended)

1. Open the Command Palette — `Ctrl+Shift+P`
2. Run **Tasks: Run Task**
3. Select **`py run dev`**

The frontend starts at `http://localhost:5500/index.html` and the backend API at `http://127.0.0.1:8000`.

---

### Option 2: Manual Setup

**Create and activate the virtual environment** (once, from the project root):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Install backend dependencies** (once, from `backend/`):

```powershell
cd backend
pip install -r requirements.txt
cd ..
```

**Start the backend** (from `backend/`):

```powershell
..\.venv\Scripts\python.exe -m uvicorn src.interface.main:app --reload --port 8000
```

**Start the frontend** (from the project root, in a separate terminal):

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

Open `http://localhost:5500/index.html` in your browser.

---

## API Reference

Interactive docs are available at `http://localhost:8000/docs` once the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/statements/import` | Upload a PDF, parse it, and persist transactions |
| `GET` | `/api/statements` | List all imported statements with totals and diff |
| `DELETE` | `/api/statements/{id}` | Hard delete a statement and all its transactions |
| `GET` | `/api/transactions` | Filtered, sorted, paginated transaction list |
| `GET` | `/api/settings/category-rules` | List category rules ordered by priority |
| `PUT` | `/api/settings/category-rules` | Atomically replace all category rules |
| `GET` | `/api/settings/fixed-costs` | List fixed cost entries |
| `PUT` | `/api/settings/fixed-costs` | Atomically replace fixed cost entries |
| `GET` | `/api/settings/fixed-income` | List fixed income entries |
| `PUT` | `/api/settings/fixed-income` | Atomically replace fixed income entries |
| `GET` | `/health` | Health check |

---

## Project Structure

```
├── index.html                  # Single-page frontend app
├── styles/
│   └── style.css               # All CSS — light + dark themes
├── pdfs/
│   └── YYYY-MM.pdf             # Optional: PDFs here are auto-imported on first run / offline fallback
├── backend/
│   ├── requirements.txt
│   ├── src/
│   │   ├── domain/             # Entities + repository interfaces
│   │   ├── application/        # Use cases (ImportStatement, DeleteStatement, …)
│   │   ├── infrastructure/     # SQLAlchemy ORM, repositories, PDF parser
│   │   └── interface/          # FastAPI app, routers, Pydantic DTOs
│   └── tests/                  # Pytest suite + golden baseline
└── docs/
    ├── ARCHITECTURE.md
    ├── TECHSTACK.md
    └── SETUP.md                # Detailed setup & PDF extraction internals
```

---

## Running Tests

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/ -v --cov=src
```

The test suite includes:
- Unit tests for every use case and repository
- A **golden baseline** check (`tests/baseline/golden_2025.json`) that validates the Python PDF parser matches the original JavaScript output within BRL 0.01 tolerance per statement period

---

## Architecture

Freefin Finance follows **Clean Architecture** (Onion variant) with the Repository pattern:

```
Interface (FastAPI routers + Pydantic DTOs)
    ↓
Application (use cases — pure Python, no framework)
    ↓
Domain (entities + repository interfaces — no external dependencies)
    ↑
Infrastructure (SQLAlchemy ORM, SQLite, pdfplumber)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/TECHSTACK.md](docs/TECHSTACK.md) for full details.

---

## License

MIT
