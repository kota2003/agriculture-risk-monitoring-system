"""
src/indicators/drought.py — Drought-related climate indicators (Phase 04).

Implements:
  - SPI (Standardised Precipitation Index): McKee et al. (1993).
    Zero-adjusted Gamma distribution is fitted at each grid cell for each
    calendar month using the WMO 1961-1990 climatological baseline.
    k-month precipitation accumulations (SPI-3, SPI-12 by default) are
    transformed to standard normal via the fitted CDF.
  - CDD (Consecutive Dry Days): maximum number of consecutive days with
    daily rainfall < 1 mm over the growing season.

All indicators are computed at SILO grid resolution (dims: time, lat, lon),
consistent with scope §3.6 and §5.1.  Region aggregation and distributional
summaries are the responsibility of the calling script
(phase04_s02_drought_grid.py).

Gamma fitting procedure (WMO 2012, pp. 14–15):
  For each calendar month m and each k-month accumulation window, collect the
  n_baseline k-month totals.  Estimate the probability of zero (q = n_zeros /
  n_total).  Apply Thom (1958) analytical MLE to non-zero values:
    A = ln(x̄) − mean(ln(xᵢ))
    α̂ = (1 + √(1 + 4A/3)) / (4A)
    β̂ = x̄ / α̂
  Build the mixed CDF: H(x) = q + (1 − q) × Γ_CDF(x; α̂, β̂), x > 0
                               H(0) = q
  SPI = Φ⁻¹(H(x)), where Φ⁻¹ is the standard-normal quantile function.

References
----------
SPI:
  McKee, T.B., Doesken, N.J. & Kleist, J. (1993). The relationship of drought
  frequency and duration to time scales. Proc. 8th Conf. Applied Climatology,
  American Meteorological Society, 179–184.

  WMO (2012). Standardized Precipitation Index User Guide (WMO-No. 1090).
  World Meteorological Organization, Geneva.

  Thom, H.C.S. (1958). A note on the Gamma distribution. Monthly Weather
  Review, 86(4), 117–122.

CDD:
  ETCCDI (2009). Indices for monitoring changes in extremes.
  http://etccdi.pacificclimate.org/list_27_indices.shtml
"""

from __future__ import annotations

import numpy as np
import xarray as xr
from scipy import stats

from src.indicators._base import (
    EVAP,
    RAIN,
    GrowingWindow,
    load_silo_year,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Rainfall threshold below which a day is classified as "dry" (mm/day).
RAIN_DRY_THRESHOLD: float = 1.0

#: Default accumulation periods for SPI.
SPI_SCALES: tuple[int, ...] = (3, 12)

#: WMO standard baseline years for SPI fitting.
SPI_BASELINE_START: int = 1961
SPI_BASELINE_END: int = 1990


# ---------------------------------------------------------------------------
# Monthly aggregation
# ---------------------------------------------------------------------------


def monthly_rain(year: int) -> xr.DataArray:
    """Aggregate daily rainfall to monthly totals for a single calendar year.

    Parameters
    ----------
    year:
        Calendar year (1961–2024).

    Returns
    -------
    xr.DataArray with dims (month, lat, lon) where month is 1–12.
    Missing values in daily data propagate: a month with any NaN day → NaN.
    """
    rain_daily = load_silo_year(RAIN, year)
    # resample to monthly totals; skipna=False propagates NaN
    rain_mon = rain_daily.resample(time="1ME").sum(skipna=False)
    # Add a 'month' coordinate (1–12) for easier indexing later.
    rain_mon = rain_mon.assign_coords(month=("time", rain_mon.time.dt.month.values))
    rain_mon.attrs["units"] = "mm"
    rain_mon.attrs["long_name"] = "Monthly precipitation total"
    return rain_mon


# ---------------------------------------------------------------------------
# SPI Gamma parameter fitting
# ---------------------------------------------------------------------------


def _thom_gamma_fit(x: np.ndarray) -> tuple[float, float]:
    """Thom (1958) analytical MLE for Gamma distribution parameters.

    Parameters
    ----------
    x : 1-D array of positive values (zeros excluded before calling).

    Returns
    -------
    (alpha, beta) where beta is the scale (mean / alpha).
    Returns (NaN, NaN) if x has fewer than 4 non-zero values or is degenerate.
    """
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) < 4:
        return np.nan, np.nan
    ln_xbar = np.log(x.mean())
    mean_lnx = np.mean(np.log(x))
    A = ln_xbar - mean_lnx
    if A <= 0:
        return np.nan, np.nan
    alpha = (1.0 + np.sqrt(1.0 + 4.0 * A / 3.0)) / (4.0 * A)
    beta = x.mean() / alpha
    return alpha, beta


