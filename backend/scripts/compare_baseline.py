"""
compare_baseline.py — acceptance gate for the migration.

Runs the backend parser against all 2025 PDFs and compares the output
against the golden snapshot captured by capture_baseline.py.

Exit codes:
    0 — all periods match within tolerance  ← migration passes
    1 — one or more divergences found       ← migration FAILS

Usage:
    cd backend
    ../.venv/Scripts/python.exe scripts/compare_baseline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
PDFS_DIR = REPO_ROOT / "pdfs"
BASELINE_FILE = BACKEND_DIR / "tests" / "baseline" / "golden_2025.json"

sys.path.insert(0, str(BACKEND_DIR))

from src.infrastructure.parser.pdf_parser import DEFAULT_CATEGORY_RULES, parse_pdf


def _compare_value(label: str, expected: float, actual: float, tolerance: float) -> list[str]:
    diff = abs(expected - actual)
    if diff > tolerance:
        return [f"  {label}: expected={expected:.2f}  actual={actual:.2f}  diff={diff:.2f}"]
    return []


def main() -> None:
    if not BASELINE_FILE.exists():
        print(f"ERROR: Baseline file not found: {BASELINE_FILE}")
        print("Run scripts/capture_baseline.py first.")
        sys.exit(1)

    snapshot = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    tolerance: float = snapshot.get("tolerance", 0.01)
    golden: dict = snapshot["periods"]

    pdfs = sorted(PDFS_DIR.glob("2025-*.pdf"))
    if not pdfs:
        print(f"ERROR: No 2025 PDFs found in {PDFS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Comparing {len(pdfs)} PDFs against baseline (tolerance={tolerance})")
    print(f"Baseline captured at: {snapshot.get('captured_at', 'unknown')}\n")

    all_failures: list[str] = []

    for pdf_path in pdfs:
        pdf_bytes = pdf_path.read_bytes()
        result = parse_pdf(pdf_bytes, pdf_path.name, rules=DEFAULT_CATEGORY_RULES)
        si = result.statement_info
        txs = result.transactions
        key = si.statement_key

        if key not in golden:
            print(f"  {key}  SKIP (not in baseline)")
            continue

        expected = golden[key]
        parsed_total = round(sum(t.value for t in txs), 2)
        failures: list[str] = []

        # Totals
        failures += _compare_value(
            f"{key}.official_total",
            expected["official_total"],
            result.official_total,
            tolerance,
        )
        failures += _compare_value(
            f"{key}.parsed_total",
            expected["parsed_total"],
            parsed_total,
            tolerance,
        )

        # Transaction count (exact match)
        if len(txs) != expected["transaction_count"]:
            failures.append(
                f"  {key}.transaction_count: expected={expected['transaction_count']}"
                f"  actual={len(txs)}"
            )

        # Per-category totals
        actual_cats: dict[str, float] = {}
        for t in txs:
            actual_cats[t.category] = round(actual_cats.get(t.category, 0.0) + t.value, 2)

        all_cats = set(expected.get("categories", {}).keys()) | set(actual_cats.keys())
        for cat in sorted(all_cats):
            exp_val = expected.get("categories", {}).get(cat, 0.0)
            act_val = actual_cats.get(cat, 0.0)
            failures += _compare_value(f"{key}.categories.{cat}", exp_val, act_val, tolerance)

        if failures:
            print(f"  {key}  FAIL")
            all_failures.extend(failures)
        else:
            print(f"  {key}  OK  tx={len(txs)}  parsed={parsed_total:.2f}")

    print()
    if all_failures:
        print(f"BASELINE COMPARISON FAILED — {len(all_failures)} divergence(s):")
        for f in all_failures:
            print(f)
        sys.exit(1)
    else:
        print("BASELINE COMPARISON PASSED - migration is numerically equivalent.")
        sys.exit(0)


if __name__ == "__main__":
    main()
