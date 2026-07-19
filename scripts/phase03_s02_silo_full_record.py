"""
Phase 03, Step 02 — full-record SILO region climatology aggregation.

Goal:
    Extend the SILO region means to the full record (1961-2024; evap_pan
    1970-2024) and derive the WMO-baseline table, providing the inputs for the
    Phase 03 regional climate climatology EDA (interannual variation, trends,
    baseline anomalies).

Outputs:
    data/processed/silo_region_means/annual_1961_2024.csv   (gitignored)
    outputs/tables/s02_region_climate_baselines.csv          (committed)

Cost note:
    Reads the 375 masked SILO NetCDFs (~13 GB) once each; expect ~30-60 min on a
    laptop. Reads only; two atomic writes at the end. The cell-region map is
    reused from Phase 02 (cached parquet); no re-download.

Exit code:
    0 if the aggregation completes and every sanity check passes; 1 otherwise.

Run from repo root:
    python scripts/phase03_s02_silo_full_record.py
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
from src.processing.silo_climatology import (  # noqa: E402
    FULL_RECORD_END,
    FULL_RECORD_START,
    aggregate_annual_full_record,
    check_full_record,
    compute_baselines,
    write_annual_full_record,
    write_baselines,
)
from src.processing.silo_region_aggregation import (  # noqa: E402
    CELL_REGION_MAP_PARQUET,
    SILO_PROCESSED_DIR,
    load_cell_region_map,
)


def _preflight() -> int:
    """Fail fast if the Phase 02 cell map or the SILO archive are missing."""
    if not CELL_REGION_MAP_PARQUET.exists():
        error(
            f"cell-region map missing: {CELL_REGION_MAP_PARQUET}. "
            "Run scripts/phase02_s04a_silo_region_means.py first."
        )
        return 1
    probes = [
        SILO_PROCESSED_DIR / "max_temp" / f"{FULL_RECORD_START}.max_temp.nc",
        SILO_PROCESSED_DIR / "evap_pan" / "1970.evap_pan.nc",
        SILO_PROCESSED_DIR / "daily_rain" / f"{FULL_RECORD_END}.daily_rain.nc",
    ]
    missing = [p for p in probes if not p.exists()]
    if missing:
        error(f"SILO processed files missing (sample): {[str(p) for p in missing]}")
        return 1
    return 0


def main() -> int:
    section("Phase 03 - Step 02: full-record SILO region climatology")

    if _preflight() != 0:
        return 1

    subsection("Aggregation")
    log("reading 375 masked SILO NetCDFs (~13 GB); this takes ~30-60 min...")
    cell_df = load_cell_region_map()
    log(f"  cell-region map: {len(cell_df):,} cells")
    annual = aggregate_annual_full_record(cell_df)

    subsection("Sanity checks")
    checks = check_full_record(annual)
    n_fail = 0
    for name, good, detail in checks:
        (ok if good else warn)(f"  {name}: {detail}")
        n_fail += 0 if good else 1
    if n_fail:
        error(f"sanity checks FAILED ({n_fail}); not writing outputs")
        return 1

    subsection("Baselines")
    baselines = compute_baselines(annual)
    log(f"  {len(baselines)} baseline rows (2 periods x variables x regions)")

    subsection("Persist")
    a_path = write_annual_full_record(annual)
    b_path = write_baselines(baselines)
    ok(f"  annual series ({len(annual):,} rows) -> {a_path.name}")
    ok(f"  baselines     ({len(baselines):,} rows) -> {b_path.name}")

    ok("s02 aggregation complete: full-record annual series + baselines persisted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