def fit_spi_params(
    baseline_years: list[int],
    k: int,
) -> xr.Dataset:
    """Fit zero-adjusted Gamma parameters for SPI at every grid cell.

    For each calendar month m and each grid cell (lat, lon), collects the
    k-month accumulated rainfall ending at month m across all baseline years,
    then fits the Gamma distribution via Thom (1958).

    Parameters
    ----------
    baseline_years:
        List of years used for climatological fitting (e.g. 1961–1990).
        Each year must have a corresponding processed SILO file.
    k:
        Accumulation period in months (e.g. 3 for SPI-3, 12 for SPI-12).

    Returns
    -------
    xr.Dataset with coordinates (cal_month, lat, lon) and variables:
        alpha      — Gamma shape parameter (NaN where insufficient data)
        beta       — Gamma scale parameter
        prob_zero  — Probability of zero precipitation P(X=0)

    Raises
    ------
    FileNotFoundError if any baseline year file is missing.
    """
    # ---- 1. Load monthly totals for all baseline years ----
    # Build a CONTINUOUS monthly series: (n_years * 12, nlat, nlon).
    # Treating years as a continuous series (rather than fitting each year
    # independently) is essential for SPI-12 — a 12-month rolling sum for
    # October requires November of the prior year, which is only available
    # when years are concatenated in sequence.
    n_years = len(baseline_years)
    n_months_total = n_years * 12
    rain_continuous = None  # (n_months_total, nlat, nlon)
    lat = None
    lon = None

    for idx, yr in enumerate(baseline_years):
        da = monthly_rain(yr)  # dims: (time=12, lat, lon)
        arr = da.values  # (12, nlat, nlon)
        if rain_continuous is None:
            nlat, nlon = arr.shape[1], arr.shape[2]
            rain_continuous = np.full(
                (n_months_total, nlat, nlon), np.nan, dtype=np.float64
            )
            lat = da.lat.values
            lon = da.lon.values
        rain_continuous[idx * 12 : idx * 12 + 12, :, :] = arr

    # ---- 2. Compute k-month rolling sums on the continuous series ----
    # accum[t] = sum of rain_continuous[t-k+1 : t+1] (valid from t >= k-1).
    accum_cont = np.full_like(rain_continuous, np.nan)
    for t in range(k - 1, n_months_total):
        accum_cont[t, :, :] = rain_continuous[t - k + 1 : t + 1, :, :].sum(axis=0)

    # ---- 3. Fit Gamma per calendar month per cell ----
    # For each calendar month m (0=Jan, 11=Dec), extract k-month sums from
    # the continuous series at positions m, m+12, m+24, … (same calendar month
    # across baseline years).  Positions < k-1 are NaN and are skipped
    # automatically by isfinite filtering.
    alpha_arr = np.full((12, nlat, nlon), np.nan, dtype=np.float64)
    beta_arr = np.full((12, nlat, nlon), np.nan, dtype=np.float64)
    pzero_arr = np.full((12, nlat, nlon), np.nan, dtype=np.float64)

    for m in range(12):  # calendar month index (0=Jan, 11=Dec)
        # Indices in the continuous series that correspond to calendar month m.
        indices_m = np.arange(m, n_months_total, 12)
        x_m = accum_cont[indices_m, :, :]  # (n_years, nlat, nlon)
        for i in range(nlat):
            for j in range(nlon):
                ts = x_m[:, i, j]
                valid = ts[np.isfinite(ts)]
                if len(valid) == 0:
                    continue
                n_total = len(valid)
                n_zero = int(np.sum(valid <= 0))
                q = n_zero / n_total
                pzero_arr[m, i, j] = q
                nonzero = valid[valid > 0]
                if len(nonzero) >= 4:
                    a, b = _thom_gamma_fit(nonzero)
                    alpha_arr[m, i, j] = a
                    beta_arr[m, i, j] = b

    # ---- 4. Wrap in xarray Dataset ----
    cal_months = np.arange(1, 13)
    ds = xr.Dataset(
        {
            "alpha": (["cal_month", "lat", "lon"], alpha_arr),
            "beta": (["cal_month", "lat", "lon"], beta_arr),
            "prob_zero": (["cal_month", "lat", "lon"], pzero_arr),
        },
        coords={"cal_month": cal_months, "lat": lat, "lon": lon},
    )
    ds.attrs["k_months"] = k
    ds.attrs["baseline_start"] = baseline_years[0]
    ds.attrs["baseline_end"] = baseline_years[-1]
    ds.attrs["method"] = "Thom-1958 MLE; WMO-No.1090"
    return ds


