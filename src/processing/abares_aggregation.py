"""
src/processing/abares_aggregation.py — per-typical-farm -> region-total weighting.

Phase 02, Step 02 (Task B). ABARES Farm Data Portal (FDP) reports survey
estimates as *per-typical-farm averages*, not region totals (Phase 01 s06
empirical finding #2; scope v5 §4.3, §5.3, §11.6). To obtain region-total
extensive quantities (sown area, production) they must be multiplied by the
number of farms the survey represents in that region-year.

Denominator decision (Phase 02 s02, empirically grounded):
    Use the FDP ``Population`` variable — the survey's own estimate of the
    number of broadacre farm businesses in each region-year. This overrides
    the phase01_summary §5 default (ABS Census 2020-21 SA2 business counts).
    Rationale:
      - Region-native and per-year: no SA2<->AAGIS spatial join is needed
        (that mapping stays a Task G concern), and the weight tracks the
        same time axis as the yields.
      - Internally exact: because ``Population`` is the survey's expansion
        factor, sum over regions of (per-farm value x Population)
        reconstructs the FDP national total almost exactly. Verified for
        wheat 2020/2021/2022: ratio region-sum / national = 0.999 / 1.000 /
        1.001.
      - Single-source discipline: keeps the weighting inside the ABARES
        frame that produced the per-typical-farm values, so region totals
        are exactly the survey's implied totals.
    ABS Census SA2 counts and ABARES national industry counts remain useful
    as *independent cross-checks* in Task G, not as the primary weight.

Weighting rule:
    - EXTENSIVE columns (per-farm; require weighting):
        area_ha       -> area_total_ha       = area_ha       x Population
        production_t  -> production_total_t  = production_t  x Population
    - INTENSIVE column (already per-hectare; NOT weighted):
        yield_t_ha    -> carried through unchanged (per-farm-representative
                         regional yield remains dimensionally valid).

Coverage caveat:
    ``Population`` is present for all 35 FDP years (1990-2024), but a few
    early years report only 29 of 32 regions. Region-years without a
    ``Population`` match yield NaN totals and are reported, not silently
    dropped. National-reconstruction validation is applied only to
    full-coverage (32-region) years.

Usage:
    from src.processing.abares_aggregation import (
        load_population, load_commodity_perfarm,
        weight_to_region_totals, validate_reconstruction, write_region_totals,
    )
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.io_utils import read_csv_safe
from src.log_utils import ok, warn
from src.paths import DATA_PROCESSED, DATA_RAW

# ---------------------------------------------------------------------------
# Locations & constants
# ---------------------------------------------------------------------------

FDP_REGIONAL_CSV: Path = DATA_RAW / "abares" / "fdp-regional-historical.csv"
FDP_NATIONAL_CSV: Path = DATA_RAW / "abares" / "fdp-national-historical.csv"
PROCESSED_ABARES_DIR: Path = DATA_PROCESSED / "abares"

COMMODITIES: tuple[str, ...] = ("wheat", "barley", "canola")

POPULATION_VAR: str = "Population"
NATIONAL_INDUSTRY: str = "All Broadacre"
EXPECTED_N_REGIONS: int = 32
DEFAULT_TOLERANCE: float = 0.05  # +-5% survey-error tolerance (scope §6.2)
# Survey-reliability gate (%). A year is graded against DEFAULT_TOLERANCE only
# if the FDP national production RSE is at or below this threshold. This
# operationalises the "survey-error tolerance" qualifier: years whose survey
# error is itself extreme (e.g. early-1990s canola, RSE 22-88%, integer-rounded
# to 2-3 t/farm) are reported but not graded. Empirically, RSE <= 20% cleanly
# separates the unreliable canola years (1990-1993) from the reliable window
# (1994+, RSE <= 15%, reconstruction error <= 3.4%).
RSE_GATE_THRESHOLD: float = 20.0

# FDP raw production variable name per commodity (used for national check).
PRODUCTION_VAR_BY_COMMODITY: dict[str, str] = {
    "wheat": "Wheat produced (t)",
    "barley": "Barley produced (t)",
    "canola": "Canola produced (t)",
}

# per-farm extensive column -> region-total column name.
WEIGHT_MAP: dict[str, str] = {
    "area_ha": "area_total_ha",
    "production_t": "production_total_t",
}
INTENSIVE_COLUMNS: tuple[str, ...] = ("yield_t_ha",)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_population(fdp_regional_csv: str | Path = FDP_REGIONAL_CSV) -> pd.DataFrame:
    """
    Return the per (region, year) survey population (farm count).

    Returns
    -------
    pandas.DataFrame
        Columns ``region`` (str), ``year`` (int), ``population`` (float).
    """
    fdp_regional_csv = Path(fdp_regional_csv)
    if not fdp_regional_csv.exists():
        raise FileNotFoundError(f"FDP regional CSV not found: {fdp_regional_csv}")

    df = read_csv_safe(
        fdp_regional_csv,
        usecols=["Variable", "Year", "ABARES region", "Value"],
    )
    pop = df[df["Variable"] == POPULATION_VAR].copy()
    pop = pop.rename(
        columns={"ABARES region": "region", "Year": "year", "Value": "population"}
    )
    pop["region"] = pop["region"].astype(str).str.strip()
    pop["year"] = pop["year"].astype(int)
    pop["population"] = pop["population"].astype(float)
    return pop[["region", "year", "population"]].reset_index(drop=True)


def load_commodity_perfarm(
    commodity: str,
    processed_dir: str | Path = PROCESSED_ABARES_DIR,
) -> pd.DataFrame:
    """
    Load the per-typical-farm processed commodity table (Phase 01 s06 output).

    Expected columns: ``region, year, area_ha, production_t, yield_t_ha,
    area_rse, production_rse``.
    """
    path = Path(processed_dir) / f"{commodity}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Processed commodity CSV not found: {path}")
    df = read_csv_safe(path)
    df["region"] = df["region"].astype(str).str.strip()
    df["year"] = df["year"].astype(int)
    for col in ("area_ha", "production_t", "yield_t_ha"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------


def weight_to_region_totals(
    perfarm_df: pd.DataFrame,
    population_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Multiply per-typical-farm extensive columns by the survey population.

    Adds ``population``, ``area_total_ha``, ``production_total_t`` and keeps
    intensive ``yield_t_ha`` unchanged. Region-years lacking a Population
    match keep NaN totals (reported by the caller / orchestrator).

    Parameters
    ----------
    perfarm_df : pandas.DataFrame
        Output of :func:`load_commodity_perfarm`.
    population_df : pandas.DataFrame
        Output of :func:`load_population`.

    Returns
    -------
    pandas.DataFrame
        The per-farm frame plus the region-total columns.
    """
    merged = perfarm_df.merge(population_df, on=["region", "year"], how="left")

    n_missing = int(merged["population"].isna().sum())
    if n_missing:
        warn(
            f"  {n_missing} (region, year) rows have no Population match "
            f"(region-total set to NaN for these)"
        )

    for src_col, total_col in WEIGHT_MAP.items():
        if src_col not in merged.columns:
            raise KeyError(f"Expected per-farm column '{src_col}' not in frame")
        merged[total_col] = merged[src_col] * merged["population"]

    return merged


