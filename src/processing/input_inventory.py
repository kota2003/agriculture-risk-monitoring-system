"""
src/processing/input_inventory.py
Phase 03 — analysis-ready input inventory & structural invariants.

Loads the Phase 02 analysis-ready products (region mapping, ABARES region
yields + region totals, SILO region climatologies, cell-region map), records
their shapes/columns, and verifies the structural invariants Phase 03 EDA
depends on:

  * expected row counts per product (regression guard against silent drift),
  * region-key alignment across the yield (region name) and climate
    (aagis_code / region_name) products via the s01 region mapping,
  * full coverage of the 20 broadacre (Wheat-Sheep / High-Rainfall) regions in
    BOTH the yield and climate products.

Reused by:
  * scripts/phase03_s01_data_inventory.py       (orchestrator + CSV report)
  * notebooks/03_exploratory_analysis.ipynb     (inventory display cell)

Empirical verification (scope §2.4): the expected shapes below were confirmed
against the real Phase 02 artefacts on 2026-07-17 before this module was written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.paths import DATA_PROCESSED, TABLES_DIR
from src.processing.region_aggregation import load_region_mapping  # noqa: F401

BROADACRE_ZONES = frozenset({"Wheat Sheep", "High Rainfall"})
COMMODITIES = ("wheat", "barley", "canola")

# Reliable yield windows (scope v5.1 §3.3): wheat/barley 1990+, canola 1994+.
RELIABLE_YIELD_START = {"wheat": 1990, "barley": 1990, "canola": 1994}


@dataclass(frozen=True)
class ProductSpec:
    key: str
    location: str  # "processed" | "tables"
    relpath: str
    kind: str  # "csv" | "parquet"
    expected_rows: int | None = None


# Expected rows verified against the real artefacts on 2026-07-17.
PRODUCT_SPECS: tuple[ProductSpec, ...] = (
    ProductSpec("region_mapping", "processed", "region_mapping.csv", "csv", 32),
    ProductSpec("wheat", "processed", "abares/wheat.csv", "csv", 1114),
    ProductSpec("barley", "processed", "abares/barley.csv", "csv", 1114),
    ProductSpec("canola", "processed", "abares/canola.csv", "csv", 1114),
    ProductSpec(
        "wheat_totals", "processed", "abares/wheat_region_totals.csv", "csv", 1114
    ),
    ProductSpec(
        "barley_totals", "processed", "abares/barley_region_totals.csv", "csv", 1114
    ),
    ProductSpec(
        "canola_totals", "processed", "abares/canola_region_totals.csv", "csv", 1114
    ),
    ProductSpec(
        "silo_annual",
        "processed",
        "silo_region_means/annual_1991_2020.csv",
        "csv",
        5400,
    ),
    ProductSpec(
        "silo_monthly",
        "processed",
        "silo_region_means/monthly_climatology_1991_2020.csv",
        "csv",
        2160,
    ),
    ProductSpec(
        "silo_cell_map", "processed", "silo_cell_region_map.parquet", "parquet", 28577
    ),
    ProductSpec(
        "s04b_climatology", "tables", "s04b_region_climatology_summary.csv", "csv", 30
    ),
    ProductSpec(
        "s05_acornsat", "tables", "s05_acornsat_region_coverage.csv", "csv", None
    ),
    ProductSpec(
        "s06_openweather", "tables", "s06_openweather_silo_metrics.csv", "csv", 40
    ),
    ProductSpec("s04b_external", "tables", "s04b_external_comparison.csv", "csv", None),
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _resolve(spec: ProductSpec) -> Path:
    base = DATA_PROCESSED if spec.location == "processed" else TABLES_DIR
    return base / spec.relpath


def _read(spec: ProductSpec) -> pd.DataFrame:
    path = _resolve(spec)
    if spec.kind == "parquet":
        return pd.read_parquet(path)
    # Keep region codes as strings so joins are type-stable across products.
    # (An unused dtype key for files without `aagis_code` is ignored by pandas.)
    return pd.read_csv(path, dtype={"aagis_code": str})


def load_products() -> dict[str, pd.DataFrame]:
    """Load every product that exists on disk, keyed by spec.key."""
    out: dict[str, pd.DataFrame] = {}
    for spec in PRODUCT_SPECS:
        if _resolve(spec).exists():
            out[spec.key] = _read(spec)
    return out


def broadacre_regions(mapping: pd.DataFrame) -> pd.DataFrame:
    """The 20 broadacre (Wheat-Sheep / High-Rainfall) regions from the mapping."""
    return mapping[mapping["zone"].isin(BROADACRE_ZONES)].copy()


def build_inventory() -> pd.DataFrame:
    """One row per product: existence, shape, columns, expected-row check."""
    records = []
    for spec in PRODUCT_SPECS:
        path = _resolve(spec)
        exists = path.exists()
        n_rows = n_cols = None
        cols = ""
        if exists:
            df = _read(spec)
            n_rows, n_cols = df.shape
            cols = ";".join(map(str, df.columns))
        row_ok = (spec.expected_rows is None) or (n_rows == spec.expected_rows)
        records.append(
            {
                "product": spec.key,
                "location": spec.location,
                "path": spec.relpath,
                "exists": exists,
                "n_rows": n_rows,
                "n_cols": n_cols,
                "expected_rows": spec.expected_rows,
                "row_ok": bool(row_ok),
                "columns": cols,
            }
        )
    return pd.DataFrame.from_records(records)


def check_invariants(products: dict[str, pd.DataFrame] | None = None) -> list[Check]:
    """Structural invariants Phase 03 EDA depends on."""
    if products is None:
        products = load_products()
    checks: list[Check] = []

    mapping = products.get("region_mapping")
    if mapping is None:
        return [Check("region_mapping_present", False, "region_mapping.csv missing")]
    mapping = mapping.copy()
    mapping["aagis_code"] = mapping["aagis_code"].astype(str)

    checks.append(
        Check(
            "region_mapping_32",
            len(mapping) == 32 and mapping["aagis_code"].nunique() == 32,
            f"{len(mapping)} rows, {mapping['aagis_code'].nunique()} unique codes",
        )
    )

    broad = broadacre_regions(mapping)
    broad_codes = set(broad["aagis_code"])
    broad_names = set(broad["region_name"])
    checks.append(
        Check(
            "broadacre_count_20",
            len(broad) == 20,
            f"{len(broad)} broadacre regions (want 20)",
        )
    )

    ann = products.get("silo_annual")
    if ann is not None:
        ann = ann.copy()
        ann["aagis_code"] = ann["aagis_code"].astype(str)
        codes = set(ann["aagis_code"])
        checks.append(
            Check(
                "silo_annual_structure",
                ann["aagis_code"].nunique() == 30
                and ann["variable"].nunique() == 6
                and ann["year"].nunique() == 30,
                f"{ann['aagis_code'].nunique()} regions x "
                f"{ann['variable'].nunique()} vars x {ann['year'].nunique()} years",
            )
        )
        missing_broad = broad_codes - codes
        checks.append(
            Check(
                "silo_covers_broadacre",
                len(missing_broad) == 0,
                (
                    "all 20 broadacre regions present"
                    if not missing_broad
                    else f"missing {sorted(missing_broad)}"
                ),
            )
        )
        uncovered = set(mapping["aagis_code"]) - codes
        uncovered_zones = set(mapping[mapping["aagis_code"].isin(uncovered)]["zone"])
        checks.append(
            Check(
                "silo_uncovered_are_pastoral",
                uncovered == {"511", "711"} and uncovered_zones <= {"Pastoral"},
                f"uncovered={sorted(uncovered)} zones={sorted(uncovered_zones)} "
                "(want 511,711 both Pastoral)",
            )
        )
        checks.append(
            Check(
                "silo_region_names_in_mapping",
                set(ann["region_name"]).issubset(set(mapping["region_name"])),
                "region_name subset of mapping",
            )
        )

    mon = products.get("silo_monthly")
    if mon is not None:
        checks.append(
            Check(
                "silo_monthly_structure",
                mon["aagis_code"].astype(str).nunique() == 30
                and mon["variable"].nunique() == 6
                and mon["month"].nunique() == 12,
                f"{mon['aagis_code'].nunique()} regions x "
                f"{mon['variable'].nunique()} vars x {mon['month'].nunique()} months",
            )
        )

    for c in COMMODITIES:
        df = products.get(c)
        if df is None:
            continue
        names = set(df["region"])
        checks.append(
            Check(
                f"{c}_regions_in_mapping",
                names.issubset(set(mapping["region_name"])),
                (
                    "region names subset of mapping"
                    if names.issubset(set(mapping["region_name"]))
                    else f"unknown: {sorted(names - set(mapping['region_name']))}"
                ),
            )
        )
        checks.append(
            Check(
                f"{c}_covers_broadacre",
                broad_names.issubset(names),
                (
                    "all 20 broadacre regions present"
                    if broad_names.issubset(names)
                    else f"missing {sorted(broad_names - names)}"
                ),
            )
        )
    return checks


def reliable_yield_summary(
    products: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Per-commodity yield coverage + pre-reliable-window rows (informational)."""
    if products is None:
        products = load_products()
    rows = []
    for c in COMMODITIES:
        df = products.get(c)
        if df is None:
            continue
        start = RELIABLE_YIELD_START[c]
        pre = df[df["year"] < start]
        rows.append(
            {
                "commodity": c,
                "reliable_start": start,
                "rows": len(df),
                "non_na_yield": int(df["yield_t_ha"].notna().sum()),
                "min_year": int(df["year"].min()),
                "max_year": int(df["year"].max()),
                "pre_window_rows": len(pre),
                "pre_window_non_na_yield": int(pre["yield_t_ha"].notna().sum()),
            }
        )
    return pd.DataFrame.from_records(rows)


def write_inventory(
    df: pd.DataFrame, filename: str = "s01_input_inventory.csv"
) -> Path:
    """Atomic (.part -> rename) write of the inventory table to outputs/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / filename
    tmp = out.with_suffix(".csv.part")
    df.to_csv(tmp, index=False)
    os.replace(tmp, out)
    return out


__all__ = [
    "BROADACRE_ZONES",
    "COMMODITIES",
    "RELIABLE_YIELD_START",
    "PRODUCT_SPECS",
    "ProductSpec",
    "Check",
    "broadacre_regions",
    "build_inventory",
    "check_invariants",
    "load_products",
    "reliable_yield_summary",
    "write_inventory",
]
