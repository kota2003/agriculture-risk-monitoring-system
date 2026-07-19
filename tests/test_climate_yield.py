"""Tests for src/processing/climate_yield.py (Phase 03, Step 04)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.paths import DATA_PROCESSED  # noqa: E402
from src.processing.climate_yield import (  # noqa: E402
    EVENTS,
    _corr,
    _detrend,
    build_panel,
    cross_region_cv_corr,
    event_year_summary,
)

DATA_AVAILABLE = (
    DATA_PROCESSED / "silo_region_means" / "annual_1961_2024.csv"
).exists() and (DATA_PROCESSED / "abares" / "wheat.csv").exists()
requires_data = pytest.mark.skipif(
    not DATA_AVAILABLE, reason="climate/yield data not present (run s02/s03)"
)


# --- pure logic ---
def test_detrend_removes_linear_trend():
    years = np.arange(2000, 2030)
    values = 3.0 + 0.2 * (years - 2000)
    assert np.allclose(_detrend(years, values), 0.0, atol=1e-9)


def test_corr_perfect_and_degenerate():
    assert _corr([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert np.isnan(_corr([1, 1, 1, 1], [1, 2, 3, 4]))  # zero variance -> nan
    assert np.isnan(_corr([1, 2], [1, 2]))  # too few points -> nan


def test_events_cover_expected_years():
    assert 2005 in EVENTS["Millennium Drought (2001-2009)"]
    assert 2018 in EVENTS["2018 drought"]


# --- data-backed ---
@requires_data
def test_panel_has_residual_columns():
    p = build_panel("wheat")
    assert {"resid_yield", "resid_rain", "resid_tmax", "rain", "tmax"}.issubset(
        p.columns
    )
    assert len(p) > 300


@requires_data
def test_region_linkage_and_cross_region():
    cv_corr, table = cross_region_cv_corr("wheat")
    assert {"corr_detr_rain_yield", "rain_cv", "yield_detrended_cv"}.issubset(
        table.columns
    )
    assert -1.0 <= cv_corr <= 1.0


@requires_data
def test_drought_years_are_below_trend():
    ev = event_year_summary("wheat").set_index("event")
    non_event = ev.loc["non-event", "mean_resid_yield"]
    # both droughts should sit below the non-event mean detrended yield
    assert ev.loc["Millennium Drought (2001-2009)", "mean_resid_yield"] < non_event
    assert ev.loc["2018 drought", "mean_resid_yield"] < non_event