# ---------------------------------------------------------------------------
# SPI computation for one year
# ---------------------------------------------------------------------------


def spi_for_year(
    year: int,
    params: xr.Dataset,
) -> xr.DataArray:
    """Compute SPI values for all months of a single year.

    Uses pre-fitted Gamma parameters (from fit_spi_params) to transform the
    observed k-month accumulation into a standard normal (SPI) value for each
    calendar month and each grid cell.

    Parameters
    ----------
    year:
        Calendar year to compute SPI for (1961–2024).
    params:
        xr.Dataset produced by fit_spi_params(); must contain alpha, beta,
        prob_zero with coordinate cal_month (1–12).

    Returns
    -------
    xr.DataArray with dims (month, lat, lon).
        Values are SPI (standard normal, dimensionless).
        Months where the k-month accumulation cannot be computed (first k-1
        months of the year) are set to NaN.
    """
    k = int(params.attrs["k_months"])

    # Load monthly rainfall for the target year AND the previous year.
    # Prepending the previous year's data allows rolling sums for early months
    # (e.g. January for SPI-12 needs Dec of the prior year through Jan).
    try:
        rain_prev = monthly_rain(year - 1).values  # (12, nlat, nlon)
    except FileNotFoundError:
        # If the previous year is unavailable (e.g. year = first SILO year),
        # fill with NaN — the first k-1 months of the target year will be NaN.
        rain_yr_tmp = monthly_rain(year)
        rain_prev = np.full_like(rain_yr_tmp.values, np.nan)

    rain_curr = monthly_rain(year)
    rain_curr_np = rain_curr.values  # (12, nlat, nlon)
    nlat, nlon = rain_curr_np.shape[1], rain_curr_np.shape[2]

    # Concatenate: (24, nlat, nlon) — previous year + current year.
    rain_24 = np.concatenate([rain_prev, rain_curr_np], axis=0)  # (24, nlat, nlon)

    # Compute k-month rolling sums over the 24-month series.
    # We only need results for the current year (indices 12-23 of rain_24).
    accum = np.full((12, nlat, nlon), np.nan)
    for m in range(12):
        t = 12 + m  # index in rain_24 for month m of the current year
        if t - k + 1 >= 0:
            window = rain_24[t - k + 1 : t + 1, :, :]
            if not np.all(np.isnan(window)):
                accum[m, :, :] = window.sum(axis=0)

    # Retrieve fitted parameters (shape: (12, nlat, nlon)).
    alpha = params["alpha"].values  # (12, nlat, nlon)
    beta = params["beta"].values
    pzero = params["prob_zero"].values

    spi_np = np.full_like(accum, np.nan)

    for m in range(12):
        x = accum[m, :, :]  # (nlat, nlon)
        a = alpha[m, :, :]
        b = beta[m, :, :]
        q = pzero[m, :, :]

        # Compute mixed CDF: H(x) = q + (1-q) * Gamma_CDF(x; a, b)
        # where H(0) = q.
        valid_mask = np.isfinite(a) & np.isfinite(b) & np.isfinite(q) & np.isfinite(x)

        h = np.full(x.shape, np.nan)
        xv = x[valid_mask]
        av = a[valid_mask]
        bv = b[valid_mask]
        qv = q[valid_mask]

        # Gamma CDF: scipy parameterises as scale=beta, loc=0
        gcdf = stats.gamma.cdf(xv, a=av, scale=bv)
        hv = qv + (1.0 - qv) * gcdf
        # Handle exact zeros separately: H(0) = q
        hv = np.where(xv <= 0, qv, hv)
        # Clip to avoid infinite SPI from numerical edge values.
        hv = np.clip(hv, 1e-6, 1.0 - 1e-6)
        h[valid_mask] = hv

        spi_np[m, :, :] = stats.norm.ppf(h)

    # Build DataArray with month coordinate.
    months = np.arange(1, 13)
    spi_da = xr.DataArray(
        spi_np,
        dims=["month", "lat", "lon"],
        coords={
            "month": months,
            "lat": params.lat.values,
            "lon": params.lon.values,
        },
    )
    spi_da.attrs["units"] = "dimensionless"
    spi_da.attrs["long_name"] = f"SPI-{k}"
    spi_da.attrs["k_months"] = k
    spi_da.attrs["year"] = year
    return spi_da


