"""
src/indicators/frost — Frost-day indicator.

Computes growing-season frost-day counts per SILO grid cell.

Definition
----------
ETCCDI (Tank et al. 2009) standard:  frost day = day on which tmin < 2°C.

Threshold: 2°C (not 0°C) to account for radiative frost effects on crops
(Nix 1975; see also BoM agricultural climate products).

Reference
---------
Tank, A.M.G.K. et al. (2009). Guidelines on Analysis of Extremes in a
    Changing Climate in Support of Informed Decisions for Adaptation.
    World Meteorological Organization, WCDMP-72.

Scope
-----
Frost days are counted within the configured growing-season window
(GROWING_WINDOWS from _base).  Only cropping-mask cells are exposed via
the grid script; the indicator function itself operates on all grid cells.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from src.indicators._base import (
    GROWING_WINDOWS,
    GrowingWindow,
    TMIN,
    load_silo_year,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FROST_THRESHOLD_C: float = 2.0  # °C  (ETCCDI + crop-protection standard)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def frost_days_growing_season(
    year: int,
    window: "GrowingWindow | None" = None,
    threshold: float = FROST_THRESHOLD_C,
) -> xr.DataArray:
    """Count growing-season frost days (tmin < threshold) for one season.

    Parameters
    ----------
    year:
        Season-start year.  For cross-year windows the function loads
        ``year`` and ``year + 1``; for same-year windows only ``year``.
    window:
        GrowingWindow from _base.GROWING_WINDOWS.  Defaults to
        ``GROWING_WINDOWS["southern_winter"]`` (April–October, no cross-year).
    threshold:
        Frost threshold in °C.  Defaults to FROST_THRESHOLD_C (2°C).

    Returns
    -------
    xr.DataArray of shape (lat, lon).
        Integer count (stored as float to allow NaN) of frost days within
        the growing-season window.  NaN for cells where all tmin values
        were NaN (ocean / outside mask).

    Raises
    ------
    FileNotFoundError
        Propagated from load_silo_year when the SILO NetCDF is missing.
    """
    if window is None:
        window = GROWING_WINDOWS["southern_winter"]

    # ── Load tmin for the season year(s) ──────────────────────────────────
    tmin_curr = load_silo_year(TMIN, year)

    if window.cross_year:
        tmin_next = load_silo_year(TMIN, year + 1)
        tmin_full = xr.concat([tmin_curr, tmin_next], dim="time")
    else:
        tmin_full = tmin_curr

    # ── Season mask ────────────────────────────────────────────────────────
    months_yr0 = window.months_yr0
    months_yr1 = window.months_yr1

    if window.cross_year:
        mask_yr0 = tmin_full.time.dt.year == year
        mask_yr1 = tmin_full.time.dt.year == year + 1
        in_season = (mask_yr0 & tmin_full.time.dt.month.isin(months_yr0)) | (
            mask_yr1 & tmin_full.time.dt.month.isin(months_yr1)
        )
    else:
        in_season = tmin_full.time.dt.month.isin(months_yr0)

    tmin_season = tmin_full.sel(time=in_season)

    # ── Count frost days ───────────────────────────────────────────────────
    frost_mask = tmin_season < threshold  # (time, lat, lon) bool
    frost_count = frost_mask.sum(dim="time", skipna=True).astype(float)

    # Restore NaN for fully-NaN cells (ocean / outside mask).
    all_nan = np.all(np.isnan(tmin_season.values), axis=0)
    frost_count.values[all_nan] = np.nan

    # ── Attributes ────────────────────────────────────────────────────────
    frost_count.attrs["units"] = "days"
    frost_count.attrs["long_name"] = (
        f"Frost days (tmin < {threshold}°C) — {window.label} — {year}"
    )
    frost_count.attrs["threshold_degC"] = threshold
    frost_count.attrs["season_year"] = year
    frost_count.attrs["season_label"] = window.label
    frost_count.attrs["definition"] = "ETCCDI frost day adapted (Tank et al. 2009)"

    return frost_count
