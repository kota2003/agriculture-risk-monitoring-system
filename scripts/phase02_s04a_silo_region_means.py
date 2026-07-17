"""
Phase 02, Step 04a — SILO grid -> AAGIS region means (Task C, part 1).

Goal:
    Build the cropping-cell -> AAGIS-region assignment and compute
    cos(lat)-area-weighted region climatologies (annual series + monthly
    climatology) for the 1991-2020 reference period, for all six SILO
    variables. These feed the s04b grid-vs-region consistency check
    (scope v5 §4.2, §6.2).

Pipeline:
    1. Build + cache the cell-region map (data/processed/silo_cell_region_map.parquet).
    2. Report coverage: which of the 32 AAGIS regions receive cropping cells,
       flag any Wheat-Sheep / High-Rainfall (broadacre) region with none.
    3. Annual region means, 1991-2020, per variable -> one tidy CSV.
    4. Monthly region climatology, 1991-2020, per variable -> one tidy CSV.

Outputs (gitignored, regeneratable):
    data/processed/silo_cell_region_map.parquet
    data/processed/silo_region_means/annual_1991_2020.csv
    data/processed/silo_region_means/monthly_climatology_1991_2020.csv

Cost note:
    Heavy per-year NetCDF I/O. Each (variable, year) annual file is opened and
    reduced over time; expect order tens of minutes for the full 6 variables x
    30 years x 2 temporal scales on a laptop. Reads only; single atomic writes.
    Safe to re-run; the cell-region map is cached and reused.

Run from repo root:
    python scripts/phase02_s04a_silo_region_means.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# sys.path injection
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

import pandas as pd  # noqa: E402

from src.log_utils import log, ok, section, subsection, warn  # noqa: E402
from src.processing.region_aggregation import load_region_mapping  # noqa: E402
from src.processing.silo_region_aggregation import (  # noqa: E402
    CELL_REGION_MAP_PARQUET,
    REFERENCE_PERIOD,
    SILO_VARIABLES,
    aggregate_region_climatologies,
    build_cell_region_map,
    load_cell_region_map,
    save_cell_region_map,
    write_region_means,
)

# Broadacre zones expected to carry cropping cells (Pastoral is not cropping).
BROADACRE_ZONES = {"Wheat Sheep", "High Rainfall"}


def _cell_region_map() -> pd.DataFrame:
    if CELL_REGION_MAP_PARQUET.exists():
        log(f"using cached cell-region map: {CELL_REGION_MAP_PARQUET.name}")
        return load_cell_region_map()
    cell_df = build_cell_region_map()
    save_cell_region_map(cell_df)
    return cell_df


def _report_coverage(cell_df: pd.DataFrame) -> None:
    subsection("Cell-region coverage")
    mapping = load_region_mapping()  # 32 regions with zone
    per_region = cell_df.groupby(["aagis_code", "region_name"]).size().rename("n_cells")
    merged = mapping.merge(
        per_region.reset_index()[["aagis_code", "n_cells"]],
        on="aagis_code",
        how="left",
    )
    merged["n_cells"] = merged["n_cells"].fillna(0).astype(int)

    covered = int((merged["n_cells"] > 0).sum())
    log(f"  regions with cropping cells : {covered} / {len(merged)}")
    log(f"  total assigned cells        : {int(merged['n_cells'].sum()):,}")

    broadacre = merged[merged["zone"].isin(BROADACRE_ZONES)]
    missing = broadacre[broadacre["n_cells"] == 0]
    if len(missing):
        warn(
            "  broadacre regions with NO cropping cells: "
            f"{missing['region_name'].tolist()}"
        )
    else:
        ok("  every broadacre (Wheat-Sheep / High-Rainfall) region is covered")

    top = merged.sort_values("n_cells", ascending=False).head(5)
    log("  top 5 regions by cell count:")
    for r in top.itertuples(index=False):
        log(f"    {r.aagis_code}  {r.region_name:<40s} {r.n_cells:>6,d}  [{r.zone}]")


def main() -> int:
    section("Phase 02 - Step 04a: SILO grid -> AAGIS region means")

    y0, y1 = REFERENCE_PERIOD
    years = list(range(y0, y1 + 1))

    subsection("Cell-region assignment")
    cell_df = _cell_region_map()
    _report_coverage(cell_df)

    subsection(f"Region aggregation, single-pass ({y0}-{y1})")
    annual, monthly = aggregate_region_climatologies(SILO_VARIABLES, years, cell_df)
    write_region_means(annual, f"annual_{y0}_{y1}")
    write_region_means(monthly, f"monthly_climatology_{y0}_{y1}")

    ok(
        f"s04a complete: cell-region map + annual ({len(annual):,} rows) + "
        f"monthly climatology ({len(monthly):,} rows) persisted."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
