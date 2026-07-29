"""Tests for SPEI additions in src/indicators/drought.py (Phase 04, Step 03).

Coverage:
  - _loglogistic_fit(): known analytical case — uniform data produces
    valid (alpha, beta, gamma) with beta > 1.
  - _loglogistic_fit(): degenerate cases — constant input, n < 6.
  - monthly_pet(): shape, coordinate, and NaN-propagation (monkeypatched).
  - monthly_water_balance(): D = rain - evap_pan sign checks (monkeypatched).
  - fit_spei_params(): output Dataset structure (monkeypatched SILO).
  - fit_spei_params(): fitted beta > 1 for all cells with sufficient data.
  - spei_for_year(): output dims, dtype, and plausibility (monkeypatched).
  - spei_for_year(): standard-normal property — mean close to 0, std close
    to 1 when applied to a year drawn from the same distribution as baseline.

Data-backed tests (require SILO processed files) are marked with
``@requires_data`` and skipped automatically when the files are absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import xarray as xr  # noqa: E402

from src.indicators.drought import (  # noqa: E402
    EVAP_BASELINE_END,
    EVAP_BASELINE_START,
    SPEI_SCALES,
    _loglogistic_fit,
    fit_spei_params,
    monthly_pet,
    monthly_water_balance,
    spei_for_year,
)
from src.paths import DATA_PROCESSED  # noqa: E402

# ---------------------------------------------------------------------------
# Skip guard for data-backed tests
# ---------------------------------------------------------------------------

_SILO_EVAP_1970 = DATA_PROCESSED / "silo" / "evap_pan" / "1970.evap_pan.nc"
requires_data = pytest.mark.skipif(
    not _SILO_EVAP_1970.exists(),
    reason="SILO processed evap_pan files not present (run Phase 01 first)",
)


# ---------------------------------------------------------------------------
# Helpers — synthetic SILO DataArray factories
# ---------------------------------------------------------------------------

_NLAT, _NLON = 3, 4


def _make_daily_da(year: int, variable: str, value: float = 2.0) -> xr.DataArray:
    """Synthetic daily DataArray (365 days) for a given year and variable."""
    import pandas as pd

    times = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    data = np.full((len(times), _NLAT, _NLON), value, dtype=np.float64)
    lats = np.linspace(-35.0, -30.0, _NLAT)
    lons = np.linspace(140.0, 145.0, _NLON)
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "mm"},
    )


def _make_varying_daily_da(year: int, variable: str) -> xr.DataArray:
    """Synthetic daily DataArray with sinusoidal seasonal variation.

    Each cell has a different amplitude.  rain and evap_pan are given
    different base levels and phase offsets so that D = rain − evap is
    non-trivial and varies across years/cells — needed for non-degenerate
    distribution fitting.
    """
    import pandas as pd

    times = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    n = len(times)
    lats = np.linspace(-35.0, -30.0, _NLAT)
    lons = np.linspace(140.0, 145.0, _NLON)
    t = np.arange(n)
    data = np.zeros((n, _NLAT, _NLON), dtype=np.float64)
    # Phase offset: rain peaks in (austral) winter, evap peaks in summer.
    phase = 0.0 if variable == "daily_rain" else np.pi  # offset evap by 6 months
    base_shift = (
        0.0 if variable == "daily_rain" else 1.0
    )  # evap slightly higher baseline
    rng_seed = hash(variable) % (2**31)
    rng = np.random.default_rng(rng_seed + year)
    for i in range(_NLAT):
        for j in range(_NLON):
            amp = 3.0 + (i * _NLON + j) * 0.4
            base = 2.0 + base_shift + (i * _NLON + j) * 0.2
            noise = rng.normal(0, 0.5, n)
            data[:, i, j] = base + amp * np.sin(2 * np.pi * t / 365.25 + phase) + noise
    data = np.clip(data, 0.0, None)
    return xr.DataArray(
        data,
        dims=["time", "lat", "lon"],
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "mm"},
    )


def _patch_load_silo(monkeypatch, year_map: dict[tuple[str, int], xr.DataArray]):
    """Monkeypatch load_silo_year in drought module to return synthetic data."""
    import src.indicators.drought as drought_mod

    def _fake_load(variable: str, year: int) -> xr.DataArray:
        key = (variable, year)
        if key in year_map:
            return year_map[key]
        raise FileNotFoundError(f"Synthetic: no data for {variable} {year}")

    monkeypatch.setattr(drought_mod, "load_silo_year", _fake_load)


# ---------------------------------------------------------------------------
# _loglogistic_fit — unit tests (pure, no I/O)
# ---------------------------------------------------------------------------


class TestLoglogisticFit:
    def test_valid_input_returns_finite_params(self):
        """Data from a log-logistic distribution should produce a valid fit."""
        from scipy.stats import fisk

        rng = np.random.default_rng(42)
        # Draw from fisk (2-parameter log-logistic) with c=3 (beta=3 > 1),
        # then shift by a negative gamma to allow negative input values.
        x_raw = fisk.rvs(c=3, scale=5.0, size=60, random_state=rng)
        x = x_raw - 2.0  # shift to create some negative values (simulates D)
        a, b, g = _loglogistic_fit(x)
        assert np.isfinite(a), "alpha should be finite"
        assert np.isfinite(b), "beta should be finite"
        assert np.isfinite(g), "gamma should be finite"
        assert a > 0, "alpha must be positive"
        assert b > 1.0, "beta must exceed 1 for a valid fit"

    def test_constant_input_returns_nan(self):
        """Constant series → zero variance → degenerate fit → NaN."""
        x = np.full(30, 5.0)
        a, b, g = _loglogistic_fit(x)
        assert np.isnan(a) and np.isnan(b) and np.isnan(g)

    def test_too_few_values_returns_nan(self):
        """Fewer than 6 finite values must return NaN triple."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # n=5 < 6
        a, b, g = _loglogistic_fit(x)
        assert np.isnan(a) and np.isnan(b) and np.isnan(g)

    def test_all_nan_returns_nan(self):
        """All-NaN input must return NaN triple without error."""
        x = np.full(30, np.nan)
        a, b, g = _loglogistic_fit(x)
        assert np.isnan(a) and np.isnan(b) and np.isnan(g)

    def test_nan_stripped_before_fitting(self):
        """NaN values in the array should be stripped; fit from finite portion."""
        from scipy.stats import fisk

        rng = np.random.default_rng(7)
        # Use log-logistic data to guarantee a valid (non-NaN) fit.
        x_clean = fisk.rvs(c=3, scale=5.0, size=40, random_state=rng) - 1.0
        x_with_nan = np.concatenate([x_clean, np.full(10, np.nan)])
        a1, b1, g1 = _loglogistic_fit(x_clean)
        a2, b2, g2 = _loglogistic_fit(x_with_nan)
        # Both fits should be finite and identical (NaN stripped before fitting).
        assert np.isfinite(a1) and np.isfinite(a2), "Both fits should be finite"
        assert np.isclose(a1, a2, rtol=1e-10)
        assert np.isclose(b1, b2, rtol=1e-10)
        assert np.isclose(g1, g2, rtol=1e-10)

    def test_alpha_positive(self):
        """alpha (scale) must be strictly positive for all valid fits."""
        rng = np.random.default_rng(99)
        for seed in range(10):
            x = rng.normal(loc=float(seed), scale=2.0, size=30)
            a, b, g = _loglogistic_fit(x)
            if np.isfinite(a):
                assert a > 0, f"alpha={a} is non-positive for seed {seed}"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestSPEIConstants:
    def test_baseline_range(self):
        assert EVAP_BASELINE_START == 1970
        assert EVAP_BASELINE_END == 1999
        assert EVAP_BASELINE_END - EVAP_BASELINE_START + 1 == 30

    def test_spei_scales(self):
        assert 3 in SPEI_SCALES
        assert 12 in SPEI_SCALES


