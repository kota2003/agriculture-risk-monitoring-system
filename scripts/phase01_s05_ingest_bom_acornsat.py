"""
Phase 01, Step 05 - BoM ACORN-SAT station-level temperature ingestion.

Goal:
    Retrieve homogenised daily Tmax/Tmin records for ACORN-SAT
    reference stations that BoM publishes at the canonical hqsites URL.
    A small fixed list (ACORN_SAT_UNAVAILABLE_STATIONS in src.ingestion.bom_acornsat)
    is skipped before any download attempt; these stations are listed in
    the ACORN-SAT network but BoM does not publish a daily CSV for them.

Pipeline:
    1. Fetch the 112-station list from BoM's machine-readable endpoint.
    2. For each (station x variable in {tmin, tmax}), either skip
       (known-unavailable / already-downloaded) or download.
    3. Validate a random sample of files structurally.

Idempotency:
    Already-downloaded files and known-unavailable stations are both
    skipped. Re-run safely.

Run from repo root:
    python scripts/phase01_s05_ingest_bom_acornsat.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import random

from src.paths import DATA_RAW, DATA_PROCESSED
from src.log_utils import log, ok, warn, section, subsection
from src.ingestion.bom_acornsat import (
    fetch_station_list,
    ingest_all_stations,
    validate_csv,
    acornsat_local_path,
    ACORN_SAT_VARIABLES,
    ACORN_SAT_UNAVAILABLE_STATIONS,
    EXPECTED_N_STATIONS,
)


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024.0
        if n < 1024 or unit == "GB":
            return f"{n:.2f} {unit}"
    return f"{n:.2f} GB"


def main() -> int:
    section("Phase 01, Step 05 - BoM ACORN-SAT station temperature ingestion")

    raw_dir = DATA_RAW / "acorn_sat"
    processed_dir = DATA_PROCESSED
    station_list_cache = raw_dir / "station_list.csv"

    log(f"Raw dir (cache):  {raw_dir}")
    log(f"Processed dir:    {processed_dir}/bom_acornsat/<variable>/<id>.daily.csv")
    log(f"Variables:        {ACORN_SAT_VARIABLES}")
    log(
        f"Known-unavailable stations (Master-grade explicit skip): "
        f"{len(ACORN_SAT_UNAVAILABLE_STATIONS)}"
    )

    # ----- (1) Fetch station list -----------------------------------
    subsection("1. Obtain ACORN-SAT 112-station list")
    raw_dir.mkdir(parents=True, exist_ok=True)
    stations = fetch_station_list(cache_path=station_list_cache)

    if len(stations) != EXPECTED_N_STATIONS:
        warn(
            f"Got {len(stations)} stations, expected {EXPECTED_N_STATIONS}. "
            "Manual inspection recommended."
        )
    else:
        ok(f"{len(stations)} stations fetched/cached as expected")

    # ----- (2) Download per-station CSVs ----------------------------
    subsection(
        f"2. Download {len(stations)} x {len(ACORN_SAT_VARIABLES)} = "
        f"{len(stations) * len(ACORN_SAT_VARIABLES)} per-station daily CSVs"
    )
    log(
        f"  {len(ACORN_SAT_UNAVAILABLE_STATIONS)} stations will be skipped without "
        f"download attempt (publish gap at BoM hqsites)."
    )
    summary = ingest_all_stations(stations, processed_dir)

    # ----- (3) Per-variable summary ---------------------------------
    subsection("3. Per-variable summary")
    log(
        f"  {'variable':<8s} {'done':>5s} {'skip-done':>10s} {'skip-unavail':>13s} "
        f"{'errors':>7s} {'total_size':>12s}"
    )
    total_done = 0
    total_skip_done = 0
    total_skip_unavail = 0
    total_errors = 0
    total_bytes = 0
    for variable, stats in summary.items():
        log(
            f"  {variable:<8s} {stats['done']:>5d} "
            f"{stats['skipped_already_done']:>10d} "
            f"{stats['skipped_unavailable']:>13d} "
            f"{len(stats['errors']):>7d} "
            f"{_fmt_bytes(stats['total_bytes']):>12s}"
        )
        total_done += stats["done"]
        total_skip_done += stats["skipped_already_done"]
        total_skip_unavail += stats["skipped_unavailable"]
        total_errors += len(stats["errors"])
        total_bytes += stats["total_bytes"]
    log("")
    log(f"  Total succeeded (this run):       {total_done}")
    log(f"  Total skipped (already done):     {total_skip_done}")
    log(f"  Total skipped (unavailable):      {total_skip_unavail}")
    log(f"  Total errors:                     {total_errors}")
    log(f"  Total disk usage:                 {_fmt_bytes(total_bytes)}")

    # ----- (4) Error details ----------------------------------------
    if total_errors > 0:
        subsection("4. Errors (review and re-run to retry)")
        for variable, stats in summary.items():
            for err in stats["errors"][:10]:
                warn(
                    f"  {variable} {err.get('station_id', '?')}: "
                    f"{err.get('error', '?')}"
                )
            if len(stats["errors"]) > 10:
                warn(f"  ... and {len(stats['errors']) - 10} more {variable} errors")

    # ----- (5) Structural validation on sample ----------------------
    subsection("5. Structural validation (random sample of 5 stations)")
    # Validate only stations we actually downloaded:
    available_ids = [
        sid
        for sid in stations["station_id"].tolist()
        if sid not in ACORN_SAT_UNAVAILABLE_STATIONS
    ]
    sample_ids = random.sample(available_ids, min(5, len(available_ids)))
    n_valid = 0
    n_attempted = 0
    for sid in sample_ids:
        for variable in ACORN_SAT_VARIABLES:
            p = acornsat_local_path(processed_dir, variable, sid)
            if not p.exists():
                continue
            n_attempted += 1
            v = validate_csv(p)
            if v["valid"]:
                log(
                    f"  OK  {variable} {sid}: {v['n_rows']:,} rows, "
                    f"{v['first_date']} -> {v['last_date']}"
                )
                n_valid += 1
            else:
                warn(f"  BAD {variable} {sid}: {v['reason']}")
    log(f"  {n_valid} of {n_attempted} sample files valid")

    # ----- (6) Handoff to s06 ---------------------------------------
    subsection("6. Handoff to Step 06 (ABARES regional commodity statistics)")
    log("Step 06 (src/ingestion/abares.py) will:")
    log("  - retrieve ABARES regional annual yield/area/production for")
    log("    wheat (primary), barley, canola (secondary)")
    log("  - join to AAGIS regions from s01")
    log("  - persist as data/processed/abares/<commodity>.csv")

    expected_total = len(stations) * len(ACORN_SAT_VARIABLES)
    completed = total_done + total_skip_done + total_skip_unavail
    if total_errors == 0 and completed == expected_total:
        ok("Phase 01 Step 05 complete")
        return 0
    else:
        warn("Phase 01 Step 05 partial. Re-run to retry failures.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