# ---------------------------------------------------------------------------
# Validation (region-sum reconstruction vs FDP national)
# ---------------------------------------------------------------------------


def load_national_production(
    commodity: str,
    fdp_national_csv: str | Path = FDP_NATIONAL_CSV,
) -> pd.DataFrame:
    """
    Reconstruct FDP national commodity production per year, with survey RSE.

    National total = per-farm national production x national Population, both
    filtered to Industry == 'All Broadacre'. ``national_rse`` is the published
    relative standard error (%) of the per-farm production figure; it drives
    the survey-reliability gate in :func:`validate_reconstruction`.

    Returns
    -------
    pandas.DataFrame
        Columns ``year`` (int), ``national_total_t`` (float),
        ``national_rse`` (float, percent).
    """
    fdp_national_csv = Path(fdp_national_csv)
    if not fdp_national_csv.exists():
        raise FileNotFoundError(f"FDP national CSV not found: {fdp_national_csv}")

    prod_var = PRODUCTION_VAR_BY_COMMODITY[commodity]
    df = read_csv_safe(
        fdp_national_csv,
        usecols=["Variable", "Year", "Value", "RSE", "Industry"],
    )
    df = df[df["Industry"] == NATIONAL_INDUSTRY].copy()
    df["Year"] = df["Year"].astype(int)

    prod = df[df["Variable"] == prod_var].set_index("Year")
    perfarm = prod["Value"].astype(float)
    rse = prod["RSE"].astype(float)
    pop = df[df["Variable"] == POPULATION_VAR].set_index("Year")["Value"].astype(float)
    national = (perfarm * pop).rename("national_total_t")
    out = pd.DataFrame({"national_total_t": national, "national_rse": rse}).dropna(
        subset=["national_total_t"]
    )
    return out.reset_index().rename(columns={"Year": "year"})


