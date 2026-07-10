"""
Phase 01, Step 08 — OpenWeather One Call 3.0 historical ingestion.

Goal:
    Retrieve daily-aggregated historical weather for 10 approved AAGIS
    region centroids over 2022-01-01 to 2024-12-31 (3 years), as a
    validation comparator vs SILO (scope v4 §4.5). The OpenWeather–SILO
    comparison study itself is conducted in Phase 02 / Phase 09; s08
    only acquires the data.

Pipeline:
    1. Load OPENWEATHER_API_KEY from .env (gitignored).
    2. Compute centroids for the 10 approved AAGIS regions from the s01
       repaired shapefile.
    3. For each region, fetch one daily record per date over 2022–2024,
       persisting per-year Parquet files in data/raw/openweather/.
       Resumable: dates already cached are skipped.
    4. Stop when DAILY_CALL_QUOTA calls have been made in this run
       (default 10,500 = within 11,000 dashboard hard limit with headroom).
    5. Sanity check: count days persisted per (region, year) and report.
    6. Handoff summary for Step 09 (Phase 01 closure ceremony).

Cost expectation (scope v4 §6.4):
    Total target calls = 10 regions × 1,095 days = 10,950
    Free quota         = 1,000 / day
    Paid               = up to 9,950 × GBP 0.0012 ≈ GBP 12 (≈ AUD 23)
    Daily hard limit set to 11,000 in OpenWeather dashboard.

Runtime expectation:
    60 calls/min ceiling with 1.05 s sleep ≈ 57 calls/min.
    10,950 calls / 57 per min ≈ 192 min ≈ 3h 12min.

Idempotency:
    Re-run after partial completion resumes where it left off.

Run from repo root:
    python scripts/phase01_s08_ingest_openweather.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# sys.path injection
# ---------------------------------------------------------------------------
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.paths import DATA_RAW, DATA_PROCESSED  # noqa: E402
from src.log_utils import log, ok, warn, error, section, subsection  # noqa: E402
from src.processing.aagis_centroids import (  # noqa: E402
    APPROVED_REGION_CODES,
    compute_centroids,
)
from src.ingestion.openweather import (  # noqa: E402
    DEFAULT_SLEEP_SECONDS,
    get_api_key,
    ingest_region,
    summary_count_by_region_year,
)


# ----- Run-time configuration --------------------------------------------

# Period (scope §4.5: "OpenWeather historical window only", and a 3-year
# overlap with SILO covers seasonal cycle × 3 for the comparison study).
START_DATE = date(2022, 1, 1)
END_DATE = date(2024, 12, 31)

# Soft cap on calls per *this run* to stay within the dashboard hard limit
# (11,000) with headroom for retries. If reached, the run exits cleanly;
# re-running the next day resumes from where it left off.
DAILY_CALL_QUOTA = 10_500

# Output directory
RAW_OUTPUT_DIR = DATA_RAW / "openweather"


def main() -> int:
    section("Phase 01, Step 08 — OpenWeather One Call 3.0 historical ingestion")

    log(f"Period:            {START_DATE} → {END_DATE}")
    log(f"Approved regions:  {APPROVED_REGION_CODES}")
    log(f"Daily call quota:  {DAILY_CALL_QUOTA:,} (dashboard hard limit: 11,000)")
    log(
        f"Sleep per call:    {DEFAULT_SLEEP_SECONDS}s "
        f"(≈ {60/DEFAULT_SLEEP_SECONDS:.0f} calls/min)"
    )
    log(f"Output:            {RAW_OUTPUT_DIR}")

    # ----- (1) Load API key ----------------------------------------
    subsection("1. Load API key from .env")
    try:
        api_key = get_api_key()
    except RuntimeError as e:
        error(str(e))
        return 1
    masked = api_key[:6] + "…" + api_key[-4:] if len(api_key) > 12 else "***"
    ok(f"  API key loaded: {masked}")

    # ----- (2) Compute centroids ------------------------------------
    subsection("2. Compute 10 AAGIS region centroids")
    aagis_gpkg = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
    try:
        centroids = compute_centroids(aagis_gpkg)
    except (FileNotFoundError, RuntimeError) as e:
        error(f"  centroid computation failed: {e}")
        return 1
    if len(centroids) != len(APPROVED_REGION_CODES):
        warn(
            f"  centroid count mismatch: got {len(centroids)}, "
            f"expected {len(APPROVED_REGION_CODES)}"
        )

    # ----- (3) Ingest with daily quota tracking --------------------
    subsection(
        "3. Ingest historical day-summary per region "
        "(resumable, daily-quota-bounded)"
    )

    calls_this_run = {"count": 0}

    def on_call_quota_check(region_code: str, date_str: str) -> None:
        calls_this_run["count"] += 1
        n = calls_this_run["count"]
        # Heartbeat every 100 calls
        if n % 100 == 0:
            log(
                f"    [progress] {n:,} calls this run "
                f"(latest: region {region_code} date {date_str})"
            )
        if n >= DAILY_CALL_QUOTA:
            warn(
                f"  Daily quota of {DAILY_CALL_QUOTA:,} reached. "
                f"Exiting cleanly; re-run to resume from next date."
            )
            raise StopIteration

    totals = {"fetched": 0, "skipped_existing": 0, "skipped_failed": 0}
    quota_hit = False
    for c in centroids:
        log(f"\n  --- region {c.code} ({c.name}) ---")
        try:
            stats = ingest_region(
                api_key=api_key,
                region_code=c.code,
                lat=c.lat,
                lon=c.lon,
                start_date=START_DATE,
                end_date=END_DATE,
                out_dir=RAW_OUTPUT_DIR,
                on_call=on_call_quota_check,
            )
        except StopIteration:
            quota_hit = True
            break
        except RuntimeError as e:
            # 401 from API key — abort entire run
            error(f"  fatal: {e}")
            return 1
        for k in totals:
            totals[k] += stats[k]
        log(
            f"  region {c.code} stats: fetched={stats['fetched']}, "
            f"skipped_existing={stats['skipped_existing']}, "
            f"skipped_failed={stats['skipped_failed']}"
        )

    # ----- (4) Run summary ----------------------------------------
    subsection("4. Run summary")
    log(f"  Calls this run:         {calls_this_run['count']:,}")
    log(f"  Newly fetched rows:     {totals['fetched']:,}")
    log(f"  Skipped (already done): {totals['skipped_existing']:,}")
    log(f"  Skipped (failed):       {totals['skipped_failed']:,}")
    if quota_hit:
        warn(
            "  Daily quota was reached. Re-run tomorrow (or after midnight UTC) "
            "to resume from the next date. Each region's per-year Parquet is "
            "already persisted up to the last successful call."
        )

    # ----- (5) Coverage report ------------------------------------
    subsection("5. Coverage by region × year")
    df = summary_count_by_region_year(RAW_OUTPUT_DIR)
    if df.empty:
        warn("  no output files found yet")
    else:
        # Pretty-print as grouped tally
        for region_code, sub in df.groupby("region_code"):
            year_strs = [f"{int(r.year)}={int(r.n_days)}" for r in sub.itertuples()]
            log(f"  {region_code}: " + ", ".join(year_strs))
        total = int(df["n_days"].sum())
        target_total = len(APPROVED_REGION_CODES) * ((END_DATE - START_DATE).days + 1)
        log(
            f"  TOTAL days persisted: {total:,} / target {target_total:,} "
            f"({100*total/target_total:.1f}%)"
        )

    # ----- (6) Handoff --------------------------------------------
    subsection("6. Handoff to Step 09 (Phase 01 closure)")
    log("Step 09 (s09 closure ceremony) will:")
    log("  - populate data/raw/manifest.yaml with s01-s08 source entries")
    log("  - append PROJECT_LOG entries for s02-s08")
    log("  - draft scope v4 patch for Phase 01 empirical findings")
    log("  - regenerate README via scripts/update_readme.py")
    log("  - merge phase-01-data-acquisition → main with --no-ff")
    log("  - tag v0.1-phase01-complete")

    if quota_hit:
        warn(
            "Phase 01 Step 08 partial (daily quota reached). "
            "Re-run after dashboard daily reset."
        )
        return 0
    if totals["fetched"] > 0 or totals["skipped_existing"] > 0:
        ok("Phase 01 Step 08 complete")
        return 0
    else:
        warn("Phase 01 Step 08 produced no rows; investigate")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
