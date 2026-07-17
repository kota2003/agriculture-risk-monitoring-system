"""
Phase 02, Step 02 — ABARES per-typical-farm -> region-total weighting (Task B).

Goal:
    Convert the per-typical-farm extensive quantities (sown area, production)
    in the processed ABARES commodity tables into region totals by weighting
    with the FDP survey ``Population`` (number of broadacre farms per
    region-year), and validate that region sums reconstruct the FDP national
    totals within +-5% (scope v5 §4.3, §6.2, §11.6).

Denominator:
    FDP ``Population`` (survey expansion factor), decided at s02 after
    empirical triangulation. See src/processing/abares_aggregation.py for the
    rationale (overrides the phase01_summary §5 ABS-SA2 default).

Pipeline (per commodity in wheat/barley/canola):
    1. Load per-typical-farm table (data/processed/abares/<commodity>.csv).
    2. Weight area_ha, production_t by Population -> *_total columns; carry
       yield_t_ha unchanged.
    3. Validate region-sum vs FDP national reconstruction (full-coverage
       years only) within +-5%.
    4. Persist data/processed/abares/<commodity>_region_totals.csv
       (atomic .part -> rename).

Exit status:
    0 if every commodity passes; 1 otherwise.

Idempotency:
    Reads only; the single write per commodity is atomic. Re-run freely.

Expected runtime: < 10 seconds.

Run from repo root:
    python scripts/phase02_s02_abares_weighting.py
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

from src.log_utils import error, log, ok, section, subsection  # noqa: E402
from src.processing.abares_aggregation import (  # noqa: E402
    COMMODITIES,
    DEFAULT_TOLERANCE,
    build_and_validate_commodity,
    load_population,
    write_region_totals,
)


def _print_report(commodity: str, report: dict) -> None:
    per_year = report["per_year"]
    # Show a compact tail (most recent 5 graded years) for a human eyeball.
    recent = per_year.sort_values("year").tail(5)
    subsection(f"{commodity}: region-sum vs national reconstruction (recent years)")
    for row in recent.itertuples(index=False):
        if not row.full_coverage:
            flag = "  [partial coverage, ungraded]"
        elif not row.reliable:
            flag = f"  [RSE {row.national_rse:.0f}% > gate, ungraded]"
        else:
            flag = ""
        log(
            f"  {int(row.year)}  region_sum={row.region_sum_t / 1e6:7.3f} Mt  "
            f"national={row.national_total_t / 1e6:7.3f} Mt  "
            f"rel_err={row.rel_error * 100:5.2f}%{flag}"
        )
    log("")
    log(f"  graded years                 : {report['n_graded_years']}")
    log(f"  worst relative error         : {report['worst_rel_error'] * 100:.2f}%")
    log(f"  tolerance                    : {report['tolerance'] * 100:.0f}%")
    log(
        f"  survey-reliability gate      : national RSE <= {report['rse_threshold']:.0f}%"
    )
    if report["partial_coverage_years"]:
        log(f"  partial-coverage years       : {report['partial_coverage_years']}")
    if report["high_rse_years"]:
        log(f"  high-RSE (ungraded) years    : {report['high_rse_years']}")


def main() -> int:
    section("Phase 02 - Step 02: ABARES per-farm -> region-total weighting")

    population = load_population()
    log(
        f"loaded Population for {population['region'].nunique()} regions "
        f"across {population['year'].nunique()} years"
    )

    all_ok = True
    for commodity in COMMODITIES:
        subsection(f"Weighting: {commodity}")
        weighted, report = build_and_validate_commodity(
            commodity, population_df=population, tolerance=DEFAULT_TOLERANCE
        )
        _print_report(commodity, report)

        if not report["valid"]:
            error(f"{commodity}: reconstruction exceeds +-{DEFAULT_TOLERANCE:.0%}")
            all_ok = False
            continue

        write_region_totals(weighted, commodity)

    if not all_ok:
        error("Task B validation FAILED for at least one commodity.")
        return 1

    ok(
        f"Task B complete: {len(COMMODITIES)} commodities weighted to region "
        f"totals; region sums reconstruct FDP national within "
        f"+-{DEFAULT_TOLERANCE:.0%}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
