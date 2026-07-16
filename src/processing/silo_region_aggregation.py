"""
src/processing/silo_region_aggregation.py — SILO grid -> AAGIS region means.

Phase 02, Step 04a (Task C, part 1). Aggregates the cropping-masked SILO
gridded climate data to AAGIS-region means, so that the grid-vs-region
aggregation consistency check (s04b) can confirm that area-weighted region
climatologies are sane (scope v5 §4.2, §6.2; phase01_summary §4.2).

Design (agreed at s04a kickoff):
  1. Cell -> region assignment. The processed SILO files are already masked
     to the t005 broadacre cropping cells (Phase 01 s04). Each active cell
     centroid is spatially joined (point-in-polygon) to the AAGIS region
     polygons once and cached (`data/processed/silo_cell_region_map.parquet`).
  2. Area weighting. On a 0.05° lat/lon grid, cell ground area is
     proportional to cos(latitude); the region mean is the cos(lat)-weighted
     mean over the region's active cells.
  3. Memory-efficient single-pass aggregation. Each annual NetCDF is opened
     once; the annual reduction (mean for state variables, sum for rainfall)
     and the twelve monthly reductions are computed and the active cells
     sampled immediately, so the full daily cube is never carried across
     cells.

Grid-alignment note (s04a bug, fixed):
  The cropping mask (cropping_mask.nc) stores latitude DESCENDING while the
  SILO data files store it ASCENDING. Sampling a SILO field by the mask's own
  row index therefore reads the latitude-flipped cell (e.g. Tasmania cells
  landed on tropical ocean -> NaN; WA wheat-belt cells landed on the arid
  Pilbara -> plausible-looking but wrong). Grid indices are now resolved by
  matching coordinate VALUES against each SILO file's own lat/lon axes
  (`resolve_cell_grid_indices`), which is robust to axis ordering.

Grid facts (verified against src/processing/cropping_mask.py, src/ingestion/
silo.py, and the SILO files themselves):
  - SILO grid: 0.05°, lat 681 (ascending -44..-10) × lon 841 (112..154),
    EPSG:4326; internal variable name equals the canonical name (e.g.
    `max_temp`); coords `lat`, `lon`, `time`.
  - Cropping mask: `data/processed/cropping_mask.nc`, var `cropping_mask_t005`
    (28,721 True cells), same grid but latitude DESCENDING.
  - AAGIS polygons: `data/processed/aagis_regions_repaired.gpkg`, EPSG:4283
    (GDA94; ~sub-metre from WGS84 over Australia), 32 regions.

The heavy per-year I/O is intended to run on the user's machine; the
weighted-mean core (`weighted_region_means`) is pure numpy/pandas and unit
tested independently of any data.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.log_utils import log, ok, warn
from src.paths import DATA_PROCESSED

# ---------------------------------------------------------------------------
# Locations & constants
# ---------------------------------------------------------------------------

SILO_PROCESSED_DIR: Path = DATA_PROCESSED / "silo"
CROPPING_MASK_NC: Path = DATA_PROCESSED / "cropping_mask.nc"
AAGIS_GPKG: Path = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
CELL_REGION_MAP_PARQUET: Path = DATA_PROCESSED / "silo_cell_region_map.parquet"
REGION_MEANS_DIR: Path = DATA_PROCESSED / "silo_region_means"

CROPPING_MASK_VAR: str = "cropping_mask_t005"

SILO_VARIABLES: tuple[str, ...] = (
    "max_temp",
    "min_temp",
    "daily_rain",
    "vp",
    "radiation",
    "evap_pan",
)

# Temporal reduction rule per variable: rainfall accumulates (sum), state
# variables average (mean). Units after annual reduction:
#   max_temp/min_temp degC, daily_rain mm/yr (annual total), vp hPa,
#   radiation MJ/m^2/day (mean), evap_pan mm/day (mean).
AGG_RULE: dict[str, str] = {
    "max_temp": "mean",
    "min_temp": "mean",
    "daily_rain": "sum",
    "vp": "mean",
    "radiation": "mean",
    "evap_pan": "mean",
}

# Standard WMO climate-normal reference period used for the consistency check.
REFERENCE_PERIOD: tuple[int, int] = (1991, 2020)

# evap_pan is observed only from 1970 (Phase 01 finding #6); the reference
# period (1991-2020) is safely inside that window for every variable.


# ---------------------------------------------------------------------------
# Weighted-mean core (pure numpy/pandas; unit tested without data)
# ---------------------------------------------------------------------------


def area_weight_from_lat(lat: np.ndarray) -> np.ndarray:
    """
    Return cos(latitude) area weights for a lat/lon grid.

    Cell ground area on a regular lat/lon grid is proportional to the cosine
    of latitude; longitude spacing in metres shrinks towards the poles.
    """
    return np.cos(np.deg2rad(np.asarray(lat, dtype=float)))


def weighted_region_means(
    values: np.ndarray,
    aagis_code: np.ndarray,
    region_name: np.ndarray,
    weights: np.ndarray,
) -> pd.DataFrame:
    """
    Compute cos(lat)-weighted means grouped by region for a single field.

    NaN values are dropped before weighting (they carry no weight). Regions
    whose weights sum to zero return NaN.

    Parameters
    ----------
    values : np.ndarray
        1-D array of cell values (one time/level slice), aligned to the cell
        order of the cell-region map. May contain NaN.
    aagis_code, region_name, weights : np.ndarray
        1-D arrays aligned to ``values``.

    Returns
    -------
    pandas.DataFrame
        Columns ``aagis_code``, ``region_name``, ``value``, ``n_cells``.
    """
    df = pd.DataFrame(
        {
            "aagis_code": np.asarray(aagis_code),
            "region_name": np.asarray(region_name),
            "v": np.asarray(values, dtype=float),
            "w": np.asarray(weights, dtype=float),
        }
    ).dropna(subset=["v"])

    def _agg(group: pd.DataFrame) -> pd.Series:
        wsum = group["w"].sum()
        value = np.average(group["v"], weights=group["w"]) if wsum > 0 else np.nan
        return pd.Series({"value": value, "n_cells": int(len(group))})

    out = (
        df.groupby(["aagis_code", "region_name"], sort=True)
        .apply(_agg, include_groups=False)
        .reset_index()
    )
    return out


# ---------------------------------------------------------------------------
# Cell -> region assignment
# ---------------------------------------------------------------------------


def build_cell_region_map(
    mask_nc: str | Path = CROPPING_MASK_NC,
    aagis_gpkg: str | Path = AAGIS_GPKG,
    mask_var: str = CROPPING_MASK_VAR,
) -> pd.DataFrame:
    """
    Assign each active (cropping) SILO cell to an AAGIS region.

    Reads the boolean cropping mask, takes the True cells, builds their
    centroids, and spatially joins (point within polygon) to the AAGIS
    regions. Cells falling outside every region (e.g. near-coast) are
    reported and excluded.

    Returns
    -------
    pandas.DataFrame
        Columns: ``row``, ``col`` (indices into the MASK grid — retained for
        reference only; SILO sampling resolves indices from coordinate values,
        see :func:`resolve_cell_grid_indices`), ``lat``, ``lon``, ``weight``
        (cos lat), ``aagis_code``, ``region_name``.
    """
    import geopandas as gpd
    import xarray as xr

    mask_nc = Path(mask_nc)
    if not mask_nc.exists():
        raise FileNotFoundError(f"Cropping mask not found: {mask_nc}")

    ds = xr.open_dataset(mask_nc)
    if mask_var not in ds.data_vars:
        raise KeyError(f"'{mask_var}' not in {mask_nc}; have {list(ds.data_vars)}")
    mask = ds[mask_var].astype(bool)
    lat = mask["lat"].values
    lon = mask["lon"].values
    mask_arr = mask.values  # (nlat, nlon)
    ds.close()

    rows, cols = np.where(mask_arr)
    cell_lat = lat[rows]
    cell_lon = lon[cols]
    log(f"  {len(rows):,} active cropping cells in {Path(mask_nc).name}")

    points = gpd.GeoDataFrame(
        {
            "row": rows,
            "col": cols,
            "lat": cell_lat,
            "lon": cell_lon,
        },
        geometry=gpd.points_from_xy(cell_lon, cell_lat),
        crs="EPSG:4326",
    )

    regions = gpd.read_file(aagis_gpkg)
    if regions.crs is None:
        raise RuntimeError(f"AAGIS gpkg has no CRS: {aagis_gpkg}")
    if regions.crs.to_epsg() != 4326:
        regions = regions.to_crs(epsg=4326)
    regions = regions[["class", "name", "geometry"]].rename(
        columns={"class": "aagis_code", "name": "region_name"}
    )
    regions["aagis_code"] = regions["aagis_code"].astype(str).str.strip()
    regions["region_name"] = regions["region_name"].astype(str).str.strip()

    joined = gpd.sjoin(points, regions, how="left", predicate="within")

    n_unassigned = int(joined["aagis_code"].isna().sum())
    if n_unassigned:
        warn(
            f"  {n_unassigned:,} active cells fall outside all AAGIS regions "
            f"(excluded; typically near-coast cropping cells)"
        )
    joined = joined.dropna(subset=["aagis_code"]).copy()
    joined["weight"] = area_weight_from_lat(joined["lat"].values)

    out = joined[
        ["row", "col", "lat", "lon", "weight", "aagis_code", "region_name"]
    ].reset_index(drop=True)
    out["row"] = out["row"].astype(int)
    out["col"] = out["col"].astype(int)
    ok(
        f"  assigned {len(out):,} cells to {out['aagis_code'].nunique()} "
        f"AAGIS regions"
    )
    return out


def save_cell_region_map(
    cell_df: pd.DataFrame, path: str | Path = CELL_REGION_MAP_PARQUET
) -> Path:
    """Persist the cell-region map (atomic .part -> rename)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    cell_df.to_parquet(tmp, index=False)
    tmp.replace(path)
    ok(f"  wrote cell-region map ({len(cell_df):,} cells) -> {path}")
    return path


