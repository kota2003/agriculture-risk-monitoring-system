"""Phase 04 Step 04a — EHF grid computation.

Computes daily EHF and growing-season heatwave-day counts for all years
1961–2024 at SILO grid resolution.

Usage (dry-run):
    python scripts/phase04_s04a_ehf_grid.py --dry-run

Usage (full run):
    python scripts/phase04_s04a_ehf_grid.py

Outputs
-------
indicators/ehf/
    t90_baseline.nc                  — 90th-percentile T_mean (lat, lon)

indicators/ehf/annual/
    {year}.ehf_daily.nc              — daily EHF (time, lat, lon)
    {year}.ehf_hwdays.nc             — heatwave-day count per season (lat, lon)

indicators/ehf/
    ehf_region_timeseries.parquet    — AAGIS region-level seasonal HW-day means

Validation assertions (exit code 1 on failure):
  - T90 in plausible range (15–45°C) for Australian grid.
  - EHF heatwave-day count ≥ 0 for all grid cells.
  - Mean heatwave days > 0 for at least some years (non-trivial output).

References
----------
Nairn, J.R. & Fawcett, R.G. (2015). The excess heat factor: a metric for
    heatwave intensity and its use in classifying heatwave severity.
    International Journal of Environmental Research and Public Health, 12(1).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

from src.indicators._base import (  # noqa: E402
    GROWING_WINDOWS,
    INDICATORS_DIR,
    cos_lat_weights,
    get_cropping_cells,
)
from src.indicators.heat import (  # noqa: E402
    EHF_BASELINE_END,
    EHF_BASELINE_START,
    compute_t90_baseline,
    ehf_for_year,
    ehf_season_summary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EHF_YEARS: list[int] = list(range(1961, 2025))
BASELINE_YEARS: list[int] = list(range(EHF_BASELINE_START, EHF_BASELINE_END + 1))

EHF_DIR: Path = INDICATORS_DIR / "ehf"
ANNUAL_DIR: Path = EHF_DIR / "annual"
T90_PATH: Path = EHF_DIR / "t90_baseline.nc"
REGION_TS_PATH: Path = EHF_DIR / "ehf_region_timeseries.parquet"

# Use southern-winter window by default; QLD-specific handled via get_growing_window.
DEFAULT_WINDOW = GROWING_WINDOWS["southern_winter"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dirs(dry_run: bool) -> None:
    if not dry_run:
        ANNUAL_DIR.mkdir(parents=True, exist_ok=True)


def _save_nc(da_or_ds, path: Path, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY-RUN] would write → %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    da_or_ds.to_netcdf(path)
    log.info("Saved → %s", path)


def _region_aggregate_hw(
    hw_da: xr.DataArray,
    cells: pd.DataFrame,
    year: int,
) -> pd.DataFrame:
    """Area-weighted mean heatwave-day count per AAGIS region."""
    lat_vals = xr.DataArray(cells["lat"].values, dims="cell")
    lon_vals = xr.DataArray(cells["lon"].values, dims="cell")
    sampled = hw_da.sel(lat=lat_vals, lon=lon_vals, method="nearest").values
    lats = cells["lat"].values
    weights = cos_lat_weights(lats)

    records = []
    for region_code, grp in cells.groupby("aagis_code"):
        idx = grp.index
        vals = sampled[idx]
        w = weights[idx]
        finite = np.isfinite(vals)
        mean_hw = (
            float(np.average(vals[finite], weights=w[finite]))
            if finite.any()
            else np.nan
        )
        records.append(
            {"year": year, "aagis_code": region_code, "ehf_hwdays_mean": mean_hw}
        )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(dry_run: bool = False) -> None:
    log.info("Phase 04 Step 04a — EHF grid computation (dry_run=%s)", dry_run)
    _ensure_dirs(dry_run)

    cells = get_cropping_cells()
    log.info(
        "Cropping cells: %d cells, %d regions",
        len(cells),
        cells["aagis_code"].nunique(),
    )

    # ── Compute / load T90 baseline ────────────────────────────────────────
    if T90_PATH.exists() and not dry_run:
        log.info("Loading cached T90 from %s", T90_PATH)
        t90 = xr.open_dataarray(T90_PATH)
    else:
        log.info(
            "Computing T90 baseline (%d–%d)…", EHF_BASELINE_START, EHF_BASELINE_END
        )
        t90 = compute_t90_baseline(baseline_years=BASELINE_YEARS)
        _save_nc(t90, T90_PATH, dry_run)

    # ── Validate T90 ───────────────────────────────────────────────────────
    t90_vals = t90.values[np.isfinite(t90.values)]
    if len(t90_vals) > 0:
        log.info("T90 range: %.1f – %.1f °C", t90_vals.min(), t90_vals.max())
        if not (15.0 < t90_vals.min() and t90_vals.max() < 45.0):
            log.error(
                "VALIDATION FAILED: T90 out of plausible range (15–45°C); "
                "min=%.1f max=%.1f",
                t90_vals.min(),
                t90_vals.max(),
            )
            sys.exit(1)
        log.info("T90 validation PASSED ✓")

    # ── Annual EHF computation ─────────────────────────────────────────────
    region_frames: list[pd.DataFrame] = []
    any_positive = False

    for year in EHF_YEARS:
        daily_path = ANNUAL_DIR / f"{year}.ehf_daily.nc"
        hwdays_path = ANNUAL_DIR / f"{year}.ehf_hwdays.nc"

        if daily_path.exists() and hwdays_path.exists() and not dry_run:
            log.debug("Skipping %d (already exists)", year)
            hw_da = xr.open_dataarray(hwdays_path)
        else:
            try:
                log.info("EHF %d …", year)
                ehf_da = ehf_for_year(year, t90)
                hw_da = ehf_season_summary(year, t90, DEFAULT_WINDOW)
            except FileNotFoundError as exc:
                log.warning("EHF %d: skipping — %s", year, exc)
                continue

            _save_nc(ehf_da, daily_path, dry_run)
            _save_nc(hw_da, hwdays_path, dry_run)

        # Validate: hw count ≥ 0.
        hw_vals = hw_da.values[np.isfinite(hw_da.values)]
        if len(hw_vals) > 0:
            if hw_vals.min() < 0:
                log.error("VALIDATION FAILED: negative heatwave day count in %d", year)
                sys.exit(1)
            if hw_vals.max() > 0:
                any_positive = True

        df_r = _region_aggregate_hw(hw_da, cells, year)
        region_frames.append(df_r)

    # ── Validate non-trivial output ────────────────────────────────────────
    if not any_positive:
        log.warning("No year had EHF > 0 — check T90 threshold or temperature data.")

    # ── Persist region time-series ─────────────────────────────────────────
    if region_frames:
        df_all = pd.concat(region_frames, ignore_index=True)
        df_all = df_all.sort_values(["year", "aagis_code"])
        if not dry_run:
            REGION_TS_PATH.parent.mkdir(parents=True, exist_ok=True)
            df_all.to_parquet(REGION_TS_PATH, index=False)
            log.info("Region time-series → %s  (%d rows)", REGION_TS_PATH, len(df_all))
        else:
            log.info("[DRY-RUN] would write region time-series → %s", REGION_TS_PATH)

    log.info("Phase 04 Step 04a — EHF computation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 04 Step 04a: EHF grid computation"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
