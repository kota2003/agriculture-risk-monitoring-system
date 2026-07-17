"""
Tests for src/processing/openweather_silo_compare.py (Phase 02 s06, Task D).

Pure-logic tests always run. The data-backed test needs pyarrow + xarray and
the OpenWeather / SILO / cell-map data; it skips otherwise.

Run from repo root:
    python -m pytest tests/test_openweather_silo_compare.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.processing.openweather_silo_compare import (  # noqa: E402
    CELL_REGION_MAP_PARQUET,
    CENTROID_CODES,
    OPENWEATHER_DIR,
    compute_metrics,
    compute_pooled_metrics,
    haversine_km,
    nearest_cropping_cell,
    saturation_vapour_pressure_hpa,
)


# ---------------------------------------------------------------------------
# Pure-logic tests
# ---------------------------------------------------------------------------


def test_saturation_vapour_pressure_tetens():
    assert float(saturation_vapour_pressure_hpa(0.0)) == pytest.approx(6.108, abs=1e-3)
    # Tetens at 20 degC ~ 23.4 hPa
    assert float(saturation_vapour_pressure_hpa(20.0)) == pytest.approx(23.4, abs=0.2)


def test_haversine_one_degree_latitude():
    # 1 degree of latitude is ~111 km.
    assert float(haversine_km(0.0, 0.0, 1.0, 0.0)) == pytest.approx(111.2, abs=1.0)


def test_nearest_cropping_cell_picks_closest():
    cell_map = pd.DataFrame(
        {"lat": [-31.0, -34.0, -20.0], "lon": [117.0, 140.0, 130.0]}
    )
    nc = nearest_cropping_cell(-31.1, 117.05, cell_map)
    assert nc.lat == -31.0 and nc.lon == 117.0
    assert nc.dist_km < 15.0


def _paired(ow, silo, variable="tmax", code="121"):
    n = len(ow)
    return pd.DataFrame(
        {
            "aagis_code": [code] * n,
            "date": pd.date_range("2022-01-01", periods=n, freq="D"),
            "variable": [variable] * n,
            "ow": ow,
            "silo": silo,
            "offset_km": [5.0] * n,
        }
    )


def test_compute_metrics_bias_rmse_corr():
    paired = _paired([2.0, 3.0, 4.0], [1.0, 2.0, 3.0])  # OW = SILO + 1
    m = compute_metrics(paired)
    row = m.iloc[0]
    assert int(row["n"]) == 3
    assert row["bias_ow_minus_silo"] == pytest.approx(1.0)
    assert row["rmse"] == pytest.approx(1.0)
    assert row["corr"] == pytest.approx(1.0)


def test_compute_pooled_metrics_perfect_match():
    paired = _paired([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    pooled = compute_pooled_metrics(paired)
    row = pooled[pooled["variable"] == "tmax"].iloc[0]
    assert row["rmse"] == pytest.approx(0.0)
    assert row["bias_ow_minus_silo"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Data-backed test
# ---------------------------------------------------------------------------

try:
    import pyarrow  # noqa: F401
    import xarray  # noqa: F401

    _ENGINE_OK = True
except Exception:  # pragma: no cover
    _ENGINE_OK = False

_OW_OK = (OPENWEATHER_DIR / f"{CENTROID_CODES[0]}_2022.parquet").exists()
_DATA_OK = _ENGINE_OK and _OW_OK and CELL_REGION_MAP_PARQUET.exists()


@pytest.mark.skipif(not _DATA_OK, reason="pyarrow/xarray or OW/SILO data absent")
def test_tmax_agreement_is_strong_on_real_data():
    from src.processing.openweather_silo_compare import build_comparison

    paired = build_comparison(codes=(CENTROID_CODES[0],))
    pooled = compute_pooled_metrics(paired)
    tmax = pooled[pooled["variable"] == "tmax"].iloc[0]
    # OpenWeather and SILO tmax should track closely at a broadacre centroid.
    assert tmax["corr"] > 0.9
    assert abs(tmax["bias_ow_minus_silo"]) < 5.0