# ---------------------------------------------------------------------------
# CDD — Consecutive Dry Days over the growing season
# ---------------------------------------------------------------------------


def _max_consecutive_below(arr: np.ndarray, threshold: float) -> int:
    """Return the maximum run of consecutive values below threshold.

    Parameters
    ----------
    arr: 1-D numpy array of daily rainfall values.
    threshold: dry-day threshold (exclusive, i.e. < threshold).

    Returns
    -------
    Integer count (0 if all values are >= threshold or array is empty).
    """
    is_dry = arr < threshold
    if not is_dry.any():
        return 0
    # Find run lengths using diff on the cumulative sum trick.
    # Pad with False on both ends to capture runs at array edges.
    padded = np.concatenate([[False], is_dry, [False]])
    diff = np.diff(padded.astype(int))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return int((ends - starts).max())


def cdd_growing_season(
    year: int,
    window: GrowingWindow,
    threshold: float = RAIN_DRY_THRESHOLD,
) -> xr.DataArray:
    """Maximum consecutive dry days within the growing season for one year.

    Parameters
    ----------
    year:
        Calendar year (season-start year for cross-year windows).
    window:
        GrowingWindow defining which months belong to the growing season.
    threshold:
        Dry-day threshold in mm/day (default 1.0 mm).  Days with rainfall
        strictly less than this value are counted as "dry".

    Returns
    -------
    xr.DataArray with dims (lat, lon) — integer CDD values.
    """
    rain_yr0 = load_silo_year(RAIN, year)

    if window.cross_year:
        rain_yr1 = load_silo_year(RAIN, year + 1)
        rain_full = xr.concat([rain_yr0, rain_yr1], dim="time")
    else:
        rain_full = rain_yr0

    # Subset to growing-season months.
    if window.cross_year:
        mask_yr0 = rain_full.time.dt.year == year
        mask_yr1 = rain_full.time.dt.year == year + 1
        in_season = (mask_yr0 & rain_full.time.dt.month.isin(window.months_yr0)) | (
            mask_yr1 & rain_full.time.dt.month.isin(window.months_yr1)
        )
    else:
        in_season = rain_full.time.dt.month.isin(window.months_yr0)

    rain_season = rain_full.sel(time=in_season)

    # Compute max consecutive dry days per grid cell.
    rain_np = rain_season.values  # (n_days, nlat, nlon)
    nlat, nlon = rain_np.shape[1], rain_np.shape[2]
    cdd_np = np.full((nlat, nlon), np.nan, dtype=np.float64)

    for i in range(nlat):
        for j in range(nlon):
            ts = rain_np[:, i, j]
            if np.all(np.isnan(ts)):
                continue  # masked cell
            # Replace NaN with 0 conservatively (NaN day treated as non-dry).
            ts_clean = np.where(np.isnan(ts), 0.0, ts)
            cdd_np[i, j] = _max_consecutive_below(ts_clean, threshold)

    cdd_da = xr.DataArray(
        cdd_np,
        dims=["lat", "lon"],
        coords={"lat": rain_season.lat.values, "lon": rain_season.lon.values},
    )
    cdd_da.attrs["units"] = "days"
    cdd_da.attrs["long_name"] = (
        f"Max consecutive dry days (<{threshold} mm) — " f"{window.label} — {year}"
    )
    cdd_da.attrs["threshold_mm"] = threshold
    cdd_da.attrs["season_year"] = year
    cdd_da.attrs["season_label"] = window.label
    return cdd_da


