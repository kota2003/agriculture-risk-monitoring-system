"""
Tests for src/processing/climate_consistency.py (Phase 02 s04b, Task C part 2).

Pure-logic tests always run. The data-backed test exercises the real s04a
outputs and skips if they are absent.

Run from repo root:
    python -m pytest tests/test_climate_consistency.py -v
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

from src.processing.climate_consistency import (  # noqa: E402
    ANNUAL_CSV,
    CELL_REGION_MAP_PARQUET,
    MONTHLY_CSV,
    TMAX_LAT_CORR_MIN,
    check_internal_consistency,
    compare_to_reference,
    load_region_annual,
    load_region_latitude,
    load_seasonality,
)

_SVARS = ["max_temp", "min_temp", "daily_rain", "vp", "radiation", "evap_pan"]


def _synthetic():
    codes = ["521", "421", "322", "121"]
    lat = pd.Series(
        {"521": -31.0, "421": -33.0, "322": -27.0, "121": -29.0}, name="lat"
    )
    # tmax/tmin increase with latitude (toward the equator) -> strong +corr.
    region_annual = pd.DataFrame(
        {
            "max_temp": {c: 50.0 + lat[c] for c in codes},
            "min_temp": {c: 32.0 + lat[c] for c in codes},
            "daily_rain": {c: 400.0 for c in codes},
            "vp": {c: 14.0 for c in codes},
            "radiation": {c: 18.0 for c in codes},
            "evap_pan": {c: 5.0 for c in codes},
        }
    )
    region_annual.index.name = "aagis_code"
    seasonality = pd.DataFrame(
        {
            "winter_share": {"521": 55.0, "421": 50.0, "322": 19.0, "121": 25.0},
            "summer_share": {"521": 20.0, "421": 22.0, "322": 54.0, "121": 47.0},
        }
    )
    zone = pd.Series({c: "Wheat Sheep" for c in codes}, name="zone")
    return region_annual, seasonality, lat, zone


def test_internal_consistency_passes_on_clean_synthetic():
    region_annual, seasonality, lat, zone = _synthetic()
    report = check_internal_consistency(region_annual, seasonality, lat, zone)
    assert report["valid"] is True
    assert report["checks"]["tmax_latitude_corr"] is True
    assert report["checks"]["rainfall_seasonality_regime"] is True
    assert report["tmax_lat_corr"] >= TMAX_LAT_CORR_MIN


def test_internal_consistency_flags_broken_temperature_gradient():
    region_annual, seasonality, lat, zone = _synthetic()
    region_annual["max_temp"] = 25.0  # constant -> no latitude correlation
    report = check_internal_consistency(region_annual, seasonality, lat, zone)
    assert report["checks"]["tmax_latitude_corr"] is False
    assert report["valid"] is False


def test_internal_consistency_flags_wrong_seasonality():
    region_annual, seasonality, lat, zone = _synthetic()
    # Make a winter-dominant region look summer-dominant.
    seasonality.loc["521", "winter_share"] = 15.0
    seasonality.loc["521", "summer_share"] = 60.0
    report = check_internal_consistency(region_annual, seasonality, lat, zone)
    assert report["checks"]["rainfall_seasonality_regime"] is False
    assert "521" in report["winter_regime_failures"]


def test_compare_to_reference_matches_close_values():
    region_annual = pd.DataFrame(
        {
            "max_temp": {"221": 23.8},
            "min_temp": {"221": 10.5},
            "daily_rain": {"221": 300.0},
        }
    )
    region_annual.index.name = "aagis_code"
    out = compare_to_reference(region_annual)
    row = out[out["aagis_code"] == "221"].iloc[0]
    assert bool(row["tmax_within_3C"]) is True
    assert bool(row["rain_within_45pct"]) is True


# ---------------------------------------------------------------------------
# Data-backed
# ---------------------------------------------------------------------------

_DATA_OK = (
    ANNUAL_CSV.exists() and MONTHLY_CSV.exists() and CELL_REGION_MAP_PARQUET.exists()
)


@pytest.mark.skipif(not _DATA_OK, reason="s04a region-mean outputs not present")
def test_internal_consistency_on_real_outputs():
    from src.processing.region_aggregation import load_region_mapping

    region_annual = load_region_annual()
    seasonality = load_seasonality()
    region_lat = load_region_latitude()
    zone = load_region_mapping().set_index("aagis_code")["zone"]

    report = check_internal_consistency(region_annual, seasonality, region_lat, zone)
    assert report["valid"] is True, report
    assert report["tmax_lat_corr"] >= TMAX_LAT_CORR_MIN
    assert np.isfinite(report["tmin_lat_corr"])
