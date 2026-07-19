"""
Phase 03, Step 01 — analysis-ready data inventory + structural verification.

Goal:
    Load the Phase 02 analysis-ready inputs, confirm their shapes/coverage and
    the region-key alignment across yield (region name) and climate
    (aagis_code) products, and persist an inventory table — establishing a
    verified data baseline before any substantive EDA or the optional-crop
    decision.

Outputs:
    outputs/tables/s01_input_inventory.csv   (committed, small)

Exit code:
    0 if every product is present, all row counts match, and all structural
    invariants hold; 1 otherwise.

Run from repo root:
    python scripts/phase03_s01_data_inventory.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# sys.path injection
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.log_utils import error, log, ok, section, subsection, warn  # noqa: E402
from src.processing.input_inventory import (  # noqa: E402
    build_inventory,
    check_invariants,
    load_products,
    reliable_yield_summary,
    write_inventory,
)


def main() -> int:
    section("Phase 03 - Step 01: analysis-ready input inventory")

    subsection("Product inventory")
    inv = build_inventory()
    for r in inv.itertuples(index=False):
        status = "OK  " if (r.exists and r.row_ok) else "!!  "
        exp = "" if r.expected_rows is None else f" (exp {r.expected_rows})"
        log(f"  {status}{r.product:<18s} rows={str(r.n_rows):>6s}{exp:<12s} {r.path}")
    missing = inv[~inv["exists"]]
    bad_rows = inv[inv["exists"] & ~inv["row_ok"]]

    subsection("Structural invariants")
    products = load_products()
    checks = check_invariants(products)
    n_fail = 0
    for c in checks:
        if c.ok:
            ok(f"  {c.name}: {c.detail}")
        else:
            warn(f"  {c.name}: {c.detail}")
            n_fail += 1

    subsection("Reliable yield windows (informational)")
    for r in reliable_yield_summary(products).itertuples(index=False):
        log(
            f"  {r.commodity:<7s} {r.min_year}-{r.max_year}  reliable>={r.reliable_start}  "
            f"non-NA yield={r.non_na_yield}  pre-window rows={r.pre_window_rows} "
            f"(non-NA {r.pre_window_non_na_yield})"
        )

    out = write_inventory(inv)

    subsection("Result")
    if len(missing):
        error(f"missing products: {missing['product'].tolist()}")
    if len(bad_rows):
        error(f"row-count mismatch: {bad_rows['product'].tolist()}")
    if len(missing) or len(bad_rows) or n_fail:
        error(
            f"inventory FAILED: {len(missing)} missing, "
            f"{len(bad_rows)} row-mismatch, {n_fail} invariant failures"
        )
        return 1
    ok(f"inventory PASSED: {len(inv)} products, all invariants green. Wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
