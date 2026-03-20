# Dashboard de Gastos

A frontend + FastAPI app for visualising Nubank credit card statements.

## Quick start

### Option 1: Run Task (recommended)

1. Open Command Palette (`Ctrl+Shift+P`).
2. Run `Tasks: Run Task`.
3. Select `py run dev`.

This starts the frontend on `http://localhost:5500/index.html` and the backend API on `http://127.0.0.1:8000`.

### Option 2: Manual run

From the project root:

```powershell
# 1) Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2) Install backend dependencies (first time only)
cd backend
pip install -r requirements.txt

# 3) Start FastAPI backend
..\.venv\Scripts\python.exe -m uvicorn src.interface.main:app --reload --port 8000
```

In a second terminal (project root), start the frontend server:

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

Open `http://localhost:5500/index.html` in your browser.

---

## Tech stack

| Layer | What |
|-------|------|
| Structure | HTML5 |
| Style | CSS3 — custom properties, Grid/Flexbox (`styles/style.css`) |
| Logic | Vanilla JS (ES2020+) |
| PDF reading | [PDF.js](https://mozilla.github.io/pdf.js/) (Mozilla) via CDN |
| Charts | [Chart.js](https://www.chartjs.org/) via CDN |
| Input mask | jQuery + jquery.mask (currency fields only) |
| Persistence | `localStorage` — rules, fixed costs/income, theme preference |
| File loading | `fetch()` for auto-load from `pdfs/`; File API for manual upload |

---

## How PDF data extraction works

### 1. Load
On startup, the app calls `fetch()` for every `pdfs/YYYY-MM.pdf` candidate from Jan 2023 to the current month. Files that don't exist return a 404 and are silently skipped. If nothing loads, a manual upload button appears.

### 2. Render to text rows
PDF.js renders each page and returns positioned text items. The app groups them into **two-column rows** by comparing the horizontal (x) midpoint of each item against the page width — left column and right column are tracked independently. This mirrors the physical layout of a Nubank statement.

### 3. Identify the statement period
The app searches the rows for a line matching `Postagem: DD/MM/YYYY` (the bill posting date). That date's month/year becomes the canonical statement key (e.g. `2025-11`), independent of the file name.

### 4. Locate transaction sections
Each column is scanned for section headers:
- **`Compras e saques`** → opens the current-month transaction section
- **`Compras parceladas`** → marks a future-instalment section (skipped)
- **`Encargos cobrados nesta fatura`** → closes the section

Only rows that are **inside an open section**, **start with a DD/MM date**, and are **not** in the future-instalment section are kept.

### 5. Parse each line
Every kept line is matched against the regex:
```
/^(\d{2}\/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})$/
```
This extracts: `purchaseDate`, `merchant`, `value (BRL)`.  
Instalment notation (`02/06`) inside the merchant name is detected separately and stored as `installmentCurrent / installmentTotal`.

### 6. Extract taxes
Lines like `Repasse de IOF` and `Total de encargos` have no date, so they bypass the regex above. A separate pass catches them by keyword, borrows the last seen date, and adds them as `category: "Impostos"`.

### 7. Categorise
Each merchant is run through a keyword-rule list (editable in the Categorias tab, persisted in `localStorage`). First match wins; no match → `"Outros"`.

### 8. Reconcile
The app also extracts the **`Valor da fatura atual`** total printed in the PDF and compares it against the sum of all parsed transactions. The diff is shown per file in the Arquivos tab to catch any parsing gaps.

---

## File structure

```
index.html          main app
styles/
  style.css         all CSS (light + dark theme)
pdfs/
  YYYY-MM.pdf       monthly statements (auto-loaded)
index.checkpoint-*.html   saved snapshots
```
