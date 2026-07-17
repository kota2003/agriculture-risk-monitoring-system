"""
src/processing/climate_consistency.py — grid-vs-region SILO consistency checks.

Phase 02, Step 04b (Task C, part 2). Confirms that the area-weighted SILO
region climatologies produced by s04a reproduce expected regional climate
(scope v5 §4.2, §6.2). Per the Phase 02 decision criteria, INTERNAL
consistency (fully reproducible from committed code + regenerable data) is the
primary, load-bearing check; an EXTERNAL comparison against published BoM
station normals (observed data, cited) is a supporting plausibility check.

Internal checks (physically grounded, quantitative):
  1. Coverage: every broadacre (Wheat-Sheep / High-Rainfall) region present
     for all six variables; no NaN; no spurious zero rainfall.
  2. Temperature-latitude structure: region mean tmax (and tmin) correlate
     strongly with latitude (further south -> cooler). A grid flip or
     mis-aggregation destroys this.
  3. Rainfall seasonality regime: south-western / southern Mediterranean
     regions are winter-dominant; subtropical / monsoonal northern regions
     are summer-dominant. Encodes the continental winter->summer rainfall
     gradient.

External check (secondary, observed, cited):
  Region area-weighted means are compared to representative in-region BoM
  station normals. A region spans a climate gradient, so the region mean is
  expected to sit near / within the spread of representative stations, not to
  equal any single one; temperature (spatially smooth) is the tighter test.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.io_utils import read_csv_safe
from src.paths import DATA_PROCESSED

# ---------------------------------------------------------------------------
# Locations & constants
# ---------------------------------------------------------------------------

REGION_MEANS_DIR: Path = DATA_PROCESSED / "silo_region_means"
ANNUAL_CSV: Path = REGION_MEANS_DIR / "annual_1991_2020.csv"
MONTHLY_CSV: Path = REGION_MEANS_DIR / "monthly_climatology_1991_2020.csv"
CELL_REGION_MAP_PARQUET: Path = DATA_PROCESSED / "silo_cell_region_map.parquet"

BROADACRE_ZONES: tuple[str, ...] = ("Wheat Sheep", "High Rainfall")
WINTER_MONTHS: tuple[int, ...] = (5, 6, 7, 8)  # May-Aug
SUMMER_MONTHS: tuple[int, ...] = (11, 12, 1, 2)  # Nov-Feb

# Expected rainfall-seasonality regime by climate zone (domain knowledge).
WINTER_DOMINANT_CODES: tuple[str, ...] = ("521", "522", "531", "421")
SUMMER_DOMINANT_CODES: tuple[str, ...] = ("322", "331", "332", "121", "713", "714")

# Consistency thresholds.
TMAX_LAT_CORR_MIN: float = 0.85  # |corr(lat, tmax)| lower bound
TMIN_LAT_CORR_MIN: float = 0.80

# External BoM reference anchors — long-term normals from BoM "Climate
# statistics for Australian locations" (observed; secondary plausibility only).
# (aagis_code, region_name, station, bom_url, annual_rain_mm, tmax_c, tmin_c)
REFERENCE_STATIONS: list[tuple[str, str, str, str, float, float, float]] = [
    (
        "221",
        "VIC Mallee",
        "Mildura (076031)",
        "https://www.bom.gov.au/climate/averages/tables/cw_076031.shtml",
        278.0,
        23.8,
        10.4,
    ),
    (
        "521",
        "WA Central and Southern Wheat Belt",
        "Merredin (010092)",
        "http://www.bom.gov.au/climate/averages/tables/cw_010092.shtml",
        310.0,
        25.4,
        11.5,
    ),
    (
        "123",
        "NSW Riverina",
        "Wagga Wagga (072150)",
        "https://www.bom.gov.au/climate/averages/tables/cw_072150_All.shtml",
        614.0,
        22.5,
        9.4,
    ),
]

# External tolerances: temperature is spatially smooth (tight); rainfall
# varies across a region relative to a point station (loose).
TMAX_ABS_TOL_C: float = 3.0
RAIN_REL_TOL: float = 0.45


# ---------------------------------------------------------------------------
# Loading / feature construction
# ---------------------------------------------------------------------------


def load_region_annual(annual_csv: str | Path = ANNUAL_CSV) -> pd.DataFrame:
    """
    Region x variable table of annual means (averaged over the year axis).

    Returns
    -------
    pandas.DataFrame
        Indexed by ``aagis_code``; columns are the SILO variables; plus a
        ``region_name`` column.
    """
    df = read_csv_safe(annual_csv, na_values=[""])
    df["aagis_code"] = df["aagis_code"].astype(str).str.strip()
    per = df.groupby(["aagis_code", "region_name", "variable"])["value"].mean()
    wide = per.unstack("variable")
    wide = wide.reset_index().set_index("aagis_code")
    return wide


def load_seasonality(monthly_csv: str | Path = MONTHLY_CSV) -> pd.DataFrame:
    """
    Per-region winter/summer rainfall share (% of annual) from the monthly
    climatology.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``aagis_code`` with ``winter_share`` and ``summer_share``.
    """
    df = read_csv_safe(monthly_csv, na_values=[""])
    df["aagis_code"] = df["aagis_code"].astype(str).str.strip()
    rain = df[df["variable"] == "daily_rain"]
    piv = rain.pivot_table(index="aagis_code", columns="month", values="value")
    annual = piv.sum(axis=1)
    winter = piv[list(WINTER_MONTHS)].sum(axis=1)
    summer = piv[list(SUMMER_MONTHS)].sum(axis=1)
    return pd.DataFrame(
        {
            "winter_share": 100 * winter / annual,
            "summer_share": 100 * summer / annual,
        }
    )


def load_region_latitude(
    cell_map: str | Path = CELL_REGION_MAP_PARQUET,
) -> pd.Series:
    """Area(cos-lat)-weighted mean latitude per region, from the cell map."""
    df = pd.read_parquet(cell_map)
    df["aagis_code"] = df["aagis_code"].astype(str).str.strip()

    def _wmean(g: pd.DataFrame) -> float:
        return float(np.average(g["lat"], weights=g["weight"]))

    return df.groupby("aagis_code").apply(_wmean, include_groups=False).rename("lat")


# ---------------------------------------------------------------------------
# Internal consistency
# ---------------------------------------------------------------------------


def check_internal_consistency(
    region_annual: pd.DataFrame,
    seasonality: pd.DataFrame,
    region_lat: pd.Series,
    region_zone: pd.Series,
) -> dict:
    """
    Run the internal grid-vs-region consistency battery.

    Parameters
    ----------
    region_annual : DataFrame indexed by aagis_code, variable columns.
    seasonality : DataFrame indexed by aagis_code (winter_share, summer_share).
    region_lat : Series indexed by aagis_code (mean latitude).
    region_zone : Series indexed by aagis_code (zone label).

    Returns
    -------
    dict
        ``valid`` boolean plus per-check details.
    """
    broad = region_zone[region_zone.isin(BROADACRE_ZONES)].index
    ba = region_annual.loc[region_annual.index.intersection(broad)]

    svars = ["max_temp", "min_temp", "daily_rain", "vp", "radiation", "evap_pan"]
    no_nan = bool(ba[svars].notnull().all().all())
    no_zero_rain = bool((ba["daily_rain"] > 0).all())
    coverage_ok = no_nan and no_zero_rain

    lat = region_lat.reindex(ba.index)
    tmax_corr = float(np.corrcoef(lat, ba["max_temp"])[0, 1])
    tmin_corr = float(np.corrcoef(lat, ba["min_temp"])[0, 1])
    tmax_ok = tmax_corr >= TMAX_LAT_CORR_MIN
    tmin_ok = tmin_corr >= TMIN_LAT_CORR_MIN

    seas = seasonality.reindex(region_annual.index)
    winter_fail = [
        c
        for c in WINTER_DOMINANT_CODES
        if c in seas.index
        and not (seas.loc[c, "winter_share"] > seas.loc[c, "summer_share"])
    ]
    summer_fail = [
        c
        for c in SUMMER_DOMINANT_CODES
        if c in seas.index
        and not (seas.loc[c, "summer_share"] > seas.loc[c, "winter_share"])
    ]
    seasonality_ok = not winter_fail and not summer_fail

    checks = {
        "coverage_no_nan_no_zero_rain": coverage_ok,
        "tmax_latitude_corr": tmax_ok,
        "tmin_latitude_corr": tmin_ok,
        "rainfall_seasonality_regime": seasonality_ok,
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "n_broadacre_regions": int(len(ba)),
        "tmax_lat_corr": tmax_corr,
        "tmin_lat_corr": tmin_corr,
        "winter_regime_failures": winter_fail,
        "summer_regime_failures": summer_fail,
    }


# ---------------------------------------------------------------------------
# External plausibility
# ---------------------------------------------------------------------------


def compare_to_reference(region_annual: pd.DataFrame) -> pd.DataFrame:
    """
    Compare region means to representative BoM station normals.

    Returns a tidy table with the SILO value, the BoM reference, the
    difference, and a plausibility verdict (temperature within
    ``TMAX_ABS_TOL_C``; rainfall within ``RAIN_REL_TOL``).
    """
    rows = []
    for code, region, station, url, rain_ref, tmax_ref, tmin_ref in REFERENCE_STATIONS:
        if code not in region_annual.index:
            continue
        r = region_annual.loc[code]
        tmax_ok = abs(float(r["max_temp"]) - tmax_ref) <= TMAX_ABS_TOL_C
        rain_ok = abs(float(r["daily_rain"]) - rain_ref) <= RAIN_REL_TOL * rain_ref
        rows.append(
            {
                "aagis_code": code,
                "region_name": region,
                "bom_station": station,
                "silo_rain_mm": round(float(r["daily_rain"]), 1),
                "bom_rain_mm": rain_ref,
                "silo_tmax_c": round(float(r["max_temp"]), 1),
                "bom_tmax_c": tmax_ref,
                "silo_tmin_c": round(float(r["min_temp"]), 1),
                "bom_tmin_c": tmin_ref,
                "tmax_within_3C": tmax_ok,
                "rain_within_45pct": rain_ok,
                "bom_url": url,
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "REGION_MEANS_DIR",
    "ANNUAL_CSV",
    "MONTHLY_CSV",
    "CELL_REGION_MAP_PARQUET",
    "BROADACRE_ZONES",
    "WINTER_MONTHS",
    "SUMMER_MONTHS",
    "WINTER_DOMINANT_CODES",
    "SUMMER_DOMINANT_CODES",
    "REFERENCE_STATIONS",
    "load_region_annual",
    "load_seasonality",
    "load_region_latitude",
    "check_internal_consistency",
    "compare_to_reference",
]
