"""
Phase 02, Step 01 — AAGIS region code <-> FDP name mapping (Task A).

Goal:
    Build and validate the canonical mapping between the AAGIS 3-digit
    region code (shapefile field ``class``) and the ABARES FDP text region
    name (``ABARES region``), then persist it for downstream Pillar 3-5
    spatial joins (scope v5 §3.1, §6.2, §11.6).

Pipeline:
    1. Load the code<->name<->zone table directly from the s01 GeoPackage
       (data/processed/aagis_regions_repaired.gpkg).
    2. Load the 32 FDP region names from the regional CSV.
    3. Validate against the Task A exit criterion:
         - 32 regions, unique 3-digit codes, unique names,
         - code redundancy (aagis == class),
         - state-prefix geographic sanity,
         - name-set equality with the FDP (zero orphans, 32/32).
    4. Persist data/processed/region_mapping.csv (atomic .part -> rename).

Exit status:
    0 if validation passes; 1 otherwise (so the step fails loudly in CI /
    a terminal if the upstream data ever drifts).

Idempotency:
    Reads only; the single write is atomic and overwrites safely. Re-run
    freely.

Expected runtime: < 5 seconds.

Run from repo root:
    python scripts/phase02_s01_region_mapping.py
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
from src.processing.region_aggregation import (  # noqa: E402
    EXPECTED_N_REGIONS,
    build_and_validate,
    write_region_mapping,
)


def _print_report(report: dict) -> None:
    subsection("Validation checks")
    for name, passed in report["checks"].items():
        mark = "PASS" if passed else "FAIL"
        log(f"  [{mark}] {name}")

    log("")
    log(f"  regions in shapefile : {report['n_regions']}")
    log(f"  region names in FDP  : {report['n_fdp_names']}")
    log(f"  matching names       : {report['n_matching']} / {EXPECTED_N_REGIONS}")

    if report["only_in_shapefile"]:
        log(f"  names only in shapefile: {report['only_in_shapefile']}")
    if report["only_in_fdp"]:
        log(f"  names only in FDP      : {report['only_in_fdp']}")
    if report["bad_codes"]:
        log(f"  malformed codes        : {report['bad_codes']}")
    if report["state_prefix_mismatches"]:
        log(f"  state-prefix mismatches: {report['state_prefix_mismatches']}")


def main() -> int:
    section("Phase 02 - Step 01: AAGIS region code <-> FDP name mapping")

    subsection("Build mapping")
    mapping, report = build_and_validate()

    # Show the full 32-row table for a human eyeball.
    subsection("Mapping table")
    display_cols = [c for c in mapping.columns if not c.startswith("_")]
    print(mapping[display_cols].to_string(index=False))

    _print_report(report)

    if not report["valid"]:
        error("Task A validation FAILED — mapping not persisted.")
        return 1

    subsection("Persist")
    out = write_region_mapping(mapping)

    ok(
        f"Task A complete: {EXPECTED_N_REGIONS}/{EXPECTED_N_REGIONS} mapped, "
        f"zero orphans. Wrote {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