# ---------------------------------------------------------------------------
# SPEI — Standardised Precipitation Evapotranspiration Index
# ---------------------------------------------------------------------------
#
# Vicente-Serrano, S.M., Begueria, S. & Lopez-Moreno, J.I. (2010).
# A multiscalar drought index sensitive to global warming: the Standardized
# Precipitation Evapotranspiration Index. Journal of Climate, 23, 1696–1718.
#
# Distribution: 3-parameter Log-logistic, fitted per calendar month per cell
# via Probability-Weighted Moments (PWM / L-moments; Hosking 1990).
#
# Baseline period: 1970–1999 (30 years).
#   Adaptive override — PROJECT_WORKFLOW §4.2:
#   SILO evap_pan is populated from 1970 onward (Phase 01 empirical finding).
#   The WMO standard baseline 1961–1990 is therefore unavailable for SPEI.
#   1970–1999 is the earliest 30-year block fully covered by evap_pan and
#   satisfies the WMO norm of a 30-year climatological baseline.
#   This override is logged in PROJECT_LOG Phase 04 Step 03.
#
# Parameterisation of the 3-parameter log-logistic:
#   F(x; α, β, γ) = 1 / (1 + (α / (x − γ))^β)   for x > γ
# implemented via scipy.stats.fisk (2-parameter) shifted by γ:
#   F(x) = fisk.cdf(x − γ, c=β, scale=α)
# The mean of this distribution exists only for β > 1; fits with β ≤ 1
# are treated as degenerate and return NaN.
#
# Water-balance input: D = monthly_rain − monthly_evap_pan
# D can be negative; γ shifts the origin to accommodate negative values.

EVAP_BASELINE_START: int = 1970
EVAP_BASELINE_END: int = 1999  # 1970–1999, 30 years

SPEI_SCALES: tuple[int, ...] = (3, 12)


def monthly_pet(year: int) -> xr.DataArray:
    """Aggregate daily pan evaporation to monthly totals for one calendar year.

    Parameters
    ----------
    year:
        Calendar year (1970–2024; evap_pan is unavailable before 1970).

    Returns
    -------
    xr.DataArray with dims (month, lat, lon) and month coordinate 1–12.
    Missing days propagate: a month with any NaN day returns NaN.

    Raises
    ------
    FileNotFoundError if the processed SILO evap_pan file is absent.
    """
    evap_daily = load_silo_year(EVAP, year)
    evap_mon = evap_daily.resample(time="1ME").sum(skipna=False)
    evap_mon = evap_mon.assign_coords(month=("time", evap_mon.time.dt.month.values))
    evap_mon.attrs["units"] = "mm"
    evap_mon.attrs["long_name"] = "Monthly pan evaporation total"
    return evap_mon


