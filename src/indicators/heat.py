"""
src/indicators/heat.py — Heat-related climate indicators (Phase 04).

Implements:
  - GDD (Growing Degree Days): daily heat accumulation above a base
    temperature, accumulated over the growing season.  Standard agronomy
    definition used for Australian broadacre cereals and oilseeds.

Planned (Phase 04 later steps):
  - EHF (Excess Heat Factor): Nairn & Fawcett (2015) heatwave indicator.

All indicators are computed at SILO grid resolution (individual cell
time-series), consistent with scope §3.6 and §5.1.  Region-level
aggregation and distributional summaries are handled by the calling
script (phase04_s01_gdd_grid.py), not here.

References
----------
Growing Degree Days:
  - McMaster, G.S. & Wilhelm, W.W. (1997). Growing degree-days: one equation,
    two interpretations. Agricultural and Forest Meteorology, 87(4), 291-300.
  - GRDC (2020). Wheat growing guide — thermal time requirements.
    https://grdc.com.au/

Base temperatures (Tbase) used:
  - Wheat / barley / canola: 0 °C  (widely used Australian standard;
    McMaster & Wilhelm; GRDC guides).
  - Alternative Tbase 5 °C and 10 °C are accepted as parameters so
    sensitivity can be explored.

EHF reference (planned):
  - Nairn, J.R. & Fawcett, R.G. (2015). The excess heat factor: a metric
    for heatwave intensity and its use in classifying heatwave severity.
    International Journal of Environmental Research and Public Health, 12(1).
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from src.indicators._base import (
    TMAX,
    TMIN,
    GrowingWindow,
    load_silo_year,
)

# ---------------------------------------------------------------------------
# EHF — Excess Heat Factor
# ---------------------------------------------------------------------------
#
# Nairn, J.R. & Fawcett, R.G. (2015). The excess heat factor: a metric for
# heatwave intensity and its use in classifying heatwave severity.
# International Journal of Environmental Research and Public Health, 12(1).
#
# BoM operational definition (adapted):
#   T_mean_daily = (tmax + tmin) / 2
#   T3day_i      = (T_mean_i + T_mean_(i-1) + T_mean_(i-2)) / 3
#   T30day_i     = mean of T_mean over the preceding 30 days (days i-32..i-3)
#   T90_m        = 90th percentile of daily T_mean over the climatological
#                  baseline per calendar month (adaptive override: annual T90
#                  to avoid RAM explosion loading full grid × 30yr daily;
#                  see PROJECT_LOG Phase 04 Step 04a).
#
#   EHI_sig   = T3day − T90           (excess above climatological threshold)
#   EHI_accum = T3day − T30day        (excess above recent background)
#   EHF       = max(1, EHI_accum) × EHI_sig
#             = positive when EHI_sig > 0 and weighted by accumulation
#
# Adaptive override (PROJECT_WORKFLOW §4.2):
#   BoM uses a smoothed daily-calendar 90th percentile (15-day window per
#   calendar day).  For this project the T90 is computed as the annual 90th
#   percentile of daily T_mean per grid cell over the WMO 1961-1990 baseline.
#   Rationale: (1) identical baseline to SPI/GDD; (2) avoids loading 30×365
#   daily arrays for the full SILO grid simultaneously; (3) the annual T90
#   is a standard published threshold in Australian heatwave literature
#   (Fischer & Knutti 2015; Perkins & Alexander 2013).
#   This override is logged in PROJECT_LOG Phase 04 Step 04a.

EHF_BASELINE_START: int = 1961
EHF_BASELINE_END: int = 1990
EHF_T90_PERCENTILE: float = 90.0

# ---------------------------------------------------------------------------
# GDD base temperatures
# ---------------------------------------------------------------------------

TBASE_CEREALS: float = 0.0  # °C — wheat, barley (Australian standard)
TBASE_CANOLA: float = 0.0  # °C — canola (same floor; literature varies 0–5)
TBASE_DEFAULT: float = TBASE_CEREALS


# ---------------------------------------------------------------------------
# Daily GDD computation
# ---------------------------------------------------------------------------


def daily_gdd(
    tmax: xr.DataArray,
    tmin: xr.DataArray,
    tbase: float = TBASE_DEFAULT,
    tcap: float | None = None,
) -> xr.DataArray:
    """Compute daily Growing Degree Days at each grid cell.

    GDD_daily = max(T_mean - Tbase, 0)
    where T_mean = (tmax + tmin) / 2.

    An optional upper cap (tcap) can be applied: temperatures above tcap are
    capped before averaging.  Not applied by default (tcap=None).

    Parameters
    ----------
    tmax:
        Daily maximum temperature DataArray (°C), dims (time, lat, lon).
    tmin:
        Daily minimum temperature DataArray (°C), dims (time, lat, lon).
    tbase:
        Base temperature below which no heat accumulation occurs (°C).
        Default 0.0 °C (Australian broadacre cereal standard).
    tcap:
        Optional upper temperature cap (°C).  If provided, tmax and tmin
        values exceeding tcap are replaced by tcap before the mean is taken.
        Default None (no cap applied).

    Returns
    -------
    xr.DataArray of daily GDD values >= 0, same dims as input.
    """
    if tcap is not None:
        tmax = tmax.clip(max=tcap)
        tmin = tmin.clip(max=tcap)

    t_mean = (tmax + tmin) / 2.0
    gdd = (t_mean - tbase).clip(min=0.0)
    gdd.attrs["units"] = "°C·day"
    gdd.attrs["long_name"] = "Daily Growing Degree Days"
    gdd.attrs["tbase"] = tbase
    if tcap is not None:
        gdd.attrs["tcap"] = tcap
    return gdd


# ---------------------------------------------------------------------------
# Growing-season GDD accumulation for one year
# ---------------------------------------------------------------------------


def gdd_growing_season(
    year: int,
    window: GrowingWindow,
    tbase: float = TBASE_DEFAULT,
    tcap: float | None = None,
) -> xr.DataArray:
    """Compute accumulated GDD over the growing season for one year.

    For seasons that do NOT cross a year boundary (cross_year=False), this
    function opens the single SILO year file, subsets to the window months,
    and sums daily GDD.

    For seasons that cross a year boundary (cross_year=True, e.g. QLD
    Sep–Feb), it opens two consecutive SILO files (year and year+1) and
    concatenates before subsetting.

    Convention for cross-year seasons:
        ``year`` refers to the START of the season (e.g. year=2000 →
        Sep 2000 – Feb 2001).  Results are labelled by the start year.

    Parameters
    ----------
    year:
        Calendar year of the season start.
    window:
        GrowingWindow named-tuple (from _base.GROWING_WINDOWS or
        _base.get_growing_window()).
    tbase, tcap:
        Passed through to daily_gdd().

    Returns
    -------
    xr.DataArray of shape (lat, lon) with accumulated GDD for the season.
    Masked cells (outside the cropping area) remain NaN.
    """
    # Load tmax and tmin for the primary year.
    tmax_yr0 = load_silo_year(TMAX, year)
    tmin_yr0 = load_silo_year(TMIN, year)

    if window.cross_year:
        # Load the following year as well.
        tmax_yr1 = load_silo_year(TMAX, year + 1)
        tmin_yr1 = load_silo_year(TMIN, year + 1)
        tmax_full = xr.concat([tmax_yr0, tmax_yr1], dim="time")
        tmin_full = xr.concat([tmin_yr0, tmin_yr1], dim="time")
    else:
        tmax_full = tmax_yr0
        tmin_full = tmin_yr0

    # Compute daily GDD over the full (possibly two-year) time axis.
    gdd_daily = daily_gdd(tmax_full, tmin_full, tbase=tbase, tcap=tcap)

    # Subset to the growing-season months.
    months_yr0 = window.months_yr0
    months_yr1 = window.months_yr1

    if window.cross_year:
        # Select months in year (yr0 months) and months in year+1 (yr1 months).
        mask_yr0 = gdd_daily.time.dt.year == year
        mask_yr1 = gdd_daily.time.dt.year == year + 1
        in_season = (mask_yr0 & gdd_daily.time.dt.month.isin(months_yr0)) | (
            mask_yr1 & gdd_daily.time.dt.month.isin(months_yr1)
        )
    else:
        in_season = gdd_daily.time.dt.month.isin(months_yr0)

    gdd_season = gdd_daily.sel(time=in_season).sum(dim="time", skipna=False)

    # Attach metadata.
    gdd_season.attrs["units"] = "°C·day"
    gdd_season.attrs["long_name"] = f"Accumulated GDD ({window.label}) — {year}"
    gdd_season.attrs["tbase"] = tbase
    gdd_season.attrs["season_year"] = year
    gdd_season.attrs["season_label"] = window.label
    if tcap is not None:
        gdd_season.attrs["tcap"] = tcap

    return gdd_season


# ---------------------------------------------------------------------------
# Cell-level GDD time-series (all years)
# ---------------------------------------------------------------------------


def gdd_timeseries_cells(
    cells,
    years: list[int],
    window: GrowingWindow,
    tbase: float = TBASE_DEFAULT,
    tcap: float | None = None,
):
    """Compute seasonal GDD for each active cropping cell, all years.

    This is the primary function called by the orchestration script.  It
    iterates over years, calls gdd_growing_season(), and samples the result
    at the active cell lat/lon indices.

    Parameters
    ----------
    cells:
        DataFrame from _base.get_cropping_cells() with columns
        [lat, lon, aagis_code, lat_idx, lon_idx].
    years:
        List of calendar years to process.
    window:
        GrowingWindow (normally the southern-winter window for most regions;
        QLD regions should be handled separately if mixed windows are needed).
    tbase, tcap:
        Passed through to gdd_growing_season().

    Returns
    -------
    DataFrame with columns [year, lat, lon, aagis_code, gdd_season].
    One row per (year × cell).
    """
    import pandas as pd  # noqa: PLC0415 — local import to keep module lightweight

    records = []
    for year in years:
        try:
            da = gdd_growing_season(year, window, tbase=tbase, tcap=tcap)
        except FileNotFoundError as exc:
            import warnings

            warnings.warn(str(exc), stacklevel=2)
            continue

        # Sample the DataArray at cell lat/lon values.
        # Use .sel with coordinate values (robust to axis ordering — same
        # approach as silo_region_aggregation.resolve_cell_grid_indices).
        lat_vals = xr.DataArray(cells["lat"].values, dims="cell")
        lon_vals = xr.DataArray(cells["lon"].values, dims="cell")
        sampled = da.sel(lat=lat_vals, lon=lon_vals, method="nearest").values

        df_year = cells[["lat", "lon", "aagis_code"]].copy()
        df_year["year"] = year
        df_year["gdd_season"] = sampled
        records.append(df_year)

    if not records:
        return pd.DataFrame(columns=["year", "lat", "lon", "aagis_code", "gdd_season"])

    result = pd.concat(records, ignore_index=True)
    result["year"] = result["year"].astype(int)
    result["gdd_season"] = result["gdd_season"].astype(float)
    return result[["year", "lat", "lon", "aagis_code", "gdd_season"]]


def compute_t90_baseline(
    baseline_years: list[int],
) -> xr.DataArray:
    """Compute the climatological 90th-percentile daily Tmean per grid cell.

    Adaptive override: uses the annual 90th percentile of daily T_mean pooled
    over all baseline years (not a per-calendar-day smoothed percentile).
    See module-level comment and PROJECT_LOG Phase 04 Step 04a.

    Parameters
    ----------
    baseline_years:
        List of years for the baseline (e.g. list(range(1961, 1991))).

    Returns
    -------
    xr.DataArray with dims (lat, lon).  Values are the 90th percentile of
    daily T_mean (°C) over the pooled baseline period.
    """
    lat = lon = None
    annual_means: list[np.ndarray] = []

    for yr in baseline_years:
        tmax_da = load_silo_year(TMAX, yr)
        tmin_da = load_silo_year(TMIN, yr)
        tmean = ((tmax_da + tmin_da) / 2.0).values  # (n_days, nlat, nlon)
        if lat is None:
            lat = tmax_da.lat.values
            lon = tmax_da.lon.values
        annual_means.append(tmean)

    all_days = np.concatenate(annual_means, axis=0)  # (n_baseline_days, nlat, nlon)
    t90 = np.nanpercentile(all_days, EHF_T90_PERCENTILE, axis=0)  # (nlat, nlon)

    t90_da = xr.DataArray(
        t90,
        dims=["lat", "lon"],
        coords={"lat": lat, "lon": lon},
    )
    t90_da.attrs["units"] = "°C"
    t90_da.attrs["long_name"] = "90th percentile daily Tmean (EHF threshold)"
    t90_da.attrs["percentile"] = EHF_T90_PERCENTILE
    t90_da.attrs["baseline_start"] = baseline_years[0]
    t90_da.attrs["baseline_end"] = baseline_years[-1]
    t90_da.attrs["baseline_note"] = (
        "Annual T90 adaptive override: pooled over baseline years per grid cell"
    )
    return t90_da


def ehf_for_year(
    year: int,
    t90: xr.DataArray,
) -> xr.DataArray:
    """Compute daily EHF for all days of a single year.

    Parameters
    ----------
    year:
        Calendar year to compute EHF for (1961–2024).
    t90:
        xr.DataArray of shape (lat, lon) produced by compute_t90_baseline().

    Returns
    -------
    xr.DataArray with dims (time, lat, lon), daily frequency.
        EHF > 0 indicates a heatwave day.  EHF ≤ 0 is stored as 0.0.
        Days 1–32 of each year are NaN (insufficient warm-up for T30day).
    """
    tmax_yr = load_silo_year(TMAX, year)
    tmin_yr = load_silo_year(TMIN, year)
    tmean_yr = ((tmax_yr + tmin_yr) / 2.0).values  # (n_days, nlat, nlon)
    times_yr = tmax_yr.time.values
    lat = tmax_yr.lat.values
    lon = tmax_yr.lon.values

    # Prepend previous year for 30-day background warm-up.
    try:
        tmax_prev = load_silo_year(TMAX, year - 1)
        tmin_prev = load_silo_year(TMIN, year - 1)
        tmean_prev = ((tmax_prev + tmin_prev) / 2.0).values
    except FileNotFoundError:
        tmean_prev = np.full_like(tmean_yr, np.nan)

    tmean_all = np.concatenate([tmean_prev, tmean_yr], axis=0)
    n_prev = tmean_prev.shape[0]
    n_curr = tmean_yr.shape[0]
    t90_np = t90.values  # (nlat, nlon)

    ehf_np = np.full((n_curr, t90_np.shape[0], t90_np.shape[1]), np.nan)

    for i_curr in range(n_curr):
        i_all = n_prev + i_curr

        # T3day: 3-day mean ending today (requires at least 2 prior days).
        if i_all < 2:
            continue
        t3_window = tmean_all[i_all - 2 : i_all + 1, :, :]
        if np.all(np.isnan(t3_window)):
            continue
        t3day = np.nanmean(t3_window, axis=0)

        # EHI_sig = T3day − T90.
        ehi_sig = t3day - t90_np

        if not np.any(ehi_sig > 0):
            ehf_np[i_curr, :, :] = 0.0
            continue

        # T30day: mean of 30 days lagged 3 days (days i-32..i-3).
        t30_start = i_all - 32
        t30_end = i_all - 2
        if t30_start < 0:
            # Insufficient warm-up — leave NaN.
            continue
        t30_window = tmean_all[t30_start:t30_end, :, :]
        t30day = np.nanmean(t30_window, axis=0)

        # EHI_accum = T3day − T30day.
        ehi_accum = t3day - t30day

        # EHF = max(1, EHI_accum) × EHI_sig; zero where EHI_sig ≤ 0.
        ehf = np.where(ehi_sig > 0, np.maximum(1.0, ehi_accum) * ehi_sig, 0.0)
        ehf_np[i_curr, :, :] = ehf

    ehf_da = xr.DataArray(
        ehf_np,
        dims=["time", "lat", "lon"],
        coords={"time": times_yr, "lat": lat, "lon": lon},
    )
    ehf_da.attrs["units"] = "°C²"
    ehf_da.attrs["long_name"] = "Excess Heat Factor (Nairn & Fawcett 2015)"
    ehf_da.attrs["year"] = year
    return ehf_da


def ehf_season_summary(
    year: int,
    t90: xr.DataArray,
    window: GrowingWindow,
) -> xr.DataArray:
    """Compute growing-season heatwave-day count (EHF > 0) for one year.

    Parameters
    ----------
    year:
        Season start year (convention: same as gdd_growing_season).
    t90:
        Output of compute_t90_baseline().
    window:
        GrowingWindow defining the season.

    Returns
    -------
    xr.DataArray of shape (lat, lon) — count of heatwave days in season.
    """
    ehf_curr = ehf_for_year(year, t90)

    if window.cross_year:
        ehf_next = ehf_for_year(year + 1, t90)
        ehf_full = xr.concat([ehf_curr, ehf_next], dim="time")
    else:
        ehf_full = ehf_curr

    if window.cross_year:
        mask_yr0 = ehf_full.time.dt.year == year
        mask_yr1 = ehf_full.time.dt.year == year + 1
        in_season = (mask_yr0 & ehf_full.time.dt.month.isin(window.months_yr0)) | (
            mask_yr1 & ehf_full.time.dt.month.isin(window.months_yr1)
        )
    else:
        in_season = ehf_full.time.dt.month.isin(window.months_yr0)

    ehf_season = ehf_full.sel(time=in_season)

    # Count heatwave days (EHF > 0).
    hw_days = (ehf_season > 0).sum(dim="time", skipna=True).astype(float)

    # Restore NaN for fully-masked cells (all NaN across season).
    all_nan = np.all(np.isnan(ehf_season.values), axis=0)
    hw_days.values[all_nan] = np.nan

    hw_days.attrs["units"] = "days"
    hw_days.attrs["long_name"] = f"Heatwave days (EHF > 0) — {window.label} — {year}"
    hw_days.attrs["season_year"] = year
    hw_days.attrs["season_label"] = window.label
    return hw_days


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TBASE_CEREALS",
    "TBASE_CANOLA",
    "TBASE_DEFAULT",
    "daily_gdd",
    "gdd_growing_season",
    "gdd_timeseries_cells",
    # EHF
    "EHF_BASELINE_START",
    "EHF_BASELINE_END",
    "EHF_T90_PERCENTILE",
    "compute_t90_baseline",
    "ehf_for_year",
    "ehf_season_summary",
]