def validate_reconstruction(
    weighted_df: pd.DataFrame,
    national_df: pd.DataFrame,
    tolerance: float = DEFAULT_TOLERANCE,
    rse_threshold: float = RSE_GATE_THRESHOLD,
) -> dict:
    """
    Check that region-summed totals reconstruct FDP national within tolerance,
    for survey-reliable, full-coverage years only.

    A year is *graded* against ``tolerance`` only if BOTH gates pass:
      - full coverage: all 32 regions carry a Population-weighted
        ``production_total_t``; AND
      - survey reliability: the FDP national production RSE for that year is
        at or below ``rse_threshold`` (honours the "survey-error tolerance"
        qualifier of the scope §6.2 exit criterion).
    Years failing either gate are reported, not graded.

    Returns
    -------
    dict
        ``valid`` boolean plus a per-year detail table, the list of
        partial-coverage years, and the list of high-RSE (ungraded) years.
    """
    valid_rows = weighted_df.dropna(subset=["production_total_t"])
    grouped = valid_rows.groupby("year")

    region_sum = grouped["production_total_t"].sum()
    n_regions = grouped["region"].nunique()

    merged = pd.DataFrame({"region_sum_t": region_sum, "n_regions": n_regions}).join(
        national_df.set_index("year"), how="inner"
    )
    merged["rel_error"] = (
        merged["region_sum_t"] - merged["national_total_t"]
    ).abs() / merged["national_total_t"]
    merged["full_coverage"] = merged["n_regions"] == EXPECTED_N_REGIONS
    merged["reliable"] = merged["national_rse"] <= rse_threshold
    merged["graded"] = merged["full_coverage"] & merged["reliable"]

    graded = merged[merged["graded"]]
    partial_years = sorted(merged[~merged["full_coverage"]].index.tolist())
    high_rse_years = sorted(
        merged[merged["full_coverage"] & ~merged["reliable"]].index.tolist()
    )

    worst = float(graded["rel_error"].max()) if len(graded) else float("nan")

    return {
        "valid": bool(len(graded) > 0 and (graded["rel_error"] <= tolerance).all()),
        "tolerance": tolerance,
        "rse_threshold": rse_threshold,
        "n_graded_years": int(len(graded)),
        "worst_rel_error": worst,
        "partial_coverage_years": partial_years,
        "high_rse_years": high_rse_years,
        "per_year": merged.reset_index(),
    }


# ---------------------------------------------------------------------------
# Persistence (atomic .part -> rename)
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS: list[str] = [
    "region",
    "year",
    "population",
    "area_total_ha",
    "production_total_t",
    "yield_t_ha",
]


def write_region_totals(
    weighted_df: pd.DataFrame,
    commodity: str,
    processed_dir: str | Path = PROCESSED_ABARES_DIR,
) -> Path:
    """
    Persist the region-total table as ``<commodity>_region_totals.csv``.

    Atomic ``.part`` -> rename, mirroring the ingestion modules.
    """
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / f"{commodity}_region_totals.csv"

    cols = [c for c in OUTPUT_COLUMNS if c in weighted_df.columns]
    to_write = weighted_df[cols].copy()

    tmp = out_path.with_suffix(out_path.suffix + ".part")
    to_write.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out_path)

    ok(f"  wrote {len(to_write)} rows -> {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def build_and_validate_commodity(
    commodity: str,
    population_df: pd.DataFrame | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[pd.DataFrame, dict]:
    """
    Weight one commodity to region totals and validate the reconstruction.

    Returns
    -------
    (pandas.DataFrame, dict)
        The weighted region-total frame and the validation report.
    """
    if population_df is None:
        population_df = load_population()
    perfarm = load_commodity_perfarm(commodity)
    weighted = weight_to_region_totals(perfarm, population_df)
    national = load_national_production(commodity)
    report = validate_reconstruction(weighted, national, tolerance=tolerance)
    if not report["valid"]:
        warn(f"  {commodity}: reconstruction validation FAILED")
    return weighted, report


__all__ = [
    "FDP_REGIONAL_CSV",
    "FDP_NATIONAL_CSV",
    "PROCESSED_ABARES_DIR",
    "COMMODITIES",
    "POPULATION_VAR",
    "DEFAULT_TOLERANCE",
    "RSE_GATE_THRESHOLD",
    "WEIGHT_MAP",
    "INTENSIVE_COLUMNS",
    "OUTPUT_COLUMNS",
    "load_population",
    "load_commodity_perfarm",
    "weight_to_region_totals",
    "load_national_production",
    "validate_reconstruction",
    "write_region_totals",
    "build_and_validate_commodity",
]