def monthly_water_balance(year: int) -> xr.DataArray:
    """Compute monthly water-balance deficit D = rain − evap_pan.

    Parameters
    ----------
    year:
        Calendar year (1970–2024).

    Returns
    -------
    xr.DataArray with dims (month, lat, lon) and month coordinate 1–12.
    Units: mm.  Negative values indicate evaporative excess.
    """
    rain = monthly_rain(year)  # (12, nlat, nlon)
    pet = monthly_pet(year)  # (12, nlat, nlon)

    # Align on the shared time dimension (both should have identical lat/lon).
    # Use .values arithmetic to avoid potential coordinate mismatch from the
    # different resample calls producing slightly different time stamps.
    d = rain.copy(data=rain.values - pet.values)
    d.attrs["units"] = "mm"
    d.attrs["long_name"] = "Monthly water-balance deficit (rain - evap_pan)"
    return d


# ---------------------------------------------------------------------------
# Log-logistic (3-parameter) fitting
# ---------------------------------------------------------------------------


def _loglogistic_fit(x: np.ndarray) -> tuple[float, float, float]:
    """Fit a 3-parameter log-logistic distribution via PWM (Hosking 1990).

    Follows Vicente-Serrano et al. (2010) Appendix.

    Parameters
    ----------
    x : 1-D array of water-balance values (may be negative or zero).

    Returns
    -------
    (alpha, beta, gamma)
        alpha : scale  (> 0)
        beta  : shape  (> 1 required for finite mean)
        gamma : location / origin shift
    Returns (NaN, NaN, NaN) for degenerate inputs.
    """
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 6:
        return np.nan, np.nan, np.nan

    x_s = np.sort(x)
    # Ascending (Landwehr 1979) plotting positions: F_i = (i − 0.35) / n.
    # The 3-parameter log-logistic PWM estimator of Vicente-Serrano (2010)
    # uses ascending α-type moments bⱼ = mean(x × F^j) (x in ascending order),
    # NOT descending β-type moments mean(x × (1−F)^j).
    F = (np.arange(1, n + 1) - 0.35) / n

    # Probability-Weighted Moments b0, b1, b2 (ascending α-type).
    w0 = np.mean(x_s)  # b0 = mean
    w1 = float(np.mean(x_s * F))  # b1 = mean(x × F)
    w2 = float(np.mean(x_s * F**2))  # b2 = mean(x × F²)

    # Shape parameter beta.
    # β = (b0 − 2b1) / (6b1 − b0 − 6b2)
    # Note: numerator is (b0 − 2b1), i.e. negated vs a descending-PWM
    # convention — this correctly recovers β > 0 for log-logistic data.
    denom = 6.0 * w1 - w0 - 6.0 * w2
    if abs(denom) < 1e-12:
        return np.nan, np.nan, np.nan
    beta = (w0 - 2.0 * w1) / denom

    # Require beta > 1 (ensures finite mean of the fitted distribution).
    if beta <= 1.0 or not np.isfinite(beta):
        return np.nan, np.nan, np.nan

    # Reflection formula: Γ(1+1/β)·Γ(1-1/β) = π/β / sin(π/β).
    try:
        factor = np.pi / beta / np.sin(np.pi / beta)
    except (ZeroDivisionError, ValueError):
        return np.nan, np.nan, np.nan

    # Scale and location parameters.
    # α = (2b1 − b0) × β / factor   [= L-scale × β / factor > 0]
    # γ = b0 − α × factor
    alpha = (2.0 * w1 - w0) * beta / factor
    gamma = w0 - alpha * factor

    if alpha <= 0 or not np.isfinite(alpha) or not np.isfinite(gamma):
        return np.nan, np.nan, np.nan

    return alpha, beta, gamma


