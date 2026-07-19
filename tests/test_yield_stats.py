"""Tests for src/processing/yield_stats.py (Phase 03, Step 03)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.paths import DATA_PROCESSED  # noqa: E402
from src.processing.yield_stats import (  # noqa: E402
    COMMODITIES,
    MIN_YEARS,
    RELIABLE_YIELD_START,
    detrended_cv,
    load_yield,
    ols_slope_per_decade,
    region_yield_summary,
)

DATA_AVAILABLE = (DATA_PROCESSED / "abares" / "wheat.csv").exists()
requires_data = pytest.mark.skipif(not DATA_AVAILABLE, reason="ABARES data not present")


# --- pure logic ---
def test_ols_slope_per_decade_known():
    years = np.arange(2000, 2020)
    values = 1.0 + 0.05 * (years - 2000)  # +0.05 t/ha per year = +0.5 per decade
    assert ols_slope_per_decade(years, values) == pytest.approx(0.5, abs=1e-9)


def test_ols_slope_too_few_points_is_nan():
    assert np.isnan(ols_slope_per_decade([2000, 2001], [1.0, 2.0]))


def test_detrended_cv_removes_trend():
    years = np.arange(2000, 2030)
    trend = 2.0 + 0.1 * (years - 2000)  # pure trend, no noise
    # residuals are ~0 -> detrended CV ~0 even though raw CV is large
    assert detrended_cv(years, trend) == pytest.approx(0.0, abs=1e-9)


def test_reliable_start_constants():
    assert RELIABLE_YIELD_START == {"wheat": 1990, "barley": 1990, "canola": 1994}


# --- data-backed ---
@requires_data
def test_canola_window_excludes_pre_1994():
    assert int(load_yield("canola").year.min()) >= 1994
    assert int(load_yield("wheat").year.min()) >= 1990


@requires_data
def test_summary_columns_and_ranges():
    s = region_yield_summary()
    expected = {
        "commodity",
        "region",
        "n_years",
        "mean_yield",
        "median_yield",
        "trend_t_ha_decade",
        "cv",
        "detrended_cv",
        "p10_yield",
        "p10_over_median",
        "worst_over_median",
        "median_prod_rse",
        "adequate",
    }
    assert expected.issubset(s.columns)
    assert set(s.commodity.unique()) == set(COMMODITIES)
    adq = s[s.adequate]
    assert (adq.n_years >= MIN_YEARS).all()
    assert adq.mean_yield.between(0, 8).all()
    assert adq.detrended_cv.between(0, 2).all()


@requires_data
def test_wheat_has_broadacre_coverage():
    s = region_yield_summary("wheat")
    # every adequate wheat region is one of the 20 broadacre regions
    assert s[s.adequate].shape[0] >= 15
