"""
src/processing/yield_stats.py — ABARES region-yield EDA statistics (Phase 03, s03).

Loads the ABARES per-region observed yields (`data/processed/abares/<crop>.csv`),
applies each crop's reliable-yield window (wheat/barley 1990+, canola 1994+; RSE
gate, scope v5.1 §3.3), and computes per-region descriptive statistics for the
Phase 03 yield EDA: level, OLS trend, dispersion (CV and *detrended* CV, which
isolates year-to-year variability from the trend), lower-tail risk (10th
percentile and worst-year relative to the median), and survey reliability
(median production RSE).

Discipline (decision gate ② = diagnostic-only): the survey RSE is reported as a
data-quality caveat, NOT used to weight the descriptive statistics; inverse-RSE
weighting is deferred to the Phase 06 regression models. Regions with fewer than
`MIN_YEARS` reliable years (marginal High-Rainfall croppers) are flagged rather
than silently mixed in.

All statistics are descriptive; inferential trend / return-period testing is
Pillar 2 (Phase 05) and Pillar 3 (Phase 06).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.paths import DATA_PROCESSED, TABLES_DIR

ABARES_DIR = DATA_PROCESSED / "abares"
REGION_MAPPING_CSV = DATA_PROCESSED / "region_mapping.csv"
BROADACRE_ZONES = ("Wheat Sheep", "High Rainfall")
COMMODITIES = ("wheat", "barley", "canola")

# Reliable-yield windows (scope v5.1 §3.3).
RELIABLE_YIELD_START = {"wheat": 1990, "barley": 1990, "canola": 1994}

# A region needs at least this many reliable years for dispersion statistics.
MIN_YEARS = 10
# Production RSE (%) above which a region-year is flagged low-reliability (for
# figure caveats only; not used to weight statistics — gate ② = diagnostic-only).
HIGH_RSE = 30.0

SUMMARY_TABLE = "s03_yield_region_summary.csv"


def broadacre_region_names() -> set[str]:
    """The 20 broadacre (Wheat-Sheep / High-Rainfall) region names."""
    rm = pd.read_csv(REGION_MAPPING_CSV, dtype={"aagis_code": str})
    return set(rm[rm.zone.isin(BROADACRE_ZONES)].region_name)


def load_yield(
    commodity: str,
    *,
    reliable_only: bool = True,
    broadacre_only: bool = True,
) -> pd.DataFrame:
    """Load one commodity's per-region yields, reliable-window & broadacre filtered."""
    df = pd.read_csv(ABARES_DIR / f"{commodity}.csv")
    if reliable_only:
        df = df[df.year >= RELIABLE_YIELD_START[commodity]]
    df = df.dropna(subset=["yield_t_ha"]).copy()
    if broadacre_only:
        df = df[df.region.isin(broadacre_region_names())]
    df["commodity"] = commodity
    return df.reset_index(drop=True)


def ols_slope_per_decade(years: np.ndarray, values: np.ndarray) -> float:
    """OLS slope of values on year, expressed per decade (NaN if < 3 points)."""
    years = np.asarray(years, float)
    values = np.asarray(values, float)
    if len(years) < 3:
        return np.nan
    return float(np.polyfit(years, values, 1)[0] * 10.0)


def detrended_cv(years: np.ndarray, values: np.ndarray) -> float:
    """
    Std of the OLS residuals divided by the mean — year-to-year variability with
    the linear trend removed (NaN if < 3 points or zero mean).
    """
    years = np.asarray(years, float)
    values = np.asarray(values, float)
    mean = values.mean()
    if len(years) < 3 or mean == 0:
        return np.nan
    resid = values - np.polyval(np.polyfit(years, values, 1), years)
    return float(np.std(resid) / mean)


def region_yield_summary(commodity: str | None = None) -> pd.DataFrame:
    """Per-region, per-commodity descriptive yield statistics."""
    commodities = [commodity] if commodity else list(COMMODITIES)
    rows = []
    for c in commodities:
        df = load_yield(c)
        for region, g in df.groupby("region", sort=True):
            y = g.year.to_numpy(float)
            v = g.yield_t_ha.to_numpy(float)
            mean = float(v.mean())
            median = float(np.median(v))
            rows.append(
                {
                    "commodity": c,
                    "region": region,
                    "n_years": int(len(g)),
                    "mean_yield": mean,
                    "median_yield": median,
                    "trend_t_ha_decade": ols_slope_per_decade(y, v),
                    "cv": float(v.std() / mean) if mean else np.nan,
                    "detrended_cv": detrended_cv(y, v),
                    "p10_yield": float(np.percentile(v, 10)),
                    "p10_over_median": (
                        float(np.percentile(v, 10) / median) if median else np.nan
                    ),
                    "worst_over_median": (
                        float(v.min() / median) if median else np.nan
                    ),
                    "median_prod_rse": float(g.production_rse.median()),
                    "adequate": bool(len(g) >= MIN_YEARS),
                }
            )
    return pd.DataFrame(rows)


def write_summary(df: pd.DataFrame, filename: str = SUMMARY_TABLE) -> Path:
    """Atomic (.part -> rename) write of the yield summary to outputs/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / filename
    tmp = out.with_suffix(".csv.part")
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, out)
    return out


def load_summary(path: str | Path | None = None) -> pd.DataFrame:
    """Load the persisted yield summary table."""
    p = TABLES_DIR / SUMMARY_TABLE if path is None else Path(path)
    return pd.read_csv(p)


__all__ = [
    "ABARES_DIR",
    "COMMODITIES",
    "RELIABLE_YIELD_START",
    "MIN_YEARS",
    "HIGH_RSE",
    "SUMMARY_TABLE",
    "broadacre_region_names",
    "load_yield",
    "ols_slope_per_decade",
    "detrended_cv",
    "region_yield_summary",
    "write_summary",
    "load_summary",
]
