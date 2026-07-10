"""
Phase 01, Step 04 - SILO gridded climate data ingestion.

Goal:
    Retrieve SILO 0.05 deg daily gridded climate data for 6 variables
    across 1961-2024, apply the broadacre cropping mask from s03, and
    persist masked NetCDF files at data/processed/silo/<variable>/<year>.nc.

Variable-specific effective periods:
    evap_pan: 1970 onward only (pre-1970 is climatological long-term
    average per SILO, not observed data; included would introduce a
    structural break at 1970).

Prereqs:
    - Phase 01 Step 03 complete (cropping_mask.nc at data/processed/)

Idempotency:
    - Already-completed (variable, year) pairs: skipped (masked output exists).
    - Pre-effective-year pairs (e.g. evap_pan 1961-1969): skipped without
      download, regardless of whether output exists.

Run from repo root:
    python scripts/phase01_s04_ingest_silo.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# sys.path injection (same pattern as phase01_s02, s03)
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.paths import DATA_RAW, DATA_PROCESSED
from src.log_utils import log, ok, warn, error, section, subsection
from src.ingestion.silo import (
    ingest_all,
    load_cropping_mask,
    SILO_VARIABLES,
    SILO_VARIABLE_EFFECTIVE_START,
    SILO_YEAR_MIN_DEFAULT,
    SILO_YEAR_MAX_DEFAULT,
)


def _fmt_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024.0
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}"
    return f"{n:.2f} TB"


def main() -> int:
    section("Phase 01, Step 04 - SILO gridded climate data ingestion")

    mask_nc = DATA_PROCESSED / "cropping_mask.nc"
    raw_dir = DATA_RAW
    processed_dir = DATA_PROCESSED

    log(f"Cropping mask:   {mask_nc}")
    log(f"Raw dir:         {raw_dir}/silo/<var>/<year>.<var>.nc (transient)")
    log(f"Processed dir:   {processed_dir}/silo/<var>/<year>.<var>.nc (persistent)")
    log(f"Variables (n=6): {list(SILO_VARIABLES.keys())}")
    log(f"Year range:      {SILO_YEAR_MIN_DEFAULT}-{SILO_YEAR_MAX_DEFAULT}")
    if SILO_VARIABLE_EFFECTIVE_START:
        log("Variable-specific effective start years (Master-grade discipline):")
        for var, yr in SILO_VARIABLE_EFFECTIVE_START.items():
            log(
                f"  {var}: effective from {yr} (pre-{yr} is long-term-average, skipped)"
            )

    if not mask_nc.exists():
        error(f"Cropping mask not found at {mask_nc}. Run phase01_s03 first.")
        return 1

    # ----- (1) Load cropping mask -------------------------------------
    subsection("1. Load cropping mask (cropping_mask_t005)")
    mask = load_cropping_mask(mask_nc, variable_name="cropping_mask_t005")
    n_true = int(mask.sum())
    n_total = mask.size
    log(f"  mask shape: {mask.shape}")
    log(f"  cropping cells: {n_true:,} ({100.0 * n_true / n_total:.3f}% of grid)")
    ok("Mask loaded")

    # ----- (2) Ingest all (variable, year) ---------------------------
    subsection(
        f"2. Sequentially ingest {len(SILO_VARIABLES)} variables x "
        f"{SILO_YEAR_MAX_DEFAULT - SILO_YEAR_MIN_DEFAULT + 1} years"
    )
    log("Each annual file: download (~410 MB) -> mask -> persist -> delete raw.")
    log("File-level idempotent: previously-completed (var, year) pairs are skipped.")
    log(
        "Pre-effective-year pairs (e.g. evap_pan 1961-1969) are skipped without download."
    )

    summary = ingest_all(
        variables=tuple(SILO_VARIABLES.keys()),
        year_min=SILO_YEAR_MIN_DEFAULT,
        year_max=SILO_YEAR_MAX_DEFAULT,
        mask_da=mask,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        delete_raw=True,
    )

    # ----- (3) Per-variable summary ----------------------------------
    subsection("3. Per-variable summary")
    log(
        f"  {'variable':<12s} {'done':>5s} {'skip-done':>10s} {'skip-preeff':>12s} "
        f"{'errors':>7s} {'masked_total':>14s}"
    )
    total_done = 0
    total_skip_done = 0
    total_skip_pre = 0
    total_errors = 0
    total_masked_bytes = 0
    for variable, stats in summary.items():
        log(
            f"  {variable:<12s} {stats['done']:>5d} "
            f"{stats['skipped_already_done']:>10d} "
            f"{stats['skipped_pre_effective']:>12d} "
            f"{len(stats['errors']):>7d} "
            f"{_fmt_bytes(stats['masked_bytes']):>14s}"
        )
        total_done += stats["done"]
        total_skip_done += stats["skipped_already_done"]
        total_skip_pre += stats["skipped_pre_effective"]
        total_errors += len(stats["errors"])
        total_masked_bytes += stats["masked_bytes"]

    log("")
    log(f"  Total succeeded (this run):       {total_done}")
    log(f"  Total skipped (already done):     {total_skip_done}")
    log(f"  Total skipped (pre-effective):    {total_skip_pre}")
    log(f"  Total errors:                     {total_errors}")
    log(f"  Total masked disk usage:          {_fmt_bytes(total_masked_bytes)}")

    # ----- (4) Error details (if any) --------------------------------
    if total_errors > 0:
        subsection("4. Errors (review and re-run to retry)")
        for variable, stats in summary.items():
            for err in stats["errors"]:
                warn(f"  {variable} {err['year']}: {err.get('error', '?')}")
        warn(
            "Some files failed. Re-running this script will retry just the "
            "failed (variable, year) pairs (successful ones are skipped)."
        )

    # ----- (5) Handoff to s05 ----------------------------------------
    subsection("5. Handoff to Step 05 (BoM ACORN-SAT)")
    log("Step 05 (src/ingestion/bom_acornsat.py) will:")
    log("  - retrieve BoM ACORN-SAT station-level homogenised temperature records")
    log("  - persist as data/processed/bom_acornsat/<station_id>.csv")
    log("Before s05: spot-check one masked SILO file:")
    log(
        "  python -c \"import xarray as xr; ds=xr.open_dataset('data/processed/silo/max_temp/2000.max_temp.nc'); print(ds)\""
    )

    expected_total = len(SILO_VARIABLES) * (
        SILO_YEAR_MAX_DEFAULT - SILO_YEAR_MIN_DEFAULT + 1
    )
    completed_or_intentionally_skipped = total_done + total_skip_done + total_skip_pre
    if total_errors == 0 and completed_or_intentionally_skipped == expected_total:
        ok("Phase 01 Step 04 complete")
        return 0
    else:
        warn("Phase 01 Step 04 partial. Re-run to retry failures.")
        return 0  # Not an error exit; just incomplete.


if __name__ == "__main__":
    raise SystemExit(main())