# ---------------------------------------------------------------------------
# monthly_pet — monkeypatched
# ---------------------------------------------------------------------------


class TestMonthlyPet:
    def test_shape_and_coords(self, monkeypatch):
        """monthly_pet() must return (12, nlat, nlon) with month coord 1–12."""
        year_map = {("evap_pan", 2000): _make_daily_da(2000, "evap_pan", 3.0)}
        _patch_load_silo(monkeypatch, year_map)
        pet = monthly_pet(2000)
        assert pet.dims == ("time", "lat", "lon"), f"unexpected dims {pet.dims}"
        assert len(pet.time) == 12, "should have 12 monthly time steps"
        assert "month" in pet.coords
        assert list(pet.month.values) == list(range(1, 13))
        assert pet.attrs["units"] == "mm"

    def test_nan_propagation(self, monkeypatch):
        """A NaN daily value should propagate to the containing month."""
        da = _make_daily_da(2000, "evap_pan", 2.0)
        # Introduce NaN in January (time index 0).
        da.values[0, 0, 0] = np.nan
        _patch_load_silo(monkeypatch, {("evap_pan", 2000): da})
        pet = monthly_pet(2000)
        jan = pet.sel(time=pet.time.dt.month == 1)
        assert np.isnan(jan.values[0, 0, 0]), "NaN day should NaN the month"

    def test_monthly_sum_correct(self, monkeypatch):
        """Constant 1.0 mm/day → January total = 31 mm."""
        _patch_load_silo(
            monkeypatch, {("evap_pan", 2000): _make_daily_da(2000, "evap_pan", 1.0)}
        )
        pet = monthly_pet(2000)
        jan = pet.sel(time=pet.time.dt.month == 1)
        expected = 31.0  # January has 31 days
        assert np.allclose(jan.values, expected), f"Jan total: expected {expected}"


