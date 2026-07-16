"""
Regression tests for the SILO cropping-mask alignment (Phase 02 s04a fix of a
Phase 01 s04 bug).

The Phase 01 masking substituted mask coordinates positionally
(``assign_coords``); because the mask is latitude-descending and the SILO data
latitude-ascending, this flipped the mask north-south and masked out the true
cropping cells. ``_assert_masking_sane`` guards against any recurrence. These
tests use tiny synthetic grids and need only xarray/numpy.

Run from repo root:
    python -m pytest tests/test_silo_masking.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

xr = pytest.importorskip("xarray")

from src.ingestion.silo import _assert_masking_sane  # noqa: E402


def _mask(lat: np.ndarray, lon: np.ndarray, true_rows) -> "xr.DataArray":
    arr = np.zeros((lat.size, lon.size), dtype=bool)
    arr[list(true_rows), :] = True
    return xr.DataArray(arr, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])


def test_reindex_alignment_preserves_cropping_location():
    """Coordinate-value reindex keeps cropping cells at their true latitudes."""
    lat_desc = np.arange(-10.0, -20.5, -1.0)  # mask order: descending
    lon = np.array([140.0, 141.0, 142.0])
    # cropping concentrated in the far south (lat -18, -19, -20)
    mask_da = _mask(lat_desc, lon, true_rows=[8, 9, 10])

    lat_asc = lat_desc[::-1]  # SILO data order: ascending
    aligned = (
        mask_da.reindex(lat=lat_asc, lon=lon, method="nearest", tolerance=0.025)
        .fillna(False)
        .astype(bool)
    )

    # Guard passes, and the True cells really are at the southern latitudes.
    _assert_masking_sane(mask_da, aligned)
    true_lats = sorted(
        float(v) for v in aligned["lat"].values[aligned.any("lon").values]
    )
    assert true_lats == [-20.0, -19.0, -18.0]


def test_guard_rejects_positional_flip():
    """The old positional assign_coords (north-south flip) must be rejected."""
    lat_desc = np.arange(-10.0, -20.5, -1.0)
    lon = np.array([140.0, 141.0, 142.0])
    mask_da = _mask(lat_desc, lon, true_rows=[8, 9, 10])

    lat_asc = lat_desc[::-1]
    flipped = mask_da.copy().assign_coords(lat=lat_asc, lon=lon)  # the Phase 01 bug

    with pytest.raises(RuntimeError, match="flip|centroid"):
        _assert_masking_sane(mask_da, flipped)
