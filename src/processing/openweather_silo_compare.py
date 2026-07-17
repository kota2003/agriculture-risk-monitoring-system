"""
src/processing/openweather_silo_compare.py — OpenWeather vs SILO comparison.

Phase 02, Step 06 (Task D; scope v5 §5.6.4). Quantifies the agreement between
the OpenWeather One Call day-summary API and the gold-standard SILO gridded
data at the 10 sampled AAGIS region centroids over 2022-2024, as an auxiliary
methodological side-finding (Pillar 6). Reported per centroid x variable:
RMSE, bias (OpenWeather - SILO), Pearson correlation.

Variable pairing:
    tmax     : OpenWeather ``tmax_c``     <-> SILO ``max_temp``
    tmin     : OpenWeather ``tmin_c``     <-> SILO ``min_temp``
    rain     : OpenWeather ``precip_mm``  <-> SILO ``daily_rain``
    humidity : OpenWeather ``humidity_pct`` (afternoon RH) <-> SILO relative
               humidity DERIVED from vapour pressure and temperature via the
               Tetens saturation formula: RH = 100 * vp / e_s(tmax). This is an
               approximation (SILO ships vapour pressure, not RH; the afternoon
               temperature is proxied by the daily max), so the humidity result
               is secondary and carries a caveat.

SILO extraction:
    OpenWeather was queried at each region's representative-point centroid; the
    masked SILO archive retains only broadacre cropping cells, so SILO is
    sampled at the NEAREST cropping cell to each centroid (from the s04a
    cell-region map). The offset distance is reported; a large offset flags a
    weaker comparison.

Bias sign convention: ``bias = mean(OpenWeather - SILO)`` — how far the
commercial API departs from the SILO reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.log_utils import log, warn
from src.paths import DATA_PROCESSED, DATA_RAW

# ---------------------------------------------------------------------------
# Locations & constants
# ---------------------------------------------------------------------------

OPENWEATHER_DIR: Path = DATA_RAW / "openweather"
SILO_PROCESSED_DIR: Path = DATA_PROCESSED / "silo"
CELL_REGION_MAP_PARQUET: Path = DATA_PROCESSED / "silo_cell_region_map.parquet"

COMPARE_YEARS: tuple[int, ...] = (2022, 2023, 2024)

# The 10 OpenWeather-sampled AAGIS region centroids (Phase 01 s08).
CENTROID_CODES: tuple[str, ...] = (
    "121",
    "122",
    "123",
    "221",
    "222",
    "322",
    "421",
    "521",
    "522",
    "631",
)

# (label, OpenWeather column, SILO column). SILO 'humidity' is derived (see
# _derive_silo_rh); it uses the synthetic SILO column name 'silo_rh'.
COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("tmax", "tmax_c", "max_temp"),
    ("tmin", "tmin_c", "min_temp"),
    ("rain", "precip_mm", "daily_rain"),
    ("humidity", "humidity_pct", "silo_rh"),
)

# SILO variables needed for the comparison (vp + max_temp -> derived RH).
_SILO_VARS: tuple[str, ...] = ("max_temp", "min_temp", "daily_rain", "vp")

OFFSET_WARN_KM: float = 30.0  # flag centroids whose nearest cropping cell is far


@dataclass(frozen=True)
class NearestCell:
    lat: float
    lon: float
    dist_km: float


# ---------------------------------------------------------------------------
# Small numeric helpers (pure; unit tested)
# ---------------------------------------------------------------------------


def haversine_km(lat1: float, lon1: float, lat2, lon2):
    """Great-circle distance (km); scalars or numpy arrays for the 2nd point."""
    r1 = np.deg2rad(lat1)
    r2 = np.deg2rad(np.asarray(lat2, dtype=float))
    dlat = np.deg2rad(np.asarray(lat2, dtype=float) - lat1)
    dlon = np.deg2rad(np.asarray(lon2, dtype=float) - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(r1) * np.cos(r2) * np.sin(dlon / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def saturation_vapour_pressure_hpa(temp_c):
    """Tetens saturation vapour pressure (hPa) at temperature ``temp_c``."""
    t = np.asarray(temp_c, dtype=float)
    return 6.108 * np.exp(17.27 * t / (t + 237.3))


def _derive_silo_rh(vp_hpa, tmax_c):
    """Approximate relative humidity (%) from SILO vapour pressure + max temp."""
    es = saturation_vapour_pressure_hpa(tmax_c)
    return 100.0 * np.asarray(vp_hpa, dtype=float) / es


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_openweather(code: str, years=COMPARE_YEARS) -> pd.DataFrame:
    """Load and concatenate the OpenWeather daily records for one centroid."""
    frames = []
    for year in years:
        path = OPENWEATHER_DIR / f"{code}_{year}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"OpenWeather file not found: {path}")
        frames.append(pd.read_parquet(path))
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df


def nearest_cropping_cell(
    lat: float, lon: float, cell_map: pd.DataFrame
) -> NearestCell:
    """Nearest cropping cell (from the s04a cell-region map) to a point."""
    d = haversine_km(lat, lon, cell_map["lat"].values, cell_map["lon"].values)
    i = int(np.argmin(d))
    return NearestCell(
        lat=float(cell_map["lat"].iloc[i]),
        lon=float(cell_map["lon"].iloc[i]),
        dist_km=float(d[i]),
    )


def extract_silo_daily(
    variable: str,
    cell: NearestCell,
    years=COMPARE_YEARS,
    processed_dir: Path = SILO_PROCESSED_DIR,
) -> pd.Series:
    """Daily SILO series for one variable at the given cropping cell."""
    import xarray as xr

    parts = []
    for year in years:
        path = Path(processed_dir) / variable / f"{year}.{variable}.nc"
        if not path.exists():
            raise FileNotFoundError(f"SILO file not found: {path}")
        ds = xr.open_dataset(path)
        da = ds[variable] if variable in ds.data_vars else ds[list(ds.data_vars)[0]]
        s = da.sel(lat=cell.lat, lon=cell.lon, method="nearest")
        idx = pd.to_datetime(s["time"].values).normalize()
        parts.append(pd.Series(np.asarray(s.values, dtype=float), index=idx))
        ds.close()
    return pd.concat(parts).rename(variable)


# ---------------------------------------------------------------------------
# Comparison assembly + metrics
# ---------------------------------------------------------------------------


def build_comparison(
    codes=CENTROID_CODES,
    years=COMPARE_YEARS,
    cell_map_path: str | Path = CELL_REGION_MAP_PARQUET,
) -> pd.DataFrame:
    """
    Assemble the paired daily OpenWeather / SILO table across all centroids.

    Returns
    -------
    pandas.DataFrame
        Long form: ``aagis_code, date, variable, ow, silo, offset_km``.
    """
    cell_map = pd.read_parquet(cell_map_path)
    out = []
    for code in codes:
        ow = load_openweather(code, years)
        clat, clon = float(ow["lat"].iloc[0]), float(ow["lon"].iloc[0])
        cell = nearest_cropping_cell(clat, clon, cell_map)
        if cell.dist_km > OFFSET_WARN_KM:
            warn(
                f"  centroid {code}: nearest cropping cell is "
                f"{cell.dist_km:.0f} km away"
            )

        silo = pd.DataFrame({v: extract_silo_daily(v, cell, years) for v in _SILO_VARS})
        silo["silo_rh"] = _derive_silo_rh(silo["vp"], silo["max_temp"])

        merged = ow.set_index("date").join(silo, how="inner")
        for label, ow_col, silo_col in COMPARISONS:
            sub = merged[[ow_col, silo_col]].dropna()
            if sub.empty:
                continue
            part = sub.reset_index().rename(
                columns={ow_col: "ow", silo_col: "silo", "index": "date"}
            )
            if "date" not in part.columns:  # index name fallback
                part = part.rename(columns={part.columns[0]: "date"})
            part["aagis_code"] = code
            part["variable"] = label
            part["offset_km"] = round(cell.dist_km, 1)
            out.append(
                part[["aagis_code", "date", "variable", "ow", "silo", "offset_km"]]
            )
        log(f"  {code}: paired {len(merged)} days (offset {cell.dist_km:.1f} km)")

    return pd.concat(out, ignore_index=True)


def _pair_metrics(g: pd.DataFrame) -> pd.Series:
    ow = g["ow"].to_numpy(dtype=float)
    silo = g["silo"].to_numpy(dtype=float)
    diff = ow - silo
    rmse = float(np.sqrt(np.mean(diff**2)))
    bias = float(np.mean(diff))
    if len(g) > 1 and ow.std() > 0 and silo.std() > 0:
        corr = float(np.corrcoef(ow, silo)[0, 1])
    else:
        corr = float("nan")
    return pd.Series(
        {"n": int(len(g)), "rmse": rmse, "bias_ow_minus_silo": bias, "corr": corr}
    )


def compute_metrics(paired: pd.DataFrame) -> pd.DataFrame:
    """Per (centroid, variable) RMSE / bias / correlation."""
    return (
        paired.groupby(["aagis_code", "variable"])
        .apply(_pair_metrics, include_groups=False)
        .reset_index()
    )


def compute_pooled_metrics(paired: pd.DataFrame) -> pd.DataFrame:
    """Metrics pooled over all centroids, per variable."""
    return (
        paired.groupby("variable")
        .apply(_pair_metrics, include_groups=False)
        .reset_index()
    )


__all__ = [
    "OPENWEATHER_DIR",
    "SILO_PROCESSED_DIR",
    "CELL_REGION_MAP_PARQUET",
    "COMPARE_YEARS",
    "CENTROID_CODES",
    "COMPARISONS",
    "OFFSET_WARN_KM",
    "NearestCell",
    "haversine_km",
    "saturation_vapour_pressure_hpa",
    "load_openweather",
    "nearest_cropping_cell",
    "extract_silo_daily",
    "build_comparison",
    "compute_metrics",
    "compute_pooled_metrics",
]
