"""
Tests for src/processing/silo_region_aggregation.py (Phase 02 s04a, Task C).

The weighted-mean core is pure numpy/pandas and always runs. The cell-region
assignment needs geopandas + xarray + the (gitignored) mask/gpkg and skips
otherwise.

Run from repo root:
    python -m pytest tests/test_silo_region_aggregation.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.processing.silo_region_aggregation import (  # noqa: E402
    AAGIS_GPKG,
    CROPPING_MASK_NC,
    SILO_PROCESSED_DIR,
    area_weight_from_lat,
    build_cell_region_map,
    resolve_cell_grid_indices,
    weighted_region_means,
)

try:
    import geopandas  # noqa: F401
    import xarray  # noqa: F401

    _GEO_OK = True
except Exception:  # pragma: no cover - environment dependent
    _GEO_OK = False

_DATA_OK = CROPPING_MASK_NC.exists() and AAGIS_GPKG.exists()
_needs_geo_data = pytest.mark.skipif(
    not (_GEO_OK and _DATA_OK),
    reason="geopandas/xarray or mask/gpkg data not available",
)


# ---------------------------------------------------------------------------
# Pure-logic tests
# ---------------------------------------------------------------------------


def test_area_weight_from_lat():
    w = area_weight_from_lat(np.array([0.0, 60.0, -60.0]))
    assert w[0] == pytest.approx(1.0)
    assert w[1] == pytest.approx(0.5, abs=1e-9)
    assert w[2] == pytest.approx(0.5, abs=1e-9)  # symmetric in |lat|


def test_weighted_region_means_basic():
    result = weighted_region_means(
        values=np.array([10.0, 20.0, 5.0]),
        aagis_code=np.array(["121", "121", "521"]),
        region_name=np.array(["A", "A", "B"]),
        weights=np.array([1.0, 3.0, 2.0]),
    ).set_index("aagis_code")

    assert result.loc["121", "value"] == pytest.approx(17.5)  # (10*1+20*3)/4
    assert int(result.loc["121", "n_cells"]) == 2
    assert result.loc["521", "value"] == pytest.approx(5.0)
    assert int(result.loc["521", "n_cells"]) == 1


def test_weighted_region_means_drops_nan_values():
    result = weighted_region_means(
        values=np.array([10.0, np.nan, 5.0]),
        aagis_code=np.array(["121", "121", "521"]),
        region_name=np.array(["A", "A", "B"]),
        weights=np.array([1.0, 3.0, 2.0]),
    ).set_index("aagis_code")

    assert result.loc["121", "value"] == pytest.approx(10.0)  # nan cell dropped
    assert int(result.loc["121", "n_cells"]) == 1


def test_weighted_region_means_zero_weight_is_nan():
    result = weighted_region_means(
        values=np.array([10.0, 20.0]),
        aagis_code=np.array(["121", "121"]),
        region_name=np.array(["A", "A"]),
        weights=np.array([0.0, 0.0]),
    ).set_index("aagis_code")

    assert np.isnan(result.loc["121", "value"])
    assert int(result.loc["121", "n_cells"]) == 2


def test_resolve_cell_grid_indices_matches_coordinate_values():
    """Indices must follow coordinate VALUES, robust to axis ordering.

    This is the regression guard for the s04a latitude-flip bug: reusing the
    mask's row order sampled the wrong (flipped) latitude.
    """
    cell = pd.DataFrame({"lat": [-43.0, -41.0], "lon": [120.0, 121.0]})
    asc_lat = np.array([-44.0, -43.0, -42.0, -41.0, -40.0])  # ascending (SILO)
    desc_lat = asc_lat[::-1]  # descending (mask-like)
    lon = np.array([120.0, 121.0, 122.0])

    r_asc, c = resolve_cell_grid_indices(cell, asc_lat, lon)
    r_desc, _ = resolve_cell_grid_indices(cell, desc_lat, lon)

    assert list(r_asc) == [1, 3]  # -43 -> idx1, -41 -> idx3 (ascending)
    assert list(r_desc) == [3, 1]  # opposite ordering -> opposite indices
    # Either way, the resolved latitude equals the requested one.
    assert asc_lat[r_asc[0]] == -43.0
    assert desc_lat[r_desc[0]] == -43.0
    assert list(c) == [0, 1]


# ---------------------------------------------------------------------------
# Data-backed test (cell-region assignment)
# ---------------------------------------------------------------------------


@_needs_geo_data
def test_cell_region_map_coverage():
    cell_df = build_cell_region_map()

    # Columns and integer grid indices.
    for col in ("row", "col", "lat", "lon", "weight", "aagis_code", "region_name"):
        assert col in cell_df.columns
    assert (cell_df["weight"] > 0).all()

    # Assigned cells cannot exceed the 28,721 t005 cropping cells.
    assert 0 < len(cell_df) <= 28721

    # Cropping is concentrated in broadacre regions -> many regions covered.
    assert cell_df["aagis_code"].nunique() >= 15


@_needs_geo_data
def test_grid_indices_align_with_silo_and_tas_has_data():
    """Resolved indices must sample the correct latitude, and the broadacre
    TAS region must carry data (regression guard for the s04a lat-flip bug,
    where TAS cells landed on tropical ocean -> all NaN)."""
    import xarray as xr

    silo_file = SILO_PROCESSED_DIR / "max_temp" / "2020.max_temp.nc"
    if not silo_file.exists():
        pytest.skip("SILO max_temp 2020 file not present")

    cell_df = build_cell_region_map()
    ds = xr.open_dataset(silo_file)
    da = ds["max_temp"]
    rows, cols = resolve_cell_grid_indices(cell_df, da["lat"].values, da["lon"].values)

    # The resolved grid coordinate must equal the cell's stored coordinate.
    assert np.abs(da["lat"].values[rows] - cell_df["lat"].values).max() < 1e-6
    assert np.abs(da["lon"].values[cols] - cell_df["lon"].values).max() < 1e-6

    # Tasmania (631, High-Rainfall broadacre) must have finite temperature.
    field = da.mean("time").values
    is_tas = cell_df["aagis_code"].astype(str).to_numpy() == "631"
    if is_tas.any():
        tas_vals = field[rows[is_tas], cols[is_tas]]
        assert np.isfinite(tas_vals).any(), "TAS cells sample NaN -> lat-flip bug"

    ds.close()
