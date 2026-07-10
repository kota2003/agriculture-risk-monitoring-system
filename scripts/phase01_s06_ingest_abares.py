"""
Phase 01, Step 06 — ABARES Farm Data Portal Historical Estimates ingestion.

Goal:
    Retrieve the three "Historical Estimates" CSVs from the ABARES Farm
    Data Portal — Regional (primary), National (sanity-check), State
    (cross-validation) — and produce processed commodity-level yield
    tables for wheat, barley, canola (scope v4 §4.3, §6.2).

Pipeline:
    1. Download three FDP CSVs to data/raw/abares/ (HTTPS, idempotent).
    2. Parse the Regional CSV (long-form: Variable, Year, region, Value, RSE).
    3. For each commodity in {wheat, barley, canola}, reshape to wide
       form (area_ha, production_t, derived yield_t_ha) and persist as
       data/processed/abares/<commodity>.csv.
    4. Sanity check: sum of regional values per year ≈ national value
       (filtered to Industry='All Broadacre', within ±5% tolerance).
    5. Cross-check: AAGIS region names in FDP exactly match the s01
       shapefile region names.
    6. Handoff summary for Step 07 (ABS Agricultural Census).

Idempotency:
    Already-downloaded raw CSVs and existing processed commodity CSVs are
    re-used. Re-run safely.

Expected runtime: < 1 minute (~22 MB total download).

Run from repo root:
    python scripts/phase01_s06_ingest_abares.py
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

from src.paths import DATA_RAW, DATA_PROCESSED
from src.log_utils import log, ok, warn, error, section, subsection
from src.ingestion.abares import (
    FDP_FILES,
    download_fdp_csv,
    fdp_local_path,
    load_fdp_csv,
    extract_commodity_wide,
    sanity_check_regional_vs_national,
    cross_check_aagis_region_names,
    COMMODITY_VARIABLES,
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
    section("Phase 01, Step 06 — ABARES Farm Data Portal Historical Estimates")

    raw_dir = DATA_RAW / "abares"
    processed_dir = DATA_PROCESSED / "abares"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    log(f"Raw dir:       {raw_dir}")
    log(f"Processed dir: {processed_dir}/<commodity>.csv")
    log(f"Commodities:   {list(COMMODITY_VARIABLES)}")

    # ----- (1) Download three FDP CSVs ------------------------------
    subsection("1. Download FDP CSVs (regional, national, state)")
    download_summary = {}
    for level in FDP_FILES:
        result = download_fdp_csv(level, raw_dir)
        if result is None:
            log(f"  {level:<10s} skipped (already exists)")
            download_summary[level] = "skipped"
        elif "error" in result:
            error(f"  {level:<10s} FAILED: {result['error']}")
            download_summary[level] = f"error: {result['error']}"
        else:
            ok(f"  {level:<10s} downloaded ({_fmt_bytes(result['size_bytes'])})")
            download_summary[level] = "downloaded"

    if download_summary.get("regional", "").startswith("error"):
        error("Cannot proceed without regional CSV")
        return 1

    # ----- (2) Parse Regional + National --------------------------
    subsection("2. Parse Regional and National CSVs (long-form)")
    df_regional = load_fdp_csv(fdp_local_path(raw_dir, "regional"), level="regional")

    df_national = None
    nat_path = fdp_local_path(raw_dir, "national")
    if nat_path.exists():
        df_national = load_fdp_csv(nat_path, level="national")

    # ----- (3) Extract per-commodity wide-form tables ---------------
    subsection("3. Extract commodity tables (wheat, barley, canola)")
    commodity_summary = {}
    for commodity in COMMODITY_VARIABLES:
        out_path = processed_dir / f"{commodity}.csv"
        if out_path.exists():
            log(f"  {commodity:<8s} skipped (already exists at {out_path.name})")
            commodity_summary[commodity] = {"status": "skipped"}
            continue
        try:
            wide = extract_commodity_wide(df_regional, commodity)
        except RuntimeError as e:
            error(f"  {commodity:<8s} extraction failed: {e}")
            commodity_summary[commodity] = {"status": "error", "msg": str(e)}
            continue

        wide.to_csv(out_path, index=False)
        n_regions = wide["region"].nunique()
        n_years = wide["year"].nunique()
        n_nonzero_yield = wide["yield_t_ha"].notna().sum()
        log(
            f"  {commodity:<8s} wrote {out_path.name}: "
            f"{len(wide):,} rows, {n_regions} regions x {n_years} years, "
            f"{n_nonzero_yield:,} non-NA yields"
        )
        commodity_summary[commodity] = {
            "status": "ok",
            "rows": len(wide),
            "regions": n_regions,
            "years": n_years,
            "non_na_yield": int(n_nonzero_yield),
        }

    # ----- (4) Sanity check: regional sum vs national All-Broadacre --
    subsection("4. Sanity check: regional sum ≈ national (Industry='All Broadacre')")
    if df_national is None:
        warn("  national CSV not available; skipping sanity check")
    else:
        for variable in [
            "Wheat produced (t)",
            "Barley produced (t)",
            "Canola produced (t)",
        ]:
            res = sanity_check_regional_vs_national(
                df_regional,
                df_national,
                variable,
                tolerance_frac=0.05,
            )
            if not res.get("valid"):
                warn(f"  '{variable}': {res.get('reason')}")
                continue
            within = res["n_years_within_tolerance"]
            total = res["n_years_compared"]
            log(
                f"  '{variable}': {within}/{total} years within ±5% "
                f"(median diff: {res['median_frac_diff']*100:+.2f}%, "
                f"max abs diff: {res['max_abs_frac_diff']*100:.2f}%)"
            )

    # ----- (5) Cross-check AAGIS region names -----------------------
    subsection("5. Cross-check AAGIS region names vs s01 shapefile")
    aagis_gpkg = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
    res = cross_check_aagis_region_names(df_regional, aagis_gpkg)
    if not res.get("valid"):
        warn(f"  cross-check skipped: {res.get('reason')}")
    else:
        log(f"  AAGIS field used: '{res['aagis_field_used']}'")
        log(f"  AAGIS regions:    {res['n_aagis_regions']}")
        log(f"  FDP regions:      {res['n_fdp_regions']}")
        log(f"  Matching:         {res['n_matching']}")
        if res["only_in_fdp"]:
            warn(f"  Only in FDP (NOT in s01 shapefile): {res['only_in_fdp']}")
        if res["only_in_aagis"]:
            warn(f"  Only in s01 shapefile (NOT in FDP): {res['only_in_aagis']}")
        if not res["only_in_fdp"] and not res["only_in_aagis"]:
            ok("  All region names match exactly — downstream spatial joins safe")

    # ----- (6) Handoff ----------------------------------------------
    subsection("6. Handoff to Step 07 (ABS Agricultural Census)")
    log("Step 07 (src/ingestion/abs_census.py) will:")
    log("  - retrieve ABS Agricultural Census 2021 SA2-level data")
    log("  - used for cross-section structural snapshot, not time-series")
    log("  - persist as data/processed/abs_census/")

    all_ok = not any(v.startswith("error") for v in download_summary.values()) and all(
        c.get("status") in ("ok", "skipped") for c in commodity_summary.values()
    )
    if all_ok:
        ok("Phase 01 Step 06 complete")
        return 0
    else:
        warn("Phase 01 Step 06 partial. Review errors above.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
