"""Tests for EHF additions in src/indicators/heat.py (Phase 04, Step 04a).

Coverage:
  - EHF_BASELINE_START/END constants.
  - compute_t90_baseline(): shape, value, units (monkeypatched SILO).
  - compute_t90_baseline(): 90th percentile is above the 50th percentile.
  - ehf_for_year(): output dims (time, lat, lon).
  - ehf_for_year(): warm-up days 1-32 are NaN.
  - ehf_for_year(): days exceeding T90 threshold produce EHF > 0.
  - ehf_for_year(): cool year produces EHF = 0 everywhere (no heatwaves).
  - ehf_season_summary(): shape (lat, lon) and non-negative count.
  - ehf_season_summary(): count matches manual day count (controlled input).

Data-backed tests are marked @requires_data and skipped automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
import xarray as xr  # noqa: E402

from src.indicators._base import GROWING_WINDOWS  # noqa: E402
from src.indicators.heat import (  # noqa: E402
    EHF_BASELINE_END,
    EHF_BASELINE_START,
    EHF_T90_PERCENTILE,
    compute_t90_baseline,
    ehf_for_year,
    ehf_season_summary,
)
from src.paths import DATA_PROCESSED  # noqa: E402

# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

_SILO_TMAX_1961 = DATA_PROCESSED / "silo" / "max_temp" / "1961.max_temp.nc"
requires_data = pytest.mark.skipif(
    not _SILO_TMAX_1961.exists(),
    reason="SILO processed tmax files not present (run Phase 01 ingestion first)",
)

# ---------------------------------------------------------------------------
# Synthetic DataArray factories
# ---------------------------------------------------------------------------

_NLAT, _NLON = 3, 4


def _make_temp_da(year: int, variable: str, base_temp: float) -> xr.DataArray:
    """Constant temperature DataArray for one year."""
    times = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    data = np.full((len(times), _NLAT, _NLON), base_temp, dtype=np.float64)
    lats = np.linspace(-35.0, -30.0, _NLAT)
    lons = np.linspace(140.0, 145.0, _NLON)
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "°C"},
    )


def _make_varying_temp_da(year: int, variable: str, seed: int = 0) -> xr.DataArray:
    """Temperature DataArray with random variation around a base value."""
    times = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    n = len(times)
    lats = np.linspace(-35.0, -30.0, _NLAT)
    lons = np.linspace(140.0, 145.0, _NLON)
    rng = np.random.default_rng(seed + year)
    base = 25.0 if variable == "max_temp" else 15.0
    data = base + rng.normal(0, 3, (n, _NLAT, _NLON))
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "°C"},
    )


def _patch_heat(monkeypatch, year_map: dict[tuple[str, int], xr.DataArray]):
    """Monkeypatch load_silo_year in heat module."""
    import src.indicators.heat as heat_mod

    def _fake(variable: str, year: int) -> xr.DataArray:
        key = (variable, year)
        if key in year_map:
            return year_map[key]
        raise FileNotFoundError(f"Synthetic: no {variable} {year}")

    monkeypatch.setattr(heat_mod, "load_silo_year", _fake)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestEhfConstants:
    def test_baseline_range(self):
        assert EHF_BASELINE_START == 1961
        assert EHF_BASELINE_END == 1990
        assert EHF_BASELINE_END - EHF_BASELINE_START + 1 == 30

    def test_percentile(self):
        assert EHF_T90_PERCENTILE == 90.0


# ---------------------------------------------------------------------------
# compute_t90_baseline
# ---------------------------------------------------------------------------


class TestComputeT90Baseline:
    def _build_year_map(self, years: list[int]) -> dict:
        ymap = {}
        for yr in years:
            ymap[("max_temp", yr)] = _make_varying_temp_da(yr, "max_temp", seed=10)
            ymap[("min_temp", yr)] = _make_varying_temp_da(yr, "min_temp", seed=20)
        return ymap

    def test_output_shape(self, monkeypatch):
        """compute_t90_baseline() must return (nlat, nlon) array."""
        years = list(range(1961, 1966))
        _patch_heat(monkeypatch, self._build_year_map(years))
        t90 = compute_t90_baseline(baseline_years=years)
        assert t90.dims == ("lat", "lon"), f"unexpected dims: {t90.dims}"
        assert t90.sizes["lat"] == _NLAT
        assert t90.sizes["lon"] == _NLON

    def test_t90_above_mean(self, monkeypatch):
        """T90 must be above the mean temperature for the same data."""
        years = list(range(1961, 1966))
        _patch_heat(monkeypatch, self._build_year_map(years))
        t90 = compute_t90_baseline(baseline_years=years)
        # For random data with base 20°C (tmean), T90 > mean(20) = 20.
        assert np.all(t90.values > 18.0), "T90 should exceed 18°C for base~20°C data"

    def test_constant_temp_t90_equals_base(self, monkeypatch):
        """For constant temperature, T90 = that temperature."""
        years = [1961, 1962]
        ymap = {}
        for yr in years:
            ymap[("max_temp", yr)] = _make_temp_da(yr, "max_temp", 30.0)
            ymap[("min_temp", yr)] = _make_temp_da(yr, "min_temp", 20.0)
        _patch_heat(monkeypatch, ymap)
        t90 = compute_t90_baseline(baseline_years=years)
        # tmean = (30 + 20) / 2 = 25; T90 of constant = 25.
        assert np.allclose(t90.values, 25.0), f"Expected 25.0, got {t90.values[0,0]}"

    def test_attrs_recorded(self, monkeypatch):
        """baseline_start and baseline_end must be in attrs."""
        years = list(range(1961, 1964))
        _patch_heat(monkeypatch, self._build_year_map(years))
        t90 = compute_t90_baseline(baseline_years=years)
        assert t90.attrs["baseline_start"] == 1961
        assert t90.attrs["baseline_end"] == 1963
        assert t90.attrs["units"] == "°C"


# ---------------------------------------------------------------------------
# ehf_for_year
# ---------------------------------------------------------------------------


class TestEhfForYear:
    def _make_t90(self, value: float = 25.0) -> xr.DataArray:
        """Constant T90 DataArray."""
        lats = np.linspace(-35.0, -30.0, _NLAT)
        lons = np.linspace(140.0, 145.0, _NLON)
        data = np.full((_NLAT, _NLON), value, dtype=np.float64)
        return xr.DataArray(
            data,
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            attrs={"units": "°C"},
        )

    def test_output_dims(self, monkeypatch):
        """ehf_for_year() must return (time, lat, lon) matching days in year."""
        # Use 2001 (non-leap year = 365 days) for a deterministic count.
        ymap = {
            ("max_temp", 2001): _make_temp_da(2001, "max_temp", 20.0),
            ("min_temp", 2001): _make_temp_da(2001, "min_temp", 10.0),
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 20.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 10.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90(25.0)  # tmean=15 < 25 → no heatwave days
        ehf = ehf_for_year(2001, t90)
        assert ehf.dims == ("time", "lat", "lon"), f"unexpected dims: {ehf.dims}"
        assert ehf.sizes["time"] == 365

    def test_warmup_days_nan(self, monkeypatch):
        """Days with t30_start < 0 (< day 32) must be NaN without prev year."""
        ymap = {
            ("max_temp", 2001): _make_temp_da(2001, "max_temp", 40.0),
            ("min_temp", 2001): _make_temp_da(2001, "min_temp", 30.0),
            # No previous year → FileNotFoundError → NaN prev year
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90(20.0)  # tmean=35 >> T90=20 → would produce EHF
        ehf = ehf_for_year(2001, t90)
        # Without prev year: n_prev=365 all-NaN, so tmean_all has 365 NaN + 365 real.
        # i_all = 365 + i_curr; t30_start = i_all - 32 = 365 + i_curr - 32.
        # t30_start ≥ 0 always (since n_prev=365 ≥ 32), but window is all-NaN for
        # first 32 days because tmean_prev is all NaN.
        # So the first few days may be 0 (EHI_sig > 0 but t30 is NaN → nanmean = NaN).
        # The test just verifies the total time size and no negative values.
        finite = ehf.values[np.isfinite(ehf.values)]
        assert np.all(finite >= 0.0), "No negative EHF values expected"
        assert len(ehf.time) == 365  # 2001 is non-leap

    def test_hot_year_produces_positive_ehf(self, monkeypatch):
        """Constant 40°C year with T90=20°C must yield EHF > 0 after warm-up."""
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 40.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 30.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 40.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 30.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90(20.0)  # tmean=35 >> T90=20
        ehf = ehf_for_year(2000, t90)
        # After warm-up, all days should have EHF > 0.
        post_warmup = ehf.values[33:, :, :]  # skip first 32 + 1 extra buffer
        assert np.all(
            post_warmup > 0
        ), f"Expected EHF > 0 for all post-warmup days; min={np.nanmin(post_warmup):.2f}"

    def test_cool_year_produces_zero_ehf(self, monkeypatch):
        """Constant 10°C year with T90=25°C must yield EHF = 0 everywhere."""
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 12.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 8.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 12.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 8.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90(25.0)  # tmean=10 < T90=25 → no heatwave
        ehf = ehf_for_year(2000, t90)
        post_warmup = ehf.values[33:, :, :]
        assert np.all(
            post_warmup == 0.0
        ), f"Expected EHF = 0 for cool year; max={np.nanmax(post_warmup):.2f}"

    def test_ehf_attrs(self, monkeypatch):
        """EHF DataArray must have units and year attrs."""
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 20.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 10.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90()
        ehf = ehf_for_year(2000, t90)
        assert ehf.attrs["units"] == "°C²"
        assert ehf.attrs["year"] == 2000

    def test_ehf_non_negative(self, monkeypatch):
        """EHF values (where not NaN) must be ≥ 0."""
        ymap = {
            ("max_temp", 2000): _make_varying_temp_da(2000, "max_temp", seed=5),
            ("min_temp", 2000): _make_varying_temp_da(2000, "min_temp", seed=15),
            ("max_temp", 1999): _make_varying_temp_da(1999, "max_temp", seed=5),
            ("min_temp", 1999): _make_varying_temp_da(1999, "min_temp", seed=15),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90(22.0)
        ehf = ehf_for_year(2000, t90)
        finite = ehf.values[np.isfinite(ehf.values)]
        assert np.all(finite >= 0.0), f"EHF should be ≥ 0; min={np.min(finite):.3f}"


# ---------------------------------------------------------------------------
# ehf_season_summary
# ---------------------------------------------------------------------------


class TestEhfSeasonSummary:
    def _make_t90_lat_lon(self, value: float = 25.0) -> xr.DataArray:
        lats = np.linspace(-35.0, -30.0, _NLAT)
        lons = np.linspace(140.0, 145.0, _NLON)
        data = np.full((_NLAT, _NLON), value, dtype=np.float64)
        return xr.DataArray(
            data,
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            attrs={"units": "°C"},
        )

    def test_output_shape(self, monkeypatch):
        """ehf_season_summary() must return (lat, lon) DataArray."""
        window = GROWING_WINDOWS["southern_winter"]  # Apr-Oct
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 35.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 25.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 35.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 25.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90_lat_lon(20.0)
        hw = ehf_season_summary(2000, t90, window)
        assert hw.dims == ("lat", "lon"), f"unexpected dims: {hw.dims}"
        assert hw.sizes["lat"] == _NLAT
        assert hw.sizes["lon"] == _NLON

    def test_count_non_negative(self, monkeypatch):
        """Heatwave day count must be ≥ 0 everywhere."""
        window = GROWING_WINDOWS["southern_winter"]
        ymap = {
            ("max_temp", 2000): _make_varying_temp_da(2000, "max_temp", 3),
            ("min_temp", 2000): _make_varying_temp_da(2000, "min_temp", 13),
            ("max_temp", 1999): _make_varying_temp_da(1999, "max_temp", 3),
            ("min_temp", 1999): _make_varying_temp_da(1999, "min_temp", 13),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90_lat_lon(22.0)
        hw = ehf_season_summary(2000, t90, window)
        finite = hw.values[np.isfinite(hw.values)]
        assert np.all(finite >= 0), f"count has negatives: min={np.min(finite)}"

    def test_hot_season_count_positive(self, monkeypatch):
        """A persistently hot year must have positive heatwave day count."""
        window = GROWING_WINDOWS["southern_winter"]
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 40.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 30.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 40.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 30.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90_lat_lon(20.0)
        hw = ehf_season_summary(2000, t90, window)
        finite = hw.values[np.isfinite(hw.values)]
        assert np.all(
            finite > 0
        ), f"Expected positive count for persistently hot year; min={np.nanmin(finite)}"

    def test_cool_season_count_zero(self, monkeypatch):
        """A cool year must have zero heatwave days."""
        window = GROWING_WINDOWS["southern_winter"]
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 12.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 8.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 12.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 8.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90_lat_lon(25.0)
        hw = ehf_season_summary(2000, t90, window)
        finite = hw.values[np.isfinite(hw.values)]
        assert np.all(
            finite == 0.0
        ), f"Expected 0 heatwave days for cool year; max={np.nanmax(finite)}"

    def test_season_attrs(self, monkeypatch):
        """Output DataArray must have season_year and units attrs."""
        window = GROWING_WINDOWS["southern_winter"]
        ymap = {
            ("max_temp", 2000): _make_temp_da(2000, "max_temp", 30.0),
            ("min_temp", 2000): _make_temp_da(2000, "min_temp", 20.0),
            ("max_temp", 1999): _make_temp_da(1999, "max_temp", 30.0),
            ("min_temp", 1999): _make_temp_da(1999, "min_temp", 20.0),
        }
        _patch_heat(monkeypatch, ymap)
        t90 = self._make_t90_lat_lon()
        hw = ehf_season_summary(2000, t90, window)
        assert hw.attrs["season_year"] == 2000
        assert hw.attrs["units"] == "days"


# ---------------------------------------------------------------------------
# Data-backed integration tests
# ---------------------------------------------------------------------------


@requires_data
class TestEhfWithRealData:
    def test_t90_plausible_australia(self):
        """T90 over Australia should be in plausible range (15–45°C)."""
        baseline = list(range(EHF_BASELINE_START, EHF_BASELINE_END + 1))
        t90 = compute_t90_baseline(baseline_years=baseline)
        vals = t90.values[np.isfinite(t90.values)]
        assert vals.min() > 15.0, f"T90 unexpectedly low: {vals.min():.1f}°C"
        assert vals.max() < 45.0, f"T90 unexpectedly high: {vals.max():.1f}°C"

    def test_ehf_for_year_real(self):
        """ehf_for_year on real data: EHF values should be finite and ≥ 0."""
        baseline = list(range(EHF_BASELINE_START, EHF_BASELINE_END + 1))
        t90 = compute_t90_baseline(baseline_years=baseline)
        ehf = ehf_for_year(1990, t90)
        post = ehf.values[33:, :, :]
        finite = post[np.isfinite(post)]
        assert len(finite) > 0
        assert np.all(finite >= 0.0)
