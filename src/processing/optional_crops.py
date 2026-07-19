"""
src/processing/optional_crops.py — optional-crop (sorghum / cotton) data
availability for the Phase 03 s05 decision.

The scope (§3.2) flags sorghum and cotton as optional crops whose inclusion is
decided in Phase 03 on the evidence. This module produces that evidence from the
raw ABARES FDP regional file:

  * cotton — the FDP regional file carries NO area/production/yield variable for
    cotton (only "Cotton receipts ($)"), so a region-level yield-risk analysis is
    impossible; cotton is also irrigated, outside the rainfed-broadacre framing.
  * sorghum — area and production ARE present, so yield is derivable
    (production ÷ area). This module reports per-region coverage and survey
    reliability so the narrow footprint / high RSE can be judged against the bar
    set by the core crops (wheat/barley/canola).

Decision (s05): exclude both. Cotton on data grounds; sorghum deferred to future
work (6 broadacre regions with ≥10 reliable years, all in the QLD/N-NSW summer
belt; median production RSE ~45 vs 19–32 for the core crops; a summer-season crop
that would need its own Pillar 1 growing-season indicators).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.paths import DATA_RAW, TABLES_DIR
from src.processing.yield_stats import MIN_YEARS, broadacre_region_names

FDP_REGIONAL = DATA_RAW / "abares" / "fdp-regional-historical.csv"
AVAILABILITY_TABLE = "s05_optional_crop_availability.csv"


def cotton_variables() -> list[str]:
    """Region-level FDP variables mentioning cotton (expected: receipts only)."""
    var = pd.read_csv(FDP_REGIONAL, usecols=["Variable"]).Variable.unique()
    return sorted(v for v in var if "cotton" in v.lower())


def load_sorghum_regional() -> pd.DataFrame:
    """Region-year sorghum with yield derived as production ÷ area (non-NA only)."""
    df = pd.read_csv(FDP_REGIONAL)
    keep = ["Year", "ABARES region", "Value", "RSE"]
    ren = {"Year": "year", "ABARES region": "region", "Value": "value", "RSE": "rse"}
    area = (
        df[df.Variable == "Sorghum area sown (ha)"][keep]
        .rename(columns=ren)
        .rename(columns={"value": "area_ha", "rse": "area_rse"})
    )
    prod = (
        df[df.Variable == "Sorghum produced (t)"][keep]
        .rename(columns=ren)
        .rename(columns={"value": "production_t", "rse": "production_rse"})
    )
    m = area.merge(prod, on=["year", "region"])
    m["yield_t_ha"] = (m["production_t"] / m["area_ha"]).replace(
        [np.inf, -np.inf], np.nan
    )
    return m.dropna(subset=["yield_t_ha"]).reset_index(drop=True)


def sorghum_availability() -> pd.DataFrame:
    """Per-region sorghum coverage, median yield, survey RSE, broadacre/adequate flags."""
    m = load_sorghum_regional()
    broad = broadacre_region_names()
    g = (
        m.groupby("region")
        .agg(
            n_years=("year", "nunique"),
            median_yield=("yield_t_ha", "median"),
            median_prod_rse=("production_rse", "median"),
        )
        .reset_index()
    )
    g["broadacre"] = g.region.isin(broad)
    g["adequate"] = g.n_years >= MIN_YEARS
    return g.sort_values("n_years", ascending=False).reset_index(drop=True)


def write_availability(df: pd.DataFrame, filename: str = AVAILABILITY_TABLE) -> Path:
    """Atomic (.part -> rename) write of the availability table to outputs/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / filename
    tmp = out.with_suffix(".csv.part")
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, out)
    return out


def load_availability(path: str | Path | None = None) -> pd.DataFrame:
    p = TABLES_DIR / AVAILABILITY_TABLE if path is None else Path(path)
    return pd.read_csv(p)


__all__ = [
    "FDP_REGIONAL",
    "AVAILABILITY_TABLE",
    "cotton_variables",
    "load_sorghum_regional",
    "sorghum_availability",
    "write_availability",
    "load_availability",
]
