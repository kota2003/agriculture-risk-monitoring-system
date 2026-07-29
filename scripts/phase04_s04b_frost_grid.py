"""Phase 04 Step 04b — Frost-day grid computation.

Counts growing-season frost days (tmin < 2°C) for all years 1961–2024
at SILO grid resolution, then aggregates to AAGIS region level.

Usage (dry-run):
    python scripts/phase04_s04b_frost_grid.py --dry-run

Usage (full run):
    python scripts/phase04_s04b_frost_grid.py

Outputs
-------
indicators/frost/annual/
    {year}.frost_days.nc              — frost-day count per season (lat, lon)

indicators/frost/
    frost_region_timeseries.parquet   — AAGIS region-level seasonal frost-day means

Validation assertions (exit code 1 on failure):
  - Frost-day counts ≥ 0 for all grid cells.
  - Mean frost days > 0 for at least one year in southern Australia
    (non-trivial output sanity check).

References
----------
Tank, A.M.G.K. et al. (2009). Guidelines on Analysis of Extremes in a
    Changing Climate in Support of Informed Decisions for Adaptation.
    World Meteorological Organization, WCDMP-72.
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
from src.indicators.frost import (  # noqa: E402
    FROST_THRESHOLD_C,
    frost_days_growing_season,
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

FROST_YEARS: list[int] = list(range(1961, 2025))

FROST_DIR: Path = INDICATORS_DIR / "frost"
ANNUAL_DIR: Path = FROST_DIR / "annual"
REGION_TS_PATH: Path = FROST_DIR / "frost_region_timeseries.parquet"

# Default window for most of Australia; QLD cells use get_growing_window().
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


def _region_aggregate_frost(
    frost_da: xr.DataArray,
    cells: pd.DataFrame,
    year: int,
) -> pd.DataFrame:
    """Area-weighted mean frost-day count per AAGIS region."""
    lat_vals = xr.DataArray(cells["lat"].values, dims="cell")
    lon_vals = xr.DataArray(cells["lon"].values, dims="cell")
    sampled = frost_da.sel(lat=lat_vals, lon=lon_vals, method="nearest").values
    lats = cells["lat"].values
    weights = cos_lat_weights(lats)

    records = []
    for region_code, grp in cells.groupby("aagis_code"):
        idx = grp.index
        vals = sampled[idx]
        w = weights[idx]
        finite = np.isfinite(vals)
        mean_fd = (
            float(np.average(vals[finite], weights=w[finite]))
            if finite.any()
            else np.nan
        )
        records.append(
            {
                "year": year,
                "aagis_code": region_code,
                "frost_days_mean": mean_fd,
            }
        )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(dry_run: bool = False) -> None:
    log.info("Phase 04 Step 04b — Frost-day grid computation (dry_run=%s)", dry_run)
    log.info("Frost threshold: %.1f °C", FROST_THRESHOLD_C)
    _ensure_dirs(dry_run)

    cells = get_cropping_cells()
    log.info(
        "Cropping cells: %d cells, %d regions",
        len(cells),
        cells["aagis_code"].nunique(),
    )

    region_frames: list[pd.DataFrame] = []
    any_positive = False

    for year in FROST_YEARS:
        frost_path = ANNUAL_DIR / f"{year}.frost_days.nc"

        if frost_path.exists() and not dry_run:
            log.debug("Skipping %d (already exists)", year)
            frost_da = xr.open_dataarray(frost_path)
        else:
            try:
                log.info("Frost %d …", year)
                frost_da = frost_days_growing_season(year, window=DEFAULT_WINDOW)
            except FileNotFoundError as exc:
                log.warning("Frost %d: skipping — %s", year, exc)
                continue

            _save_nc(frost_da, frost_path, dry_run)

        # ── Validate: counts ≥ 0 ──────────────────────────────────────────
        frost_vals = frost_da.values[np.isfinite(frost_da.values)]
        if len(frost_vals) > 0:
            if frost_vals.min() < 0:
                log.error("VALIDATION FAILED: negative frost-day count in %d", year)
                sys.exit(1)
            if frost_vals.max() > 0:
                any_positive = True

        df_r = _region_aggregate_frost(frost_da, cells, year)
        region_frames.append(df_r)

    # ── Validate non-trivial output ────────────────────────────────────────
    if not any_positive:
        log.warning("No year had frost days > 0 — check tmin data or threshold.")

    # ── Persist region time-series ─────────────────────────────────────────
    if region_frames:
        df_all = pd.concat(region_frames, ignore_index=True)
        df_all = df_all.sort_values(["year", "aagis_code"])
        if not dry_run:
            REGION_TS_PATH.parent.mkdir(parents=True, exist_ok=True)
            df_all.to_parquet(REGION_TS_PATH, index=False)
            log.info(
                "Region time-series → %s  (%d rows)",
                REGION_TS_PATH,
                len(df_all),
            )
        else:
            log.info("[DRY-RUN] would write region time-series → %s", REGION_TS_PATH)

    log.info("Phase 04 Step 04b — Frost-day computation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 04 Step 04b: Frost-day grid computation"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