# ---------------------------------------------------------------------------
# SPEI parameter fitting over the baseline
# ---------------------------------------------------------------------------


def fit_spei_params(
    baseline_years: list[int],
    k: int,
) -> xr.Dataset:
    """Fit 3-parameter log-logistic parameters for SPEI at every grid cell.

    Baseline period should be 1970–1999 (30 years) due to evap_pan
    availability (see module-level EVAP_BASELINE_START / END constants).

    Parameters
    ----------
    baseline_years:
        List of years used for fitting (e.g. list(range(1970, 2000))).
    k:
        Accumulation period in months (3 for SPEI-3, 12 for SPEI-12).

    Returns
    -------
    xr.Dataset with coordinates (cal_month, lat, lon) and variables:
        ll_alpha  — log-logistic scale parameter
        ll_beta   — log-logistic shape parameter
        ll_gamma  — log-logistic location parameter
    """
    n_years = len(baseline_years)
    n_months_total = n_years * 12

    d_continuous = None  # (n_months_total, nlat, nlon)
    lat = lon = None

    for idx, yr in enumerate(baseline_years):
        da = monthly_water_balance(yr)  # (12, nlat, nlon)
        arr = da.values
        if d_continuous is None:
            nlat, nlon = arr.shape[1], arr.shape[2]
            d_continuous = np.full(
                (n_months_total, nlat, nlon), np.nan, dtype=np.float64
            )
            lat = da.lat.values
            lon = da.lon.values
        d_continuous[idx * 12 : idx * 12 + 12, :, :] = arr

    # k-month rolling sums on the continuous series (same logic as SPI).
    accum_cont = np.full_like(d_continuous, np.nan)
    for t in range(k - 1, n_months_total):
        accum_cont[t, :, :] = d_continuous[t - k + 1 : t + 1, :, :].sum(axis=0)

    # Fit per calendar month per cell.
    ll_alpha = np.full((12, nlat, nlon), np.nan, dtype=np.float64)
    ll_beta = np.full((12, nlat, nlon), np.nan, dtype=np.float64)
    ll_gamma = np.full((12, nlat, nlon), np.nan, dtype=np.float64)

    for m in range(12):
        indices_m = np.arange(m, n_months_total, 12)
        x_m = accum_cont[indices_m, :, :]  # (n_years, nlat, nlon)
        for i in range(nlat):
            for j in range(nlon):
                ts = x_m[:, i, j]
                valid = ts[np.isfinite(ts)]
                if len(valid) < 6:
                    continue
                a, b, g = _loglogistic_fit(valid)
                ll_alpha[m, i, j] = a
                ll_beta[m, i, j] = b
                ll_gamma[m, i, j] = g

    cal_months = np.arange(1, 13)
    ds = xr.Dataset(
        {
            "ll_alpha": (["cal_month", "lat", "lon"], ll_alpha),
            "ll_beta": (["cal_month", "lat", "lon"], ll_beta),
            "ll_gamma": (["cal_month", "lat", "lon"], ll_gamma),
        },
        coords={"cal_month": cal_months, "lat": lat, "lon": lon},
    )
    ds.attrs["k_months"] = k
    ds.attrs["baseline_start"] = baseline_years[0]
    ds.attrs["baseline_end"] = baseline_years[-1]
    ds.attrs["distribution"] = "3-parameter log-logistic (PWM; Vicente-Serrano 2010)"
    ds.attrs["baseline_note"] = (
        "1970-1999 baseline (adaptive override: evap_pan unavailable before 1970)"
    )
    return ds


