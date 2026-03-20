"""
capture_baseline.py — generate the 2025 golden baseline snapshot.

Run once against the current state of the legacy Python parser (which mirrors
the JS behaviour verified in the smoke test). Output is saved to:
    tests/baseline/golden_2025.json

This file is the canonical acceptance gate for the migration.
If the backend ever produces totals that diverge beyond TOLERANCE, the
compare_baseline.py script will fail with a non-zero exit code.

Usage:
    cd backend
    ../.venv/Scripts/python.exe scripts/capture_baseline.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
PDFS_DIR = REPO_ROOT / "pdfs"
BASELINE_DIR = BACKEND_DIR / "tests" / "baseline"
BASELINE_FILE = BASELINE_DIR / "golden_2025.json"

sys.path.insert(0, str(BACKEND_DIR))

from src.infrastructure.parser.pdf_parser import DEFAULT_CATEGORY_RULES, parse_pdf

TOLERANCE = 0.01  # BRL


def main() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(PDFS_DIR.glob("2025-*.pdf"))
    if not pdfs:
        print(f"ERROR: No 2025 PDFs found in {PDFS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Capturing baseline for {len(pdfs)} PDFs in {PDFS_DIR}")

    periods: dict = {}

    for pdf_path in pdfs:
        pdf_bytes = pdf_path.read_bytes()
        result = parse_pdf(pdf_bytes, pdf_path.name, rules=DEFAULT_CATEGORY_RULES)
        si = result.statement_info
        txs = result.transactions

        parsed_total = round(sum(t.value for t in txs), 2)
        debit_count = sum(1 for t in txs if t.value > 0)
        credit_count = sum(1 for t in txs if t.value <= 0)

        # Per-category totals (rounded individually)
        categories: dict[str, float] = {}
        for t in txs:
            categories[t.category] = round(categories.get(t.category, 0.0) + t.value, 2)

        periods[si.statement_key] = {
            "source_file": pdf_path.name,
            "statement_label": si.label,
            "official_total": result.official_total,
            "parsed_total": parsed_total,
            "diff": round(result.official_total - parsed_total, 2),
            "transaction_count": len(txs),
            "debit_count": debit_count,
            "credit_count": credit_count,
            "categories": dict(sorted(categories.items())),
        }

        status = "OK" if abs(result.official_total - parsed_total) <= TOLERANCE else "MISMATCH"
        print(
            f"  {si.statement_key}  official={result.official_total:>10.2f}"
            f"  parsed={parsed_total:>10.2f}  tx={len(txs):>3}  {status}"
        )

    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "tolerance": TOLERANCE,
        "pdf_count": len(pdfs),
        "periods": periods,
    }

    BASELINE_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nBaseline saved -> {BASELINE_FILE}")

    mismatches = [k for k, v in periods.items() if abs(v["diff"]) > TOLERANCE]
    if mismatches:
        print(f"\nWARNING: {len(mismatches)} period(s) have official/parsed mismatch > {TOLERANCE}:")
        for k in mismatches:
            print(f"  {k}: diff={periods[k]['diff']}")
    else:
        print("All periods reconcile within tolerance.")


if __name__ == "__main__":
    main()