def load_cell_region_map(
    path: str | Path = CELL_REGION_MAP_PARQUET,
) -> pd.DataFrame:
    """Load a previously cached cell-region map."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Cell-region map not found: {path}. Run build_cell_region_map first."
        )
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Aggregation (xarray for I/O + time reduction; numpy/pandas for weighting)
# ---------------------------------------------------------------------------


def _open_variable_year(variable: str, year: int, processed_dir: Path):
    import xarray as xr

    path = Path(processed_dir) / variable / f"{year}.{variable}.nc"
    if not path.exists():
        raise FileNotFoundError(f"SILO processed file not found: {path}")
    ds = xr.open_dataset(path)
    da = ds[variable] if variable in ds.data_vars else ds[list(ds.data_vars)[0]]
    return ds, da


def resolve_cell_grid_indices(
    cell_df: pd.DataFrame,
    file_lat: np.ndarray,
    file_lon: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Map each cell's (lat, lon) to (row, col) indices of a SILO data file.

    Indices are resolved by matching coordinate VALUES against the SILO
    file's own lat/lon axes, NOT by reusing the cropping-mask's array order.
    This is essential because the mask stores latitude descending while the
    SILO files store it ascending; reusing the mask's row index would sample
    the latitude-flipped cell (the s04a bug this replaces).

    Raises
    ------
    ValueError
        If any cell coordinate cannot be matched to the grid.
    """
    lat_to_row = {round(float(v), 4): i for i, v in enumerate(np.asarray(file_lat))}
    lon_to_col = {round(float(v), 4): i for i, v in enumerate(np.asarray(file_lon))}
    rows = cell_df["lat"].round(4).map(lat_to_row)
    cols = cell_df["lon"].round(4).map(lon_to_col)
    if rows.isna().any() or cols.isna().any():
        n = int(rows.isna().sum() + cols.isna().sum())
        raise ValueError(f"{n} cell coordinate(s) not found in the SILO grid")
    return rows.astype(int).to_numpy(), cols.astype(int).to_numpy()