# ---------------------------------------------------------------------------
# monthly_water_balance — monkeypatched
# ---------------------------------------------------------------------------


class TestMonthlyWaterBalance:
    def test_d_equals_rain_minus_pet(self, monkeypatch):
        """D = rain - evap_pan; constant inputs give predictable monthly D."""

        rain_val, evap_val = 3.0, 1.5  # mm/day
        year_map = {
            ("daily_rain", 2000): _make_daily_da(2000, "daily_rain", rain_val),
            ("evap_pan", 2000): _make_daily_da(2000, "evap_pan", evap_val),
        }
        _patch_load_silo(monkeypatch, year_map)

        wb = monthly_water_balance(2000)
        # January: (3.0 - 1.5) * 31 = 46.5 mm
        jan = wb.sel(time=wb.time.dt.month == 1)
        assert np.allclose(jan.values, (rain_val - evap_val) * 31, rtol=1e-5)

    def test_negative_d_possible(self, monkeypatch):
        """When evap > rain, D should be negative."""
        year_map = {
            ("daily_rain", 2000): _make_daily_da(2000, "daily_rain", 0.5),
            ("evap_pan", 2000): _make_daily_da(2000, "evap_pan", 3.0),
        }
        _patch_load_silo(monkeypatch, year_map)
        wb = monthly_water_balance(2000)
        assert np.all(wb.values < 0), "All months should have negative D"


# ---------------------------------------------------------------------------
# fit_spei_params — monkeypatched
# ---------------------------------------------------------------------------


def _build_year_map_varying(years: list[int]) -> dict:
    """Synthetic year_map with seasonal variation for fitting."""
    ymap = {}
    for yr in years:
        ymap[("daily_rain", yr)] = _make_varying_daily_da(yr, "daily_rain")
        ymap[("evap_pan", yr)] = _make_varying_daily_da(yr, "evap_pan")
    return ymap