# ---------------------------------------------------------------------------
# SPEI computation for one year
# ---------------------------------------------------------------------------


def spei_for_year(
    year: int,
    params: xr.Dataset,
) -> xr.DataArray:
    """Compute SPEI values for all months of a single year.

    Parameters
    ----------
    year:
        Calendar year to compute SPEI for (1970–2024).
    params:
        xr.Dataset produced by fit_spei_params(); must contain
        ll_alpha, ll_beta, ll_gamma with coordinate cal_month (1–12).

    Returns
    -------
    xr.DataArray with dims (month, lat, lon).
        Values are SPEI (standard normal, dimensionless).
        Months where the k-month accumulation cannot be computed (first k-1
        months if the previous year is absent) are NaN.
    """
    k = int(params.attrs["k_months"])

    # Prepend previous year's water-balance, same logic as spi_for_year.
    try:
        d_prev = monthly_water_balance(year - 1).values  # (12, nlat, nlon)
    except FileNotFoundError:
        d_tmp = monthly_water_balance(year)
        d_prev = np.full_like(d_tmp.values, np.nan)

    d_curr = monthly_water_balance(year)
    d_curr_np = d_curr.values
    nlat, nlon = d_curr_np.shape[1], d_curr_np.shape[2]

    d_24 = np.concatenate([d_prev, d_curr_np], axis=0)  # (24, nlat, nlon)

    accum = np.full((12, nlat, nlon), np.nan)
    for m in range(12):
        t = 12 + m
        if t - k + 1 >= 0:
            window = d_24[t - k + 1 : t + 1, :, :]
            if not np.all(np.isnan(window)):
                accum[m, :, :] = window.sum(axis=0)

    # Retrieve fitted parameters.
    alpha_arr = params["ll_alpha"].values  # (12, nlat, nlon)
    beta_arr = params["ll_beta"].values
    gamma_arr = params["ll_gamma"].values

    from scipy.stats import fisk  # noqa: PLC0415

    spei_np = np.full_like(accum, np.nan)

    for m in range(12):
        x = accum[m, :, :]
        a = alpha_arr[m, :, :]
        b = beta_arr[m, :, :]
        g = gamma_arr[m, :, :]

        valid_mask = np.isfinite(a) & np.isfinite(b) & np.isfinite(g) & np.isfinite(x)
        # Additional guard: x - gamma must be > 0 for the log-logistic CDF.
        valid_mask &= (x - g) > 0

        h = np.full(x.shape, np.nan)
        xv = x[valid_mask]
        av = a[valid_mask]
        bv = b[valid_mask]
        gv = g[valid_mask]

        # F(x) = fisk.cdf(x - gamma, c=beta, scale=alpha)
        hv = fisk.cdf(xv - gv, c=bv, scale=av)
        hv = np.clip(hv, 1e-6, 1.0 - 1e-6)
        h[valid_mask] = hv

        spei_np[m, :, :] = stats.norm.ppf(h)

    months = np.arange(1, 13)
    spei_da = xr.DataArray(
        spei_np,
        dims=["month", "lat", "lon"],
        coords={
            "month": months,
            "lat": params.lat.values,
            "lon": params.lon.values,
        },
    )
    spei_da.attrs["units"] = "dimensionless"
    spei_da.attrs["long_name"] = f"SPEI-{k}"
    spei_da.attrs["k_months"] = k
    spei_da.attrs["year"] = year
    return spei_da


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "RAIN_DRY_THRESHOLD",
    "SPI_SCALES",
    "SPI_BASELINE_START",
    "SPI_BASELINE_END",
    "monthly_rain",
    "fit_spi_params",
    "spi_for_year",
    "cdd_growing_season",
    # SPEI
    "EVAP_BASELINE_START",
    "EVAP_BASELINE_END",
    "SPEI_SCALES",
    "monthly_pet",
    "monthly_water_balance",
    "fit_spei_params",
    "spei_for_year",
]
