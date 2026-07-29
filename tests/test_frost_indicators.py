"""Tests for src/indicators/frost — frost-day growing-season counter.

All external I/O is patched: load_silo_year is replaced with synthetic
tmin grids so no real SILO data are required.

Synthetic grid: 3 lat × 4 lon, values controlled per test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.indicators._base import GROWING_WINDOWS

# ---------------------------------------------------------------------------
# Grid / time helpers
# ---------------------------------------------------------------------------

LAT = np.array([-32.0, -33.0, -34.0])
LON = np.array([148.0, 149.0, 150.0, 151.0])
NLAT, NLON = len(LAT), len(LON)


def _make_tmin_da(year: int, fill_value: float) -> xr.DataArray:
    """Return a constant-fill tmin DataArray for the given year."""
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    data = np.full((len(dates), NLAT, NLON), fill_value, dtype=float)
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": dates, "lat": LAT, "lon": LON},
        attrs={"units": "°C", "long_name": "min_temp"},
    )


def _make_tmin_da_from_array(year: int, daily_values: np.ndarray) -> xr.DataArray:
    """Return a tmin DataArray with spatially-uniform daily values.

    daily_values: 1-D array of length n_days.
    """
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    assert len(daily_values) == len(
        dates
    ), f"daily_values length {len(daily_values)} ≠ {len(dates)} days in {year}"
    data = daily_values[:, None, None] * np.ones((1, NLAT, NLON))
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": dates, "lat": LAT, "lon": LON},
        attrs={"units": "°C"},
    )


# ---------------------------------------------------------------------------
# Fixtures / monkeypatch helpers
# ---------------------------------------------------------------------------


def _patch_load_silo(monkeypatch, year_map: dict[int, xr.DataArray]) -> None:
    """Replace frost.load_silo_year with a dict lookup."""
    import src.indicators.frost as frost_mod

    def _fake_load(variable: str, year: int) -> xr.DataArray:
        if year not in year_map:
            raise FileNotFoundError(f"No synthetic data for year {year}")
        return year_map[year]

    monkeypatch.setattr(frost_mod, "load_silo_year", _fake_load)


# ---------------------------------------------------------------------------
# 1. Module-level constants
# ---------------------------------------------------------------------------


def test_frost_threshold_constant():
    from src.indicators.frost import FROST_THRESHOLD_C

    assert FROST_THRESHOLD_C == 2.0


def test_frost_threshold_is_float():
    from src.indicators.frost import FROST_THRESHOLD_C

    assert isinstance(FROST_THRESHOLD_C, float)


# ---------------------------------------------------------------------------
# 2. Output shape and coordinates
# ---------------------------------------------------------------------------


def test_output_shape_within_year(monkeypatch):
    """Result should be (lat, lon) for a within-year window."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]  # Apr–Oct, no cross-year
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=5.0)})

    result = frost_days_growing_season(2010, window=window)
    assert result.dims == ("lat", "lon")
    assert result.shape == (NLAT, NLON)


def test_output_shape_cross_year(monkeypatch):
    """Result should be (lat, lon) for a cross-year window."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["qld_summer"]  # Sep–Feb, cross-year
    _patch_load_silo(
        monkeypatch,
        {
            2010: _make_tmin_da(2010, fill_value=15.0),
            2011: _make_tmin_da(2011, fill_value=15.0),
        },
    )
    result = frost_days_growing_season(2010, window=window)
    assert result.dims == ("lat", "lon")
    assert result.shape == (NLAT, NLON)


def test_output_coords(monkeypatch):
    """lat/lon coordinates should be preserved from input."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2005: _make_tmin_da(2005, fill_value=5.0)})
    result = frost_days_growing_season(2005, window=window)
    np.testing.assert_array_equal(result.lat.values, LAT)
    np.testing.assert_array_equal(result.lon.values, LON)


# ---------------------------------------------------------------------------
# 3. Frost-count correctness
# ---------------------------------------------------------------------------


def test_zero_frost_days_above_threshold(monkeypatch):
    """All tmin = 10°C → zero frost days everywhere."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=10.0)})
    result = frost_days_growing_season(2010, window=window)
    assert float(np.nanmax(result.values)) == 0.0


def test_all_frost_days_below_threshold(monkeypatch):
    """All tmin = -5°C → every season day is a frost day."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]  # Apr–Oct = 214 days (non-leap)
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=-5.0)})
    result = frost_days_growing_season(2010, window=window)
    # Apr(30)+May(31)+Jun(30)+Jul(31)+Aug(31)+Sep(30)+Oct(31) = 214
    expected = 214
    assert float(np.nanmax(result.values)) == expected


def test_frost_count_at_threshold_boundary(monkeypatch):
    """tmin = 2.0°C exactly should NOT be a frost day (strict <)."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=2.0)})
    result = frost_days_growing_season(2010, window=window)
    assert float(np.nanmax(result.values)) == 0.0


def test_frost_count_just_below_threshold(monkeypatch):
    """tmin = 1.99°C → every season day is a frost day."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=1.99)})
    result = frost_days_growing_season(2010, window=window)
    expected = 214  # all Apr–Oct days
    assert float(np.nanmax(result.values)) == expected


def test_custom_threshold(monkeypatch):
    """Custom threshold=0°C: tmin=1.0°C should give 0 frost days."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=1.0)})
    result = frost_days_growing_season(2010, window=window, threshold=0.0)
    assert float(np.nanmax(result.values)) == 0.0


def test_specific_frost_days_counted(monkeypatch):
    """Inject exactly N days below threshold; verify count."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]  # Apr–Oct
    year = 2010
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    daily = np.full(len(dates), 5.0)  # warm by default

    # Set 7 days in June (month 6, within window) to -1°C
    june_mask = pd.DatetimeIndex(dates).month == 6
    frost_days_in_june = int(june_mask.sum())  # 30
    daily[june_mask] = -1.0

    _patch_load_silo(monkeypatch, {year: _make_tmin_da_from_array(year, daily)})
    result = frost_days_growing_season(year, window=window)
    # All June days are frost days = 30
    assert float(np.nanmax(result.values)) == frost_days_in_june