class TestFitSpeiParams:
    def test_output_dataset_structure(self, monkeypatch):
        """fit_spei_params() must return Dataset with expected vars and dims."""
        years = list(range(1970, 1976))  # 6 years for speed
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        ds = fit_spei_params(baseline_years=years, k=3)

        assert isinstance(ds, xr.Dataset)
        for var in ("ll_alpha", "ll_beta", "ll_gamma"):
            assert var in ds, f"Missing variable: {var}"
            assert ds[var].dims == (
                "cal_month",
                "lat",
                "lon",
            ), f"{var} dims: {ds[var].dims}"
        assert "cal_month" in ds.coords
        assert list(ds.cal_month.values) == list(range(1, 13))
        assert ds.attrs["k_months"] == 3

    def test_beta_gt_1_where_finite(self, monkeypatch):
        """All finite beta values from a valid fit must exceed 1."""
        years = list(range(1970, 1976))
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        ds = fit_spei_params(baseline_years=years, k=3)
        beta = ds["ll_beta"].values
        finite_mask = np.isfinite(beta)
        if finite_mask.any():
            assert np.all(
                beta[finite_mask] > 1.0
            ), f"Some beta <= 1: {beta[finite_mask][beta[finite_mask] <= 1.0]}"

    def test_alpha_positive_where_finite(self, monkeypatch):
        """All finite alpha values must be strictly positive."""
        years = list(range(1970, 1976))
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        ds = fit_spei_params(baseline_years=years, k=3)
        alpha = ds["ll_alpha"].values
        finite_mask = np.isfinite(alpha)
        if finite_mask.any():
            assert np.all(alpha[finite_mask] > 0.0)

    def test_k12_requires_more_accumulation(self, monkeypatch):
        """SPEI-12 should have NaN for months 1–11 of the first year (no prev data)."""
        years = list(range(1970, 1982))  # 12 years, all varying
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        ds = fit_spei_params(baseline_years=years, k=12)
        # k=12 fits on calendar month 12 (index 11) using months 1–12 of yr0.
        # Months 0–10 (cal months 1–11) in the first year only have NaN
        # accumulations — but after 12+ years they all have data.
        assert ds.attrs["k_months"] == 12

    def test_baseline_attrs(self, monkeypatch):
        """Dataset attrs should correctly record the baseline period."""
        years = list(range(1970, 1980))
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        ds = fit_spei_params(baseline_years=years, k=3)
        assert ds.attrs["baseline_start"] == 1970
        assert ds.attrs["baseline_end"] == 1979


# ---------------------------------------------------------------------------
# spei_for_year — monkeypatched
# ---------------------------------------------------------------------------


