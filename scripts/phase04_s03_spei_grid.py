"""Phase 04 Step 03 — SPEI grid computation.

Computes SPEI-3 and SPEI-12 for all years 1970–2024 at SILO grid resolution.
Persists fitted parameters and annual SPEI arrays to the indicators directory.

Usage (dry-run):
    python scripts/phase04_s03_spei_grid.py --dry-run

Usage (full run):
    python scripts/phase04_s03_spei_grid.py

Outputs
-------
indicators/spei/params/
    spei_params_k{k}.nc              — fitted log-logistic params (1970-1999 baseline)

indicators/spei/annual/
    {year}.spei{k}.nc                — annual SPEI array (month, lat, lon)

indicators/spei/
    spei_region_timeseries.parquet   — AAGIS region-level monthly SPEI time-series

Validation assertions (exit code 1 on failure):
  - Fitted beta > 1 for ≥ 80% of finite cells (all calendar months).
  - SPEI mean ∈ (−0.5, 0.5) over 1970–1999 baseline period.
  - SPEI std ∈ (0.5, 1.5) over 1970–1999 baseline period.

References
----------
Vicente-Serrano, S.M., Begueria, S. & Lopez-Moreno, J.I. (2010).
    Journal of Climate, 23, 1696-1718.
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

from src.indicators._base import (
    INDICATORS_DIR,
    cos_lat_weights,
    get_cropping_cells,
)  # noqa: E402
from src.indicators.drought import (  # noqa: E402
    EVAP_BASELINE_END,
    EVAP_BASELINE_START,
    SPEI_SCALES,
    fit_spei_params,
    spei_for_year,
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

SPEI_YEARS: list[int] = list(range(1970, 2025))  # 1970–2024
BASELINE_YEARS: list[int] = list(range(EVAP_BASELINE_START, EVAP_BASELINE_END + 1))

SPEI_DIR: Path = INDICATORS_DIR / "spei"
PARAMS_DIR: Path = SPEI_DIR / "params"
ANNUAL_DIR: Path = SPEI_DIR / "annual"

REGION_TS_PATH: Path = SPEI_DIR / "spei_region_timeseries.parquet"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dirs(dry_run: bool) -> None:
    if not dry_run:
        for d in (PARAMS_DIR, ANNUAL_DIR):
            d.mkdir(parents=True, exist_ok=True)


def _save_nc(da_or_ds, path: Path, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY-RUN] would write → %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    da_or_ds.to_netcdf(path)
    log.info("Saved → %s", path)


def _region_aggregate(
    spei_da: xr.DataArray,
    cells: pd.DataFrame,
    year: int,
    k: int,
) -> pd.DataFrame:
    """Area-weighted mean SPEI per AAGIS region per month."""
    lat_vals = xr.DataArray(cells["lat"].values, dims="cell")
    lon_vals = xr.DataArray(cells["lon"].values, dims="cell")
    sampled = spei_da.sel(lat=lat_vals, lon=lon_vals, method="nearest")
    # sampled dims: (month, cell)
    spei_np = sampled.values  # (12, n_cells)

    lats = cells["lat"].values
    weights = cos_lat_weights(lats)

    records = []
    for m in range(12):
        for region_code, grp in cells.groupby("aagis_code"):
            idx = grp.index
            vals = spei_np[m, idx]
            w = weights[idx]
            finite = np.isfinite(vals)
            if not finite.any():
                mean_spei = np.nan
            else:
                mean_spei = np.average(vals[finite], weights=w[finite])
            records.append(
                {
                    "year": year,
                    "month": m + 1,
                    "aagis_code": region_code,
                    f"spei{k}_mean": mean_spei,
                }
            )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(dry_run: bool = False) -> None:
    log.info("Phase 04 Step 03 — SPEI grid computation (dry_run=%s)", dry_run)
    _ensure_dirs(dry_run)

    cells = get_cropping_cells()
    log.info(
        "Cropping cells loaded: %d cells, %d regions",
        len(cells),
        cells["aagis_code"].nunique(),
    )

    region_frames: list[pd.DataFrame] = []

    for k in SPEI_SCALES:
        log.info("─── SPEI-%d ─────────────────────────────────────────────────", k)

        # ── Fit parameters ────────────────────────────────────────────────
        params_path = PARAMS_DIR / f"spei_params_k{k}.nc"
        if params_path.exists() and not dry_run:
            log.info("Loading cached params from %s", params_path)
            params = xr.open_dataset(params_path)
        else:
            log.info(
                "Fitting log-logistic params on baseline %d–%d (k=%d)...",
                EVAP_BASELINE_START,
                EVAP_BASELINE_END,
                k,
            )
            params = fit_spei_params(baseline_years=BASELINE_YEARS, k=k)
            _save_nc(params, params_path, dry_run)

        # ── Validate fitted params ─────────────────────────────────────────
        beta = params["ll_beta"].values
        finite_beta = beta[np.isfinite(beta)]
        if len(finite_beta) > 0:
            frac_valid = np.mean(finite_beta > 1.0)
            log.info(
                "SPEI-%d: %.1f%% of fitted cells have beta > 1", k, frac_valid * 100
            )
            if frac_valid < 0.80:
                log.error(
                    "VALIDATION FAILED: fewer than 80%% of cells have beta > 1 "
                    "(got %.1f%%)",
                    frac_valid * 100,
                )
                sys.exit(1)
        else:
            log.warning("No finite beta values — all cells degenerate. Check data.")

        # ── Annual SPEI computation ────────────────────────────────────────
        spei_baseline_vals: list[np.ndarray] = []

        for year in SPEI_YEARS:
            out_path = ANNUAL_DIR / f"{year}.spei{k}.nc"
            if out_path.exists() and not dry_run:
                log.debug("Skipping %d (already exists)", year)
                spei_da = xr.open_dataarray(out_path)
            else:
                try:
                    spei_da = spei_for_year(year, params)
                except FileNotFoundError as exc:
                    log.warning("SPEI-%d %d: skipping — %s", k, year, exc)
                    continue
                _save_nc(spei_da, out_path, dry_run)

            # Collect baseline SPEI for validation.
            if EVAP_BASELINE_START <= year <= EVAP_BASELINE_END:
                spei_baseline_vals.append(spei_da.values)

            # Region aggregation.
            df_region = _region_aggregate(spei_da, cells, year, k)
            region_frames.append(df_region)

        # ── Validate SPEI distribution over baseline period ───────────────
        if spei_baseline_vals:
            all_baseline = np.concatenate([v.ravel() for v in spei_baseline_vals])
            finite_bl = all_baseline[np.isfinite(all_baseline)]
            if len(finite_bl) > 0:
                mean_bl = float(np.mean(finite_bl))
                std_bl = float(np.std(finite_bl))
                log.info(
                    "SPEI-%d baseline validation: mean=%.3f std=%.3f",
                    k,
                    mean_bl,
                    std_bl,
                )
                if not (-0.5 < mean_bl < 0.5):
                    log.error(
                        "VALIDATION FAILED: SPEI-%d baseline mean=%.3f not in (-0.5, 0.5)",
                        k,
                        mean_bl,
                    )
                    sys.exit(1)
                if not (0.5 < std_bl < 1.5):
                    log.error(
                        "VALIDATION FAILED: SPEI-%d baseline std=%.3f not in (0.5, 1.5)",
                        k,
                        std_bl,
                    )
                    sys.exit(1)
                log.info("SPEI-%d baseline validation PASSED ✓", k)

    # ── Persist region time-series ─────────────────────────────────────────
    if region_frames:
        df_all = pd.concat(region_frames, ignore_index=True)
        df_all = df_all.sort_values(["year", "month", "aagis_code"])
        # Pivot k columns into single rows (merge on year/month/aagis_code).
        key_cols = ["year", "month", "aagis_code"]
        df_merged = df_all.groupby(key_cols, sort=False).first().reset_index()
        if not dry_run:
            REGION_TS_PATH.parent.mkdir(parents=True, exist_ok=True)
            df_merged.to_parquet(REGION_TS_PATH, index=False)
            log.info(
                "Region time-series → %s  (%d rows)", REGION_TS_PATH, len(df_merged)
            )
        else:
            log.info("[DRY-RUN] would write region time-series → %s", REGION_TS_PATH)

    log.info("Phase 04 Step 03 — SPEI computation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 04 Step 03: SPEI grid computation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be written without writing any files.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