def test_frost_count_out_of_season_ignored(monkeypatch):
    """Days outside the growing-season window must not be counted."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]  # Apr–Oct
    year = 2010
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    daily = np.full(len(dates), 5.0)
    # Set January (outside window) to very cold
    jan_mask = pd.DatetimeIndex(dates).month == 1
    daily[jan_mask] = -20.0

    _patch_load_silo(monkeypatch, {year: _make_tmin_da_from_array(year, daily)})
    result = frost_days_growing_season(year, window=window)
    assert float(np.nanmax(result.values)) == 0.0


# ---------------------------------------------------------------------------
# 4. Cross-year window (QLD summer)
# ---------------------------------------------------------------------------


def test_cross_year_counts_both_halves(monkeypatch):
    """QLD summer window uses Oct–Dec from year and Jan–Feb from year+1."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["qld_summer"]  # Sep–Feb
    year = 2010

    # year: frost only in November (30 days, inside window)
    dates_yr = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    daily_yr = np.full(len(dates_yr), 5.0)
    nov_mask = pd.DatetimeIndex(dates_yr).month == 11
    daily_yr[nov_mask] = -2.0
    da_yr = _make_tmin_da_from_array(year, daily_yr)

    # year+1: frost only in February (28 days, inside window)
    dates_next = pd.date_range(f"{year+1}-01-01", f"{year+1}-12-31", freq="D")
    daily_next = np.full(len(dates_next), 5.0)
    feb_mask = pd.DatetimeIndex(dates_next).month == 2
    daily_next[feb_mask] = -2.0
    da_next = _make_tmin_da_from_array(year + 1, daily_next)

    _patch_load_silo(monkeypatch, {year: da_yr, year + 1: da_next})
    result = frost_days_growing_season(year, window=window)
    # Nov=30 (yr0) + Feb=28 (yr1) = 58
    assert float(np.nanmax(result.values)) == 58.0


# ---------------------------------------------------------------------------
# 5. NaN handling
# ---------------------------------------------------------------------------


def test_fully_nan_cell_returns_nan(monkeypatch):
    """Ocean / out-of-mask cells (all NaN) should return NaN."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    year = 2010
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    data = np.full((len(dates), NLAT, NLON), -5.0)
    data[:, 0, 0] = np.nan  # one fully-NaN cell

    da = xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": dates, "lat": LAT, "lon": LON},
    )
    _patch_load_silo(monkeypatch, {year: da})
    result = frost_days_growing_season(year, window=window)
    assert np.isnan(result.values[0, 0])
    assert not np.isnan(result.values[1, 1])


def test_partial_nan_not_propagated(monkeypatch):
    """Occasional NaN days within a cell should not make the count NaN."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    year = 2010
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    data = np.full((len(dates), NLAT, NLON), -5.0)
    # Set 3 days to NaN at cell [0,0]
    data[:3, 0, 0] = np.nan

    da = xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": dates, "lat": LAT, "lon": LON},
    )
    _patch_load_silo(monkeypatch, {year: da})
    result = frost_days_growing_season(year, window=window)
    # Cell [0,0] has < 214 (some days NaN in Jan, outside window anyway)
    assert np.isfinite(result.values[0, 0])


# ---------------------------------------------------------------------------
# 6. Attributes
# ---------------------------------------------------------------------------


def test_output_attributes(monkeypatch):
    """Output DataArray must carry required metadata attributes."""
    from src.indicators.frost import FROST_THRESHOLD_C, frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=5.0)})
    result = frost_days_growing_season(2010, window=window)

    assert result.attrs["units"] == "days"
    assert result.attrs["threshold_degC"] == FROST_THRESHOLD_C
    assert result.attrs["season_year"] == 2010
    assert result.attrs["season_label"] == window.label
    assert "long_name" in result.attrs
    assert "definition" in result.attrs


def test_custom_threshold_in_attrs(monkeypatch):
    """Custom threshold should be reflected in attrs."""
    from src.indicators.frost import frost_days_growing_season

    window = GROWING_WINDOWS["southern_winter"]
    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=5.0)})
    result = frost_days_growing_season(2010, window=window, threshold=0.0)
    assert result.attrs["threshold_degC"] == 0.0


# ---------------------------------------------------------------------------
# 7. Default window behaviour
# ---------------------------------------------------------------------------


def test_default_window_is_southern_winter(monkeypatch):
    """Calling without window= should default to southern_winter."""
    from src.indicators.frost import frost_days_growing_season

    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=10.0)})
    result = frost_days_growing_season(2010)
    assert result.attrs["season_label"] == "apr_oct"


def test_missing_year_raises(monkeypatch):
    """FileNotFoundError propagates when SILO data are absent."""
    from src.indicators.frost import frost_days_growing_season

    _patch_load_silo(monkeypatch, {})  # empty map → every year raises
    with pytest.raises(FileNotFoundError):
        frost_days_growing_season(2010)


# ---------------------------------------------------------------------------
# 8. Non-negativity
# ---------------------------------------------------------------------------


def test_frost_count_non_negative(monkeypatch):
    """Frost-day counts must never be negative."""
    from src.indicators.frost import frost_days_growing_season

    _patch_load_silo(monkeypatch, {2010: _make_tmin_da(2010, fill_value=8.0)})
    result = frost_days_growing_season(2010)
    vals = result.values[np.isfinite(result.values)]
    assert np.all(vals >= 0)