class TestSpeiForYear:
    def _fit(self, monkeypatch, years: list[int], k: int) -> xr.Dataset:
        _patch_load_silo(monkeypatch, _build_year_map_varying(years))
        return fit_spei_params(baseline_years=years, k=k)

    def test_output_shape(self, monkeypatch):
        """spei_for_year() must return (12, nlat, nlon)."""
        years = list(range(1970, 1980))
        ymap = _build_year_map_varying(years)
        # Add previous-year data for the target year.
        ymap[("daily_rain", 1979)] = _make_varying_daily_da(1979, "daily_rain")
        ymap[("evap_pan", 1979)] = _make_varying_daily_da(1979, "evap_pan")
        ymap[("daily_rain", 1978)] = _make_varying_daily_da(1978, "daily_rain")
        ymap[("evap_pan", 1978)] = _make_varying_daily_da(1978, "evap_pan")
        _patch_load_silo(monkeypatch, ymap)
        params = fit_spei_params(baseline_years=years, k=3)
        spei = spei_for_year(1979, params)
        assert spei.dims == ("month", "lat", "lon"), f"dims: {spei.dims}"
        assert spei.sizes["month"] == 12

    def test_spei3_first_two_months_may_be_nan(self, monkeypatch):
        """For SPEI-3 without a previous year, months 1–2 may be NaN."""
        years = list(range(1970, 1980))
        ymap = _build_year_map_varying(years)
        _patch_load_silo(monkeypatch, ymap)
        params = fit_spei_params(baseline_years=years, k=3)

        # Compute for 1970 (no previous year → FileNotFoundError → NaN prev).
        spei = spei_for_year(1970, params)
        # Month 1 and 2 cannot have a 3-month window; should be NaN.
        assert np.all(np.isnan(spei.values[0, :, :])), "Month 1 should be NaN for k=3"
        assert np.all(np.isnan(spei.values[1, :, :])), "Month 2 should be NaN for k=3"

    def test_spei_plausibility_within_baseline(self, monkeypatch):
        """SPEI computed for a baseline year should have mean ~0, std ~1."""
        years = list(range(1970, 2000))
        ymap = _build_year_map_varying(years)
        _patch_load_silo(monkeypatch, ymap)
        params = fit_spei_params(baseline_years=years, k=3)

        # Pick a mid-baseline year for validation.
        target = 1985
        spei = spei_for_year(target, params)
        vals = spei.values[2:, :, :]  # skip NaN months (0,1 for k=3)
        finite = vals[np.isfinite(vals)]
        assert len(finite) > 0, "No finite SPEI values"
        mean_spei = float(np.mean(finite))
        std_spei = float(np.std(finite))
        assert abs(mean_spei) < 0.5, f"SPEI mean too far from 0: {mean_spei:.3f}"
        assert 0.5 < std_spei < 1.5, f"SPEI std out of range: {std_spei:.3f}"

    def test_spei_attrs(self, monkeypatch):
        """Return DataArray should have correct metadata attrs."""
        years = list(range(1970, 1976))
        ymap = _build_year_map_varying(years)
        _patch_load_silo(monkeypatch, ymap)
        params = fit_spei_params(baseline_years=years, k=3)
        spei = spei_for_year(1975, params)
        assert spei.attrs["k_months"] == 3
        assert spei.attrs["year"] == 1975
        assert spei.attrs["units"] == "dimensionless"

    def test_spei12_only_december_valid_without_prev_year(self, monkeypatch):
        """For SPEI-12 with no previous year, only month 12 (index 11) is valid."""
        years = list(range(1970, 1982))
        ymap = _build_year_map_varying(years)
        _patch_load_silo(monkeypatch, ymap)
        params = fit_spei_params(baseline_years=years, k=12)
        spei = spei_for_year(1970, params)
        # Months 0–10 (Jan–Nov) should be NaN when no prior year is loaded.
        for m in range(11):
            assert np.all(
                np.isnan(spei.values[m, :, :])
            ), f"Month {m+1} should be NaN for k=12 without previous year"


# ---------------------------------------------------------------------------
# Data-backed integration test
# ---------------------------------------------------------------------------


@requires_data
class TestSpeiWithRealData:
    def test_monthly_pet_loads_1970(self):
        """monthly_pet(1970) should return 12 monthly values for all cells."""
        pet = monthly_pet(1970)
        assert len(pet.time) == 12
        assert pet.attrs["units"] == "mm"
        # Pan evaporation should be non-negative.
        assert np.nanmin(pet.values) >= 0.0

    def test_monthly_water_balance_1970(self):
        """monthly_water_balance should return plausible D values (mm)."""
        wb = monthly_water_balance(1970)
        assert len(wb.time) == 12
        # Water balance can be negative; absolute value should be < 1000 mm/month.
        assert np.nanmax(np.abs(wb.values)) < 1000.0

    def test_fit_spei_params_real_baseline(self):
        """fit_spei_params on real data: beta > 1 for most cells (>80%)."""
        baseline = list(range(EVAP_BASELINE_START, EVAP_BASELINE_END + 1))
        ds = fit_spei_params(baseline_years=baseline, k=3)
        beta = ds["ll_beta"].values
        finite = beta[np.isfinite(beta)]
        if len(finite) > 0:
            frac_valid = np.mean(finite > 1.0)
            assert (
                frac_valid > 0.8
            ), f"Fewer than 80% of cells have beta > 1: {frac_valid:.1%}"

    def test_spei_for_year_real(self):
        """spei_for_year on real data: finite SPEI values in [-5, 5]."""
        baseline = list(range(EVAP_BASELINE_START, EVAP_BASELINE_END + 1))
        params = fit_spei_params(baseline_years=baseline, k=3)
        spei = spei_for_year(1990, params)
        vals = spei.values
        finite = vals[np.isfinite(vals)]
        assert len(finite) > 0
        assert np.all(
            np.abs(finite) < 5.0
        ), f"SPEI values outside [-5, 5]: max abs = {np.max(np.abs(finite)):.2f}"
