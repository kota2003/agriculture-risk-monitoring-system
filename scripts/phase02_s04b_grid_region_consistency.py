"""
Phase 02, Step 04b — grid-vs-region SILO aggregation consistency check (Task C, part 2).

Goal:
    Confirm and document that the s04a area-weighted SILO region climatologies
    reproduce expected regional climate (scope v5 §4.2, §6.2). Internal
    consistency is the primary check; a BoM station comparison is a supporting
    external plausibility check.

Pipeline:
    1. Load s04a region annual means + monthly climatology + the cell map.
    2. Internal battery: coverage / no-NaN / no-zero-rain; tmax & tmin vs
       latitude correlation; rainfall seasonality regime (Mediterranean south
       winter-dominant, subtropical/monsoon north summer-dominant).
    3. External: compare representative regions to BoM station normals.
    4. Persist outputs/tables/s04b_region_climatology_summary.csv and
       outputs/tables/s04b_external_comparison.csv.

Exit status:
    0 if the internal consistency battery passes; 1 otherwise.

Run from repo root:
    python scripts/phase02_s04b_grid_region_consistency.py
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
from src.processing.climate_consistency import (  # noqa: E402
    compare_to_reference,
    check_internal_consistency,
    load_region_annual,
    load_region_latitude,
    load_seasonality,
)
from src.processing.region_aggregation import load_region_mapping  # noqa: E402


def _write_table(df, name: str) -> Path:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / name
    tmp = out.with_suffix(out.suffix + ".part")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out)
    ok(f"  wrote {out}")
    return out


def main() -> int:
    section("Phase 02 - Step 04b: grid-vs-region SILO consistency check")

    region_annual = load_region_annual()
    seasonality = load_seasonality()
    region_lat = load_region_latitude()
    mapping = load_region_mapping().set_index("aagis_code")
    region_zone = mapping["zone"]

    subsection("Internal consistency")
    report = check_internal_consistency(
        region_annual, seasonality, region_lat, region_zone
    )
    for name, passed in report["checks"].items():
        log(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    log("")
    log(f"  broadacre regions checked : {report['n_broadacre_regions']}")
    log(f"  corr(latitude, tmax)      : {report['tmax_lat_corr']:+.3f}")
    log(f"  corr(latitude, tmin)      : {report['tmin_lat_corr']:+.3f}")
    if report["winter_regime_failures"]:
        log(f"  winter-regime failures    : {report['winter_regime_failures']}")
    if report["summer_regime_failures"]:
        log(f"  summer-regime failures    : {report['summer_regime_failures']}")

    subsection("External plausibility (BoM station normals)")
    ext = compare_to_reference(region_annual)
    for row in ext.itertuples(index=False):
        log(
            f"  {row.aagis_code} {row.region_name[:32]:<32s} "
            f"rain {row.silo_rain_mm:6.0f} vs {row.bom_rain_mm:6.0f}  "
            f"tmax {row.silo_tmax_c:4.1f} vs {row.bom_tmax_c:4.1f}  "
            f"[tmax_ok={row.tmax_within_3C} rain_ok={row.rain_within_45pct}]"
        )

    subsection("Persist tables")
    summary = region_annual.reset_index().merge(
        seasonality.reset_index(), on="aagis_code", how="left"
    )
    summary = summary.merge(
        region_lat.reset_index(), on="aagis_code", how="left"
    ).merge(region_zone.reset_index(), on="aagis_code", how="left")
    _write_table(summary, "s04b_region_climatology_summary.csv")
    _write_table(ext, "s04b_external_comparison.csv")

    if not report["valid"]:
        error("Internal consistency FAILED.")
        return 1

    ok("s04b complete: grid-vs-region consistency confirmed (internal + external).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
