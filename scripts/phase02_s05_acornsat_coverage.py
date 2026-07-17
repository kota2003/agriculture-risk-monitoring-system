"""
Phase 02, Step 05 — ACORN-SAT station coverage impact assessment (Task E).

Goal:
    Quantify the impact of the 18 unavailable ACORN-SAT stations on regional
    SILO validation (Phase 01 s05 finding #5; scope v5 §4.2, §12.2): assign the
    112 ACORN-SAT stations to AAGIS regions, count available stations per
    region, and flag broadacre regions with no / sparse station truth.

Pipeline:
    1. Load the 112-station list; mark 94 available / 18 unavailable.
    2. Point-in-polygon assign stations to AAGIS regions.
    3. Per-region availability counts + broadacre under-representation flags.
    4. Persist outputs/tables/s05_acornsat_region_coverage.csv and print a
       summary (broadacre regions with no station; broadacre-relevant
       unavailable stations).

This is an assessment (documentation), not a pass/fail gate; it always exits 0
unless the station totals are inconsistent.

Run from repo root:
    python scripts/phase02_s05_acornsat_coverage.py
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

from src.log_utils import error, log, ok, section, subsection  # noqa: E402
from src.paths import TABLES_DIR  # noqa: E402
from src.processing.acornsat_coverage import (  # noqa: E402
    EXPECTED_N_STATIONS,
    assign_stations_to_regions,
    compute_region_coverage,
    load_stations,
    summarize,
)
from src.processing.region_aggregation import load_region_mapping  # noqa: E402


def main() -> int:
    section("Phase 02 - Step 05: ACORN-SAT coverage impact assessment")

    stations = load_stations()
    log(
        f"loaded {len(stations)} stations "
        f"({int(stations['available'].sum())} available, "
        f"{int((~stations['available']).sum())} unavailable)"
    )
    if len(stations) != EXPECTED_N_STATIONS:
        error(f"expected {EXPECTED_N_STATIONS} stations, got {len(stations)}")
        return 1

    assigned = assign_stations_to_regions(stations)
    mapping = load_region_mapping()
    cov = compute_region_coverage(assigned, mapping)
    summ = summarize(cov, assigned)

    subsection("Broadacre regions with NO available ACORN-SAT station")
    if summ["broadacre_no_station"]:
        for name in summ["broadacre_no_station"]:
            log(f"  - {name}")
    else:
        ok("  none — every broadacre region has >= 1 available station")

    subsection("Broadacre regions with a SINGLE available station (sparse)")
    for name in summ["broadacre_sparse"]:
        log(f"  - {name}")

    subsection("Broadacre-relevant unavailable stations (lost truth)")
    for rec in summ["broadacre_relevant_unavailable"]:
        log(
            f"  {rec['station_id']} {str(rec['name'])[:24]:<24s} -> "
            f"{rec['aagis_code']} {rec['region_name']}"
        )

    subsection("Persist table")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / "s05_acornsat_region_coverage.csv"
    tmp = out.with_suffix(out.suffix + ".part")
    cov.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out)
    ok(f"  wrote {out}")

    log("")
    log(
        f"summary: {summ['n_available_total']} available / "
        f"{summ['n_unavailable_total']} unavailable; "
        f"{len(summ['broadacre_no_station'])} broadacre region(s) with no station, "
        f"{len(summ['broadacre_sparse'])} sparse."
    )
    ok("s05 complete: ACORN-SAT coverage impact assessed and documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
