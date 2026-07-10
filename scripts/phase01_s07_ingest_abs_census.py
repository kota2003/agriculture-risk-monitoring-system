"""
Phase 01, Step 07 — ABS Agricultural Census 2020-21 SA2 ingestion.

Goal:
    Retrieve the ABS Agricultural Census 2020-21 XLSX (ASGS Edition 3,
    ~3.87 MB) and persist commodity-level SA2 cross-section tables for
    wheat, barley, canola (scope v4 §4.3).

Pipeline:
    1. Download AGCDCASGS202021.xlsx to data/raw/abs_census/ (HTTPS,
       idempotent).
    2. Parse "Table 1" sheet (long-form: region_code, region_label,
       commodity_code, commodity_description, estimate, RSE,
       n_businesses, n_businesses_rse). Skip rows 1-6 (metadata).
    3. Classify each row by ABS ASGS region_level via region_code digit
       count (national / state / sa4 / sa3 / sa2 / unknown).
    4. For each commodity in {wheat, barley, canola}, reshape SA2 rows
       to wide form (area_ha, production_t, yield_t_ha, RSEs,
       n_businesses) and persist as
       data/processed/abs_census/<commodity>_sa2.csv.
    5. Additionally save the national+state wide form for sanity reference
       as data/processed/abs_census/<commodity>_national_state.csv.
    6. Sanity check: national WHEAT_YIELD_F = 2.5 t/ha,
       BARLEY_YIELD_F = 2.7 t/ha (verified from XLSX inspection
       2026-05-15).
    7. Handoff summary for Step 08 (OpenWeather).

Structural note:
    The 2020-21 Agricultural Census was the FINAL ABS Agricultural
    Census. ABS announcement (ABS, 26 July 2022):
        "The 2020-21 Agricultural Census was the last Agricultural Census
        to be conducted by the ABS."
    Future updates use the ABS modernised pipeline (Levy Payer Register
    + satellite crop mapping), released annually from 2022-23. Project 5
    v1.0 freezes Census-derived weighting at this 2020-21 vintage.

Idempotency:
    Already-downloaded XLSX and existing processed commodity CSVs are
    re-used. Re-run safely.

Expected runtime: ~30 seconds.

Run from repo root:
    python scripts/phase01_s07_ingest_abs_census.py
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
from src.ingestion.abs_census import (
    ABS_AGCENSUS_FILENAME,
    COMMODITY_CODES,
    abs_census_local_path,
    download_abs_census,
    load_abs_census,
    add_region_level_column,
    extract_commodity_wide,
    sanity_check_national_yield,
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
    section("Phase 01, Step 07 — ABS Agricultural Census 2020-21 (SA2)")

    raw_dir = DATA_RAW / "abs_census"
    processed_dir = DATA_PROCESSED / "abs_census"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    log(f"Raw dir:       {raw_dir}")
    log(f"Processed dir: {processed_dir}/<commodity>_<level>.csv")
    log(f"Commodities:   {list(COMMODITY_CODES)}")

    # ----- (1) Download --------------------------------------------
    subsection("1. Download AGCDCASGS202021.xlsx")
    result = download_abs_census(raw_dir)
    if result is None:
        log(f"  skipped (already exists at {raw_dir / ABS_AGCENSUS_FILENAME})")
    elif "error" in result:
        error(f"  FAILED: {result['error']}")
        error(f"  URL: {result.get('url')}")
        return 1
    else:
        ok(f"  downloaded ({_fmt_bytes(result['size_bytes'])})")

    # ----- (2) Parse + (3) classify region level -------------------
    subsection("2. Parse 'Table 1' sheet (long-form)")
    df_long = load_abs_census(abs_census_local_path(raw_dir))

    subsection("3. Classify region levels via ASGS digit count")
    df_long = add_region_level_column(df_long)

    # Print level distribution
    counts = df_long["region_level"].value_counts().to_dict()
    parts = []
    n_regions_by_level = {}
    for lvl in ("national", "state", "sa4", "sa3", "sa2", "unknown"):
        if lvl in counts:
            n_unique = df_long[df_long["region_level"] == lvl]["region_code"].nunique()
            n_regions_by_level[lvl] = n_unique
            parts.append(f"{lvl}={counts[lvl]:,} rows ({n_unique} regions)")
    log("  " + ", ".join(parts))

    if "sa2" not in counts or n_regions_by_level.get("sa2", 0) < 100:
        warn(
            f"  expected ~1,124 SA2 regions reporting agriculture; "
            f"got {n_regions_by_level.get('sa2', 0)}"
        )

    # ----- (4) Extract per-commodity wide-form (SA2) ---------------
    subsection("4. Extract commodity wide-form tables (SA2)")
    commodity_summary = {}
    for commodity in COMMODITY_CODES:
        out_path = processed_dir / f"{commodity}_sa2.csv"
        if out_path.exists():
            log(f"  {commodity:<8s} skipped (already exists at {out_path.name})")
            commodity_summary[commodity] = {"status": "skipped"}
            continue
        try:
            wide = extract_commodity_wide(df_long, commodity, region_level="sa2")
        except RuntimeError as e:
            error(f"  {commodity:<8s} extraction failed: {e}")
            commodity_summary[commodity] = {"status": "error", "msg": str(e)}
            continue

        wide.to_csv(out_path, index=False)
        n_regions = wide["region_code"].nunique()
        n_nonzero_yield = (
            wide["yield_t_ha"].notna().sum() if "yield_t_ha" in wide else 0
        )
        n_nonzero_area = wide["area_ha"].notna().sum() if "area_ha" in wide else 0
        log(
            f"  {commodity:<8s} wrote {out_path.name}: "
            f"{len(wide):,} SA2 rows, "
            f"{n_nonzero_yield:,} non-NA yields, "
            f"{n_nonzero_area:,} non-NA areas"
        )
        commodity_summary[commodity] = {
            "status": "ok",
            "n_sa2": n_regions,
            "non_na_yield": int(n_nonzero_yield),
            "non_na_area": int(n_nonzero_area),
        }

    # ----- (5) Save national + state wide-form for triangulation ---
    subsection("5. Save national+state wide-form for triangulation")
    for commodity in COMMODITY_CODES:
        out_path = processed_dir / f"{commodity}_national_state.csv"
        if out_path.exists():
            log(f"  {commodity:<8s} skipped (already exists at {out_path.name})")
            continue
        if commodity_summary.get(commodity, {}).get("status") == "error":
            log(f"  {commodity:<8s} skipped (SA2 extraction failed)")
            continue
        try:
            sub_long = df_long[df_long["region_level"].isin(["national", "state"])]
            # Build a small long-form dataframe with the 3 target codes only
            codes = COMMODITY_CODES[commodity]
            sub = sub_long[sub_long["commodity_code"].isin(codes.values())].copy()
            if sub.empty:
                warn(f"  {commodity:<8s} no national/state rows")
                continue
            code_to_role = {v: k for k, v in codes.items()}
            sub["role"] = sub["commodity_code"].map(code_to_role)
            wide = (
                sub.pivot_table(
                    index=["region_code", "region_label", "region_level"],
                    columns="role",
                    values="estimate",
                    aggfunc="first",
                )
                .reset_index()
                .sort_values(["region_level", "region_code"])
            )
            wide.to_csv(out_path, index=False)
            log(f"  {commodity:<8s} wrote {out_path.name}: {len(wide)} rows")
        except Exception as e:
            warn(f"  {commodity:<8s} national/state save failed: {e}")

    # ----- (6) Sanity check: national yields -----------------------
    subsection("6. Sanity check: national yields vs XLSX-inspected values")
    expected = {
        "WHEAT_YIELD_F": 2.5,  # observed in XLSX 2026-05-15
        "BARLEY_YIELD_F": 2.7,  # observed in XLSX 2026-05-15
        # Canola not directly observed in screenshot; if absent the
        # sanity check will report missing rather than fail.
    }
    for yield_code, expected_value in expected.items():
        res = sanity_check_national_yield(df_long, yield_code, expected_value)
        if not res.get("valid"):
            warn(f"  {yield_code}: {res.get('reason')}")
            continue
        actual = res["actual"]
        frac = res["frac_diff"] * 100
        flag = "✓" if res["within_tolerance"] else "✗"
        log(
            f"  {yield_code}: expected {expected_value:.2f}, "
            f"actual {actual:.2f}, diff {frac:+.2f}% {flag}"
        )

    # ----- (7) Handoff ---------------------------------------------
    subsection("7. Handoff to Step 08 (OpenWeather validation)")
    log("Step 08 (src/ingestion/openweather.py) will:")
    log("  - retrieve OpenWeather historical daily data for sample regions")
    log("  - serve as Phase 09 validation comparison vs SILO/BoM (NEVER training)")
    log("  - persist as data/raw/openweather/<location>_<year>.csv")

    all_ok = all(
        c.get("status") in ("ok", "skipped") for c in commodity_summary.values()
    )
    if all_ok:
        ok("Phase 01 Step 07 complete")
        return 0
    else:
        warn("Phase 01 Step 07 partial. Review errors above.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
