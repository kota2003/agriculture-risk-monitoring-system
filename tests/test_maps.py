"""Smoke tests for src/viz/maps.py (Phase 03, Step 02)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.viz.maps import (  # noqa: E402
    AAGIS_GPKG,
    BROADACRE_ZONES,
    load_region_geometries,
    region_choropleth,
)

requires_gpkg = pytest.mark.skipif(
    not AAGIS_GPKG.exists(), reason="AAGIS gpkg not present"
)


def test_broadacre_zones_constant():
    assert set(BROADACRE_ZONES) == {"Wheat Sheep", "High Rainfall"}


@requires_gpkg
def test_load_region_geometries():
    g = load_region_geometries()
    assert len(g) == 32
    assert {"aagis_code", "region_name", "zone", "geometry"}.issubset(g.columns)


@requires_gpkg
def test_choropleth_runs_sequential_and_diverging():
    g = load_region_geometries()
    vals = pd.DataFrame({"aagis_code": g["aagis_code"], "v": range(len(g))})
    ax = region_choropleth(vals, "v", cmap="cividis", label="x", vmax_cap=20)
    assert ax is not None and len(ax.collections) >= 1

    signed = pd.DataFrame(
        {"aagis_code": g["aagis_code"], "d": [i - 15 for i in range(len(g))]}
    )
    ax2 = region_choropleth(signed, "d", cmap="RdBu_r", label="Δ", diverging=True)
    assert ax2 is not None and len(ax2.collections) >= 1