def aggregate_region_climatologies(
    variables,
    years,
    cell_df: pd.DataFrame,
    processed_dir: str | Path = SILO_PROCESSED_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Single-pass region aggregation: annual series + monthly climatology.

    Each (variable, year) file is opened once; the annual reduction and the
    twelve monthly reductions are computed and the active cells sampled
    immediately. Rainfall uses ``min_count=1`` so no-data cells stay NaN
    instead of collapsing to 0.

    Returns
    -------
    (annual_df, monthly_df)
        annual_df columns: ``aagis_code, region_name, year, variable, value,
        n_cells``. monthly_df columns: ``aagis_code, region_name, month,
        variable, value, n_cells`` (climatology averaged over ``years``).
    """
    processed_dir = Path(processed_dir)
    codes = cell_df["aagis_code"].to_numpy()
    names = cell_df["region_name"].to_numpy()
    weights = cell_df["weight"].to_numpy()

    annual_frames: list[pd.DataFrame] = []
    # variable -> month -> list of (n_active,) sampled fields, one per year
    monthly_samples: dict[str, dict[int, list[np.ndarray]]] = {v: {} for v in variables}

    grid_idx: tuple[np.ndarray, np.ndarray] | None = None

    for variable in variables:
        rule = AGG_RULE[variable]
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
            means = weighted_region_means(annual_vals, codes, names, weights)
            means["year"] = int(year)
            means["variable"] = variable
            annual_frames.append(means)

            monthly = (
                da.resample(time="1MS").sum(min_count=1)
                if rule == "sum"
                else da.resample(time="1MS").mean()
            )
            months = monthly["time"].dt.month.values
            marr = np.asarray(monthly.values, dtype=float)  # (12, nlat, nlon)
            ds.close()
            for i, mo in enumerate(months):
                monthly_samples[variable].setdefault(int(mo), []).append(
                    marr[i][rows, cols]
                )
            log(f"  {variable} {year}: annual + monthly reduced")

    monthly_frames: list[pd.DataFrame] = []
    for variable in variables:
        for mo in sorted(monthly_samples[variable]):
            stack = np.vstack(monthly_samples[variable][mo])  # (n_years, n_active)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                clim = np.nanmean(stack, axis=0)  # (n_active,)
            means = weighted_region_means(clim, codes, names, weights)
            means["month"] = int(mo)
            means["variable"] = variable
            monthly_frames.append(means)

    annual_df = pd.concat(annual_frames, ignore_index=True)
    monthly_df = pd.concat(monthly_frames, ignore_index=True)
    return annual_df, monthly_df


def write_region_means(
    df: pd.DataFrame, name: str, out_dir: str | Path = REGION_MEANS_DIR
) -> Path:
    """Persist a region-means table (atomic .part -> rename)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.csv"
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out_path)
    ok(f"  wrote {len(df):,} rows -> {out_path}")
    return out_path


__all__ = [
    "SILO_PROCESSED_DIR",
    "CROPPING_MASK_NC",
    "AAGIS_GPKG",
    "CELL_REGION_MAP_PARQUET",
    "REGION_MEANS_DIR",
    "CROPPING_MASK_VAR",
    "SILO_VARIABLES",
    "AGG_RULE",
    "REFERENCE_PERIOD",
    "area_weight_from_lat",
    "weighted_region_means",
    "build_cell_region_map",
    "save_cell_region_map",
    "load_cell_region_map",
    "resolve_cell_grid_indices",
    "aggregate_region_climatologies",
    "write_region_means",
]
