"""
src/processing/climate_yield.py — climate × yield linkage EDA (Phase 03, s04).

Joins the §1 full-record climate region series (annual rainfall, max temperature)
to the §2 observed yields at region-year, and quantifies — descriptively — how
climate relates to yield:

  * within-region, year-to-year: correlation of DETRENDED yield with detrended
    rainfall and detrended max temperature (both series are detrended per region
    so the strong yield trend and the climate trend do not manufacture a spurious
    correlation);
  * across regions: rainfall interannual variability (CV) vs yield variability
    (detrended CV) — does a more climate-variable region yield more variably?
  * historical-event sanity (decision gate ③ = A+): mean detrended-yield residual
    in known drought / heat years vs non-event years.

All statistics are descriptive. Formal, cross-pillar historical-event validation
is Phase 09; inferential climate–yield modelling is Pillar 3 (Phase 06). A key
EDA finding this module supports: annual, region-aggregated climate is a weak
year-to-year predictor of yield, motivating the growing-season / water-balance /
heat indicators of Pillar 1 (Phase 04).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.paths import DATA_PROCESSED, TABLES_DIR
from src.processing.silo_climatology import load_annual_full_record
from src.processing.yield_stats import load_yield, region_yield_summary

REGION_MAPPING_CSV = DATA_PROCESSED / "region_mapping.csv"

# Known high-impact events (scope §5.6.1 / phase02 handoff Task H). Inclusive years.
EVENTS: dict[str, tuple[int, ...]] = {
    "Millennium Drought (2001-2009)": tuple(range(2001, 2010)),
    "2018 drought": (2018, 2019),
    "2013/2017 heat": (2013, 2017),
}

LINKAGE_TABLE = "s04_climate_yield_linkage.csv"
EVENT_TABLE = "s04_event_year_anomaly.csv"


def _name_to_code() -> dict[str, str]:
    rm = pd.read_csv(REGION_MAPPING_CSV, dtype={"aagis_code": str})
    return dict(zip(rm.region_name, rm.aagis_code))


def load_climate_annual() -> pd.DataFrame:
    """Region-year annual rainfall (mm) and max temperature (°C), wide form."""
    ann = load_annual_full_record()
    wide = (
        ann[ann.variable.isin(["daily_rain", "max_temp"])]
        .pivot_table(index=["aagis_code", "year"], columns="variable", values="value")
        .reset_index()
        .rename(columns={"daily_rain": "rain", "max_temp": "tmax"})
    )
    wide.columns.name = None
    return wide


def _detrend(years, values) -> np.ndarray:
    years = np.asarray(years, float)
    values = np.asarray(values, float)
    if len(years) < 3:
        return np.full(len(values), np.nan)
    return values - np.polyval(np.polyfit(years, values, 1), years)


def _corr(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 4 or np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def build_panel(commodity: str, *, adequate_only: bool = True) -> pd.DataFrame:
    """Region-year yield × climate panel with per-region detrended residuals."""
    y = load_yield(commodity)
    y = y.assign(aagis_code=y.region.map(_name_to_code()))
    if adequate_only:
        adq = region_yield_summary(commodity).query("adequate").region
        y = y[y.region.isin(set(adq))]
    panel = y.merge(load_climate_annual(), on=["aagis_code", "year"], how="inner")

    parts = []
    for _, g in panel.groupby("region", sort=True):
        g = g.sort_values("year")
        g = g.assign(
            resid_yield=_detrend(g.year, g.yield_t_ha),
            resid_rain=_detrend(g.year, g.rain),
            resid_tmax=_detrend(g.year, g.tmax),
        )
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def region_linkage(commodity: str) -> pd.DataFrame:
    """Per-region detrended climate–yield correlations + variability measures."""
    panel = build_panel(commodity)
    summ = region_yield_summary(commodity).set_index("region")
    rows = []
    for region, g in panel.groupby("region", sort=True):
        rows.append(
            {
                "commodity": commodity,
                "region": region,
                "n_years": int(len(g)),
                "corr_detr_rain_yield": _corr(g.resid_yield, g.resid_rain),
                "corr_detr_tmax_yield": _corr(g.resid_yield, g.resid_tmax),
                "rain_cv": float(g.rain.std() / g.rain.mean()),
                "yield_detrended_cv": float(summ.loc[region, "detrended_cv"]),
            }
        )
    return pd.DataFrame(rows)


def cross_region_cv_corr(commodity: str) -> tuple[float, pd.DataFrame]:
    """Correlation between rainfall CV and yield detrended CV across regions."""
    table = region_linkage(commodity)
    return _corr(table.rain_cv, table.yield_detrended_cv), table


def event_year_summary(commodity: str) -> pd.DataFrame:
    """Mean detrended-yield residual (t/ha) in each event window vs non-event."""
    panel = build_panel(commodity)
    all_event = set().union(*[set(v) for v in EVENTS.values()])
    rows = []
    for name, yrs in EVENTS.items():
        sub = panel[panel.year.isin(yrs)]
        rows.append(
            {
                "commodity": commodity,
                "event": name,
                "region_years": int(len(sub)),
                "mean_resid_yield": float(sub.resid_yield.mean()),
            }
        )
    ne = panel[~panel.year.isin(all_event)]
    rows.append(
        {
            "commodity": commodity,
            "event": "non-event",
            "region_years": int(len(ne)),
            "mean_resid_yield": float(ne.resid_yield.mean()),
        }
    )
    return pd.DataFrame(rows)


def _atomic_write(df: pd.DataFrame, filename: str) -> Path:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / filename
    tmp = out.with_suffix(".csv.part")
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, out)
    return out


def write_linkage(df: pd.DataFrame) -> Path:
    return _atomic_write(df, LINKAGE_TABLE)


def write_events(df: pd.DataFrame) -> Path:
    return _atomic_write(df, EVENT_TABLE)


def load_linkage(path: str | Path | None = None) -> pd.DataFrame:
    p = TABLES_DIR / LINKAGE_TABLE if path is None else Path(path)
    return pd.read_csv(p)


__all__ = [
    "EVENTS",
    "LINKAGE_TABLE",
    "EVENT_TABLE",
    "load_climate_annual",
    "build_panel",
    "region_linkage",
    "cross_region_cv_corr",
    "event_year_summary",
    "write_linkage",
    "write_events",
    "load_linkage",
]
