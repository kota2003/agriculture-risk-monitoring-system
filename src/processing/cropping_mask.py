"""
Cropping mask construction.

This module builds the broadacre cropping mask used to spatially subset
the SILO grid retrieval (scope v4 sec. 4.1) and to define the spatial
scope of Pillar 1-2 grid-level analyses (scope v4 sec. 3.6.1).

Pipeline:
    Step 1: Convert the ACLUMP 50 m integer raster (EPSG:3577) to a
            binary uint8 raster, 1 = broadacre cropping (ALUM 3.3 codes
            330-338), 0 = other land use, 255 = nodata.

    Step 2: Reproject and resample the binary raster onto the SILO
            0.05 deg lat/lon grid (EPSG:4326) using
            Resampling.average. The resulting float32 array is the
            fraction of broadacre pixels in each SILO cell (0-1).

    Step 3: Apply three thresholds (0.05, 0.10, 0.20) to produce binary
            cropping masks. 0.05 is the project's primary cropping mask;
            0.10 and 0.20 are robustness alternatives for Phase 09
            threshold-sensitivity analysis (cf. scope v4 sec. 5.6.2 MAUP
            robustness study, same methodological precedent).

    Step 4: Persist as a single NetCDF Dataset with all four variables
            plus provenance attributes.

SILO grid spec (Queensland Government, LongPaddock SILO):
    - Longitude: 112 deg E to 154 deg E, cell centres at multiples of 0.05
    - Latitude:  10 deg S to 44 deg S,  cell centres at multiples of 0.05
    - Resolution: 0.05 deg x 0.05 deg (approx 5 km x 5 km)
    - Cell value represents the centre of the cell

    Source:
        https://www.longpaddock.qld.gov.au/silo/faq/
        https://www.longpaddock.qld.gov.au/silo/about/data-products/

    Per the FAQ: "The value at 115.05 deg East, 34.00 deg South is
    intended to be representative of the area 115.025 deg - 115.075 deg
    East, 33.975 deg - 34.025 deg South." Cell centres are therefore at
    integer multiples of 0.05 from the lat/lon origin.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.warp
import xarray as xr
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from tqdm import tqdm

from src.log_utils import log, ok, warn

# ----- SILO grid constants (per longpaddock.qld.gov.au sources above) ---

SILO_LON_MIN_CENTRE = 112.0  # cell centre, western edge
SILO_LON_MAX_CENTRE = 154.0  # cell centre, eastern edge
SILO_LAT_MIN_CENTRE = -44.0  # cell centre, southern edge
SILO_LAT_MAX_CENTRE = -10.0  # cell centre, northern edge
SILO_RESOLUTION = 0.05  # degrees

# Cell counts derived from the spec, inclusive of both edges:
SILO_LON_N_CELLS = (
    int(round((SILO_LON_MAX_CENTRE - SILO_LON_MIN_CENTRE) / SILO_RESOLUTION)) + 1
)  # 841
SILO_LAT_N_CELLS = (
    int(round((SILO_LAT_MAX_CENTRE - SILO_LAT_MIN_CENTRE) / SILO_RESOLUTION)) + 1
)  # 681

# Project's primary cropping threshold + robustness alternatives.
# 0.05 is the project's primary mask; 0.10 and 0.20 are reserved for
# Phase 09 threshold-sensitivity analysis (scope v4 sec. 5.6, robustness).
CROPPING_THRESHOLDS_DEFAULT = (0.05, 0.10, 0.20)
PRIMARY_THRESHOLD = 0.05

# Internal sentinel for the binary intermediate raster:
BINARY_NODATA_UINT8 = 255


# ----- Step 1: binary raster ----------------------------------------------


def build_broadacre_binary_raster(
    src_aclump_tif: Path,
    dst_binary_tif: Path,
    broadacre_codes: tuple[int, ...],
) -> Path:
    """
    Convert the ACLUMP land-use raster to a binary broadacre raster.

    For each ACLUMP pixel, the output is:
        1   if the pixel's ALUM code is in ``broadacre_codes`` (3.3 cropping)
        0   otherwise (non-broadacre land use)
        255 if the source pixel is nodata

    The output GeoTIFF preserves source CRS and transform; only the
    pixel-value semantics change. LZW compression is used because the
    binary content compresses heavily (typically ~10-20x smaller on disk).

    The transformation is windowed: the full ~7 billion pixel ACLUMP
    raster is never held in memory.
    """
    src_aclump_tif = Path(src_aclump_tif)
    dst_binary_tif = Path(dst_binary_tif)
    dst_binary_tif.parent.mkdir(parents=True, exist_ok=True)

    if dst_binary_tif.exists():
        ok(
            f"{dst_binary_tif.name} already exists ({dst_binary_tif.stat().st_size:,} bytes); skip"
        )
        return dst_binary_tif

    broadacre_array = np.asarray(broadacre_codes, dtype=np.int64)
    log(f"Building broadacre binary raster from {src_aclump_tif.name}")
    log(f"  broadacre codes ({len(broadacre_codes)}): {list(broadacre_codes)}")

    with rasterio.open(src_aclump_tif) as src:
        profile = src.profile.copy()
        profile.update(
            dtype="uint8",
            nodata=BINARY_NODATA_UINT8,
            count=1,
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            predictor=2,
        )
        src_nodata = src.nodata
        windows = list(src.block_windows(1))

        with rasterio.open(dst_binary_tif, "w", **profile) as dst:
            for _, window in tqdm(windows, desc="Binary raster", leave=False):
                arr = src.read(1, window=window)
                # Default 0 (non-broadacre); will overwrite broadacre and nodata.
                out = np.zeros_like(arr, dtype=np.uint8)
                is_broadacre = np.isin(arr, broadacre_array)
                out[is_broadacre] = 1
                if src_nodata is not None:
                    out[arr == src_nodata] = BINARY_NODATA_UINT8
                dst.write(out, 1, window=window)

    ok(f"Saved binary raster ({dst_binary_tif.stat().st_size:,} bytes, LZW)")
    return dst_binary_tif


# ----- Step 2: reproject + resample to SILO grid -------------------------


def silo_grid_transform_and_shape() -> tuple[rasterio.Affine, tuple[int, int]]:
    """
    Return the rasterio affine transform and (height, width) of the SILO
    grid in EPSG:4326. The transform encodes the upper-left corner of the
    upper-left cell (note: corner, not centre).
    """
    half = SILO_RESOLUTION / 2
    transform = from_origin(
        west=SILO_LON_MIN_CENTRE - half,
        north=SILO_LAT_MAX_CENTRE + half,
        xsize=SILO_RESOLUTION,
        ysize=SILO_RESOLUTION,
    )
    shape = (SILO_LAT_N_CELLS, SILO_LON_N_CELLS)
    return transform, shape


def silo_grid_coords() -> tuple[np.ndarray, np.ndarray]:
    """Return (lat, lon) coordinate arrays for the SILO grid, cell centres."""
    lats = np.linspace(SILO_LAT_MAX_CENTRE, SILO_LAT_MIN_CENTRE, SILO_LAT_N_CELLS)
    lons = np.linspace(SILO_LON_MIN_CENTRE, SILO_LON_MAX_CENTRE, SILO_LON_N_CELLS)
    return lats, lons


def reproject_to_silo_grid(binary_tif: Path) -> xr.DataArray:
    """
    Reproject + resample the binary broadacre raster to the SILO grid.

    Uses rasterio.warp.reproject with Resampling.average. Because the
    source is 0/1 valued, the average within each destination cell
    equals the fraction of source pixels that are broadacre, i.e. the
    broadacre-cropping fraction in the SILO cell.
    """
    binary_tif = Path(binary_tif)
    dst_transform, dst_shape = silo_grid_transform_and_shape()
    dst_array = np.zeros(dst_shape, dtype=np.float32)

    log(f"Reprojecting to SILO grid (EPSG:4326, {dst_shape[0]}x{dst_shape[1]} cells)")
    with rasterio.open(binary_tif) as src:
        rasterio.warp.reproject(
            source=rasterio.band(src, 1),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=BINARY_NODATA_UINT8,
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            dst_nodata=np.nan,
            resampling=Resampling.average,
        )

    # Replace NaN (no source pixels in dst cell, e.g. over open ocean) with 0:
    # for the cropping mask, "no land here" is meaningfully "no cropping here".
    dst_array = np.where(np.isnan(dst_array), 0.0, dst_array).astype(np.float32)

    lats, lons = silo_grid_coords()
    da = xr.DataArray(
        dst_array,
        dims=("lat", "lon"),
        coords={"lat": lats, "lon": lons},
        name="cropping_fraction",
    )
    da.attrs.update(
        {
            "long_name": "Fraction of SILO cell area classified as ALUM 3.3 Cropping",
            "units": "1",
            "valid_min": 0.0,
            "valid_max": 1.0,
            "source_resolution_metres": 50,
            "source_crs": "EPSG:3577",
            "destination_crs": "EPSG:4326",
            "resampling_method": "average",
        }
    )
    return da


# ----- Step 3: thresholds -------------------------------------------------


def apply_thresholds(
    fraction_da: xr.DataArray,
    thresholds: tuple[float, ...] = CROPPING_THRESHOLDS_DEFAULT,
) -> dict[float, xr.DataArray]:
    """
    Build a {threshold: bool DataArray} dict, one mask per threshold.

    A cell is cropping if its broadacre fraction is at or above the
    threshold. The output dict preserves order for downstream loops.
    """
    out: dict[float, xr.DataArray] = {}
    for t in thresholds:
        mask = (fraction_da >= t).astype(bool)
        mask.attrs.update(
            {
                "long_name": f"Cropping mask at broadacre fraction >= {t}",
                "threshold": t,
                "true_means": "cell classified as cropping",
            }
        )
        out[t] = mask
    return out


# ----- Step 4: assemble NetCDF Dataset ------------------------------------


def threshold_var_name(t: float) -> str:
    """Variable name for a threshold mask, e.g. 0.05 -> 'cropping_mask_t005'."""
    return f"cropping_mask_t{int(round(t * 100)):03d}"


def build_cropping_mask_dataset(
    fraction_da: xr.DataArray,
    masks: dict[float, xr.DataArray],
    primary_threshold: float,
    source_attrs: dict,
) -> xr.Dataset:
    """Assemble a single xr.Dataset with the fraction + each threshold mask."""
    data_vars: dict[str, xr.DataArray] = {"cropping_fraction": fraction_da}
    for t, mask in masks.items():
        data_vars[threshold_var_name(t)] = mask
    ds = xr.Dataset(data_vars)
    ds.attrs.update(source_attrs)
    ds.attrs["primary_mask_variable"] = threshold_var_name(primary_threshold)
    ds.attrs["primary_threshold"] = primary_threshold
    ds.attrs["thresholds"] = ", ".join(str(t) for t in masks.keys())
    ds.attrs["creation_date_utc"] = datetime.now(timezone.utc).isoformat()
    return ds


def save_dataset(ds: xr.Dataset, dst_nc: Path) -> Path:
    """Write the dataset to NetCDF with zlib compression on data variables."""
    dst_nc = Path(dst_nc)
    dst_nc.parent.mkdir(parents=True, exist_ok=True)
    encoding = {var: {"zlib": True, "complevel": 4} for var in ds.data_vars}
    ds.to_netcdf(dst_nc, encoding=encoding)
    return dst_nc


# ----- Sanity check 1: conservation ---------------------------------------


def validate_conservation(
    fraction_da: xr.DataArray,
    expected_aclump_broadacre_pixels: int,
    aclump_pixel_size_metres: float = 50.0,
    tolerance_pct: float = 5.0,
) -> dict:
    """
    Verify the total cropping area is preserved across the reproject step.

    Cropping area is the integral of ``cropping_fraction`` over the SILO
    grid, weighted by each cell's surface area. The expected total is
    the ACLUMP broadacre-pixel count times the source pixel size.

    Because the source raster is in EPSG:3577 (Albers Equal-Area), the
    expected area is exact. The SILO grid is in EPSG:4326 (geographic),
    so cell area varies with latitude; we use the standard spherical
    approximation R*cos(lat)*dlat*dlon.
    """
    R_KM = 6371.0
    deg2rad = np.pi / 180.0
    lat_rad = fraction_da["lat"].values * deg2rad

    # Cell dimensions in km at each lat:
    dlon_km = R_KM * np.cos(lat_rad) * SILO_RESOLUTION * deg2rad
    dlat_km = R_KM * SILO_RESOLUTION * deg2rad
    cell_area_km2 = (dlon_km * dlat_km)[:, np.newaxis]  # (n_lat, 1)

    computed_area_km2 = float((fraction_da.values * cell_area_km2).sum())
    expected_area_km2 = (
        expected_aclump_broadacre_pixels * (aclump_pixel_size_metres**2) / 1.0e6
    )
    rel_diff_pct = (
        100.0 * abs(computed_area_km2 - expected_area_km2) / expected_area_km2
    )
    return {
        "computed_area_km2": computed_area_km2,
        "expected_area_km2": expected_area_km2,
        "relative_diff_pct": rel_diff_pct,
        "tolerance_pct": tolerance_pct,
        "passes": rel_diff_pct <= tolerance_pct,
    }


# ----- Sanity check 2+3: AAGIS regional intersection ----------------------


def validate_aagis_intersection(
    mask_da: xr.DataArray,
    aagis_gpkg_path: Path,
    cropping_zones: tuple[str, ...] = ("Wheat Sheep", "High Rainfall"),
    min_cells_per_region: int = 50,
) -> pd.DataFrame:
    """
    For each cropping AAGIS region, count SILO cells classified as cropping.

    AAGIS zones not in ``cropping_zones`` (e.g. ``Pastoral``) are
    excluded since they are not broadacre-cropping environments
    (scope v4 sec. 3.1).

    Returns a DataFrame with one row per cropping region. The
    ``cells_above_threshold`` column should be at least
    ``min_cells_per_region`` for downstream EVT grid-level fitting in
    Phase 05 to be defensible.
    """
    import geopandas as gpd  # local import to keep optional cost out of module load

    aagis = gpd.read_file(aagis_gpkg_path)
    if str(aagis.crs).upper() != "EPSG:4326":
        aagis = aagis.to_crs("EPSG:4326")

    cropping_aagis = aagis[aagis["zone"].isin(cropping_zones)].copy()
    transform, _ = silo_grid_transform_and_shape()
    mask_2d = mask_da.values.astype(bool)
    shape = mask_2d.shape

    rows = []
    for _, region in cropping_aagis.iterrows():
        try:
            inside = geometry_mask(
                [region.geometry],
                out_shape=shape,
                transform=transform,
                invert=True,  # True inside the geometry
                all_touched=False,
            )
            count = int(np.sum(mask_2d & inside))
        except Exception as e:
            warn(f"Region {region.get('aagis', '?')} clip failed: {e}")
            count = -1
        rows.append(
            {
                "aagis": region.get("aagis", "?"),
                "name": region.get("name", "?"),
                "zone": region["zone"],
                "cells_above_threshold": count,
                "meets_min": count >= min_cells_per_region,
            }
        )

    df = pd.DataFrame(rows).sort_values("cells_above_threshold", ascending=False)
    return df


# ----- Sanity check 4: threshold consistency ------------------------------


def validate_threshold_consistency(masks: dict[float, xr.DataArray]) -> dict:
    """
    Verify that a higher threshold's mask is a strict subset of a lower
    threshold's mask (monotonicity in t).
    """
    sorted_t = sorted(masks.keys())
    results = {}
    for i in range(len(sorted_t) - 1):
        t_lo, t_hi = sorted_t[i], sorted_t[i + 1]
        mask_lo = masks[t_lo].values.astype(bool)
        mask_hi = masks[t_hi].values.astype(bool)
        # Anywhere mask_hi is True but mask_lo is False would violate subset:
        violations = int(np.sum(mask_hi & ~mask_lo))
        results[
            f"t{int(round(t_hi*100)):03d}_subset_of_t{int(round(t_lo*100)):03d}"
        ] = {
            "violations": violations,
            "passes": violations == 0,
        }
    return results
