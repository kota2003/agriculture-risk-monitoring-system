"""
src/processing/silo_climatology.py — full-record SILO region climatology.

Phase 03, Step 02. Extends the Phase 02 region aggregation (which produced the
1991–2020 reference-period means) to the FULL SILO record — 1961–2024, with
evap_pan restricted to 1970–2024 (Phase 01 finding #6) — so the Phase 03 climate
EDA can characterise interannual variation, trends, and WMO-baseline anomalies by
AAGIS region.

Design:
  * Annual-only aggregation. Each (variable, year) file is opened once and reduced
    over time (mean for state variables, sum for rainfall — `AGG_RULE`); the active
    cropping cells are sampled by coordinate-resolved indices (Phase 02's
    latitude-flip-safe `resolve_cell_grid_indices`) and cos(lat)-area-weighted to
    region means (`weighted_region_means`). The monthly climatology is NOT
    recomputed here: seasonality stays on the Phase 02 1991–2020 product; only the
    annual series is extended, which halves the per-file I/O.
  * Per-variable year ranges. evap_pan starts 1970; all other variables start 1961.
  * WMO baselines. Region baselines for 1961–1990 and 1991–2020 are derived from
    the annual series as the mean of annual values over each window (mean annual
    total for rainfall; climatological mean for state variables). evap_pan's
    1961–1990 baseline necessarily uses 1970–1990 (n_years reported).

Products (paths):
  data/processed/silo_region_means/annual_1961_2024.csv   (annual series; gitignored)
  outputs/tables/s02_region_climate_baselines.csv          (baselines; committed)

The heavy per-year I/O is intended to run on the user's machine; the weighting
core is Phase 02's, unit-tested independently of any data.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.log_utils import log
from src.paths import TABLES_DIR
from src.processing.silo_region_aggregation import (
    AGG_RULE,
    REGION_MEANS_DIR,
    SILO_PROCESSED_DIR,
    resolve_cell_grid_indices,
    weighted_region_means,
)

FULL_RECORD_START = 1961
FULL_RECORD_END = 2024
EVAP_PAN_START = 1970  # Phase 01 finding #6: evap_pan observed only from 1970.

# WMO standard reference periods (scope §3.3).
BASELINES: dict[str, tuple[int, int]] = {
    "1961-1990": (1961, 1990),
    "1991-2020": (1991, 2020),
}

ANNUAL_FULL_RECORD_NAME = "annual_1961_2024"
BASELINES_TABLE = "s02_region_climate_baselines.csv"


def variable_year_start(variable: str) -> int:
    """First reliably-observed year for a SILO variable (evap_pan from 1970)."""
    return EVAP_PAN_START if variable == "evap_pan" else FULL_RECORD_START


def variable_years(variable: str) -> range:
    """Inclusive year range for a variable over the full record."""
    return range(variable_year_start(variable), FULL_RECORD_END + 1)


def _open_variable_year(variable: str, year: int, processed_dir: Path):
    """Open one processed (masked) SILO NetCDF; return (dataset, dataarray)."""
    import xarray as xr

    path = Path(processed_dir) / variable / f"{year}.{variable}.nc"
    if not path.exists():
        raise FileNotFoundError(f"SILO processed file not found: {path}")
    ds = xr.open_dataset(path)
    da = ds[variable] if variable in ds.data_vars else ds[list(ds.data_vars)[0]]
    return ds, da


def aggregate_annual_full_record(
    cell_df: pd.DataFrame,
    variables=None,
    processed_dir: str | Path = SILO_PROCESSED_DIR,
) -> pd.DataFrame:
    """
    Annual cos(lat)-weighted region means over the full record, per variable.

    Reuses the Phase 02 weighting core. Grid indices are resolved once by
    coordinate value (robust to the mask/data latitude-ordering difference).

    Returns
    -------
    pandas.DataFrame
        Columns ``aagis_code, region_name, value, n_cells, year, variable``.
    """
    variables = tuple(variables) if variables is not None else tuple(AGG_RULE)
    codes = cell_df["aagis_code"].to_numpy()
    names = cell_df["region_name"].to_numpy()
    weights = cell_df["weight"].to_numpy()

    grid_idx: tuple[np.ndarray, np.ndarray] | None = None
    frames: list[pd.DataFrame] = []

    for variable in variables:
        rule = AGG_RULE[variable]
        years = variable_years(variable)
        log(f"  {variable}: aggregating {years.start}-{years.stop - 1} annual means")
        for year in years:
            ds, da = _open_variable_year(variable, year, processed_dir)
            if grid_idx is None:
                grid_idx = resolve_cell_grid_indices(
                    cell_df, da["lat"].values, da["lon"].values
                )
            rows, cols = grid_idx
            annual_field = (
                da.sum("time", min_count=1) if rule == "sum" else da.mean("time")
            )
            annual_vals = np.asarray(annual_field.values, dtype=float)[rows, cols]
            ds.close()

            means = weighted_region_means(annual_vals, codes, names, weights)
            means["year"] = int(year)
            means["variable"] = variable
            frames.append(means)

    return pd.concat(frames, ignore_index=True)


def compute_baselines(annual_df: pd.DataFrame) -> pd.DataFrame:
    """
    Region baselines (mean of annual values) for each WMO reference period.

    Returns
    -------
    pandas.DataFrame
        Columns ``aagis_code, region_name, variable, baseline, value, n_years``.
        For evap_pan the 1961–1990 baseline uses only 1970–1990 (n_years < 30).
    """
    out: list[pd.DataFrame] = []
    for label, (y0, y1) in BASELINES.items():
        sub = annual_df[(annual_df["year"] >= y0) & (annual_df["year"] <= y1)]
        grp = (
            sub.groupby(["aagis_code", "region_name", "variable"], sort=True)
            .agg(value=("value", "mean"), n_years=("year", "nunique"))
            .reset_index()
        )
        grp["baseline"] = label
        out.append(grp)
    cols = ["aagis_code", "region_name", "variable", "baseline", "value", "n_years"]
    return pd.concat(out, ignore_index=True)[cols]


def check_full_record(annual_df: pd.DataFrame) -> list[tuple[str, bool, str]]:
    """Structural + physical sanity checks on the full-record annual series."""
    checks: list[tuple[str, bool, str]] = []
    df = annual_df.copy()
    df["aagis_code"] = df["aagis_code"].astype(str)

    n_regions = df["aagis_code"].nunique()
    checks.append(("region_count_30", n_regions == 30, f"{n_regions} regions"))

    for v in sorted(df["variable"].unique()):
        yrs = df.loc[df["variable"] == v, "year"]
        want_start = variable_year_start(v)
        good = int(yrs.min()) == want_start and int(yrs.max()) == FULL_RECORD_END
        checks.append(
            (
                f"{v}_year_range",
                good,
                f"{int(yrs.min())}-{int(yrs.max())} (want {want_start}-{FULL_RECORD_END})",
            )
        )

    n_years_by_var = {
        v: (FULL_RECORD_END - variable_year_start(v) + 1)
        for v in df["variable"].unique()
    }
    exp_rows = n_regions * sum(n_years_by_var.values())
    checks.append(
        ("row_count", len(df) == exp_rows, f"{len(df)} rows (want {exp_rows})")
    )

    n_nan = int(df["value"].isna().sum())
    checks.append(("no_nan_values", n_nan == 0, f"{n_nan} NaN values"))

    piv = df.pivot_table(
        index=["aagis_code", "year"], columns="variable", values="value"
    )
    if {"max_temp", "min_temp"}.issubset(piv.columns):
        bad = int((piv["max_temp"] <= piv["min_temp"]).sum())
        checks.append(("tmax_gt_tmin", bad == 0, f"{bad} region-years with tmax<=tmin"))
    if "daily_rain" in piv.columns:
        bad = int((piv["daily_rain"] < 0).sum())
        checks.append(("rain_nonneg", bad == 0, f"{bad} negative annual rainfall"))
    return checks


def write_annual_full_record(annual_df: pd.DataFrame) -> Path:
    """Atomic (.part -> rename) write of the annual series to processed dir."""
    REGION_MEANS_DIR.mkdir(parents=True, exist_ok=True)
    out = REGION_MEANS_DIR / f"{ANNUAL_FULL_RECORD_NAME}.csv"
    tmp = out.with_suffix(out.suffix + ".part")
    annual_df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out)
    return out


def write_baselines(baselines_df: pd.DataFrame) -> Path:
    """Atomic (.part -> rename) write of the baselines table to outputs/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / BASELINES_TABLE
    tmp = out.with_suffix(".csv.part")
    baselines_df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out)
    return out


def load_annual_full_record(path: str | Path | None = None) -> pd.DataFrame:
    """Load the persisted full-record annual series (aagis_code as str)."""
    p = (
        REGION_MEANS_DIR / f"{ANNUAL_FULL_RECORD_NAME}.csv"
        if path is None
        else Path(path)
    )
    return pd.read_csv(p, dtype={"aagis_code": str})


def load_baselines(path: str | Path | None = None) -> pd.DataFrame:
    """Load the persisted baselines table (aagis_code as str)."""
    p = TABLES_DIR / BASELINES_TABLE if path is None else Path(path)
    return pd.read_csv(p, dtype={"aagis_code": str})


__all__ = [
    "FULL_RECORD_START",
    "FULL_RECORD_END",
    "EVAP_PAN_START",
    "BASELINES",
    "ANNUAL_FULL_RECORD_NAME",
    "BASELINES_TABLE",
    "variable_year_start",
    "variable_years",
    "aggregate_annual_full_record",
    "compute_baselines",
    "check_full_record",
    "write_annual_full_record",
    "write_baselines",
    "load_annual_full_record",
    "load_baselines",
]
