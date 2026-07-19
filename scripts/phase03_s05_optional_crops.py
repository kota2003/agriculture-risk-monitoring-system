"""
Phase 03, Step 05 — optional-crop (sorghum / cotton) decision evidence.

Goal:
    Produce the data-availability evidence behind the Phase 03 optional-crop
    decision (scope §3.2) and persist the sorghum coverage table.

Decision (recorded in the notebook §4, PROJECT_LOG, and methodology at s06):
    EXCLUDE both. Cotton — the FDP regional file has no area/production/yield
    (only receipts); analysis is impossible and cotton is irrigated (out of the
    rainfed-broadacre framing). Sorghum — deferred to future work: only 6
    broadacre regions have >= 10 reliable years (all QLD/N-NSW summer belt),
    median production RSE ~45 (vs 19-32 for the core crops), and it is a
    summer-season crop that would need its own Pillar 1 growing-season indicators.

Output:
    outputs/tables/s05_optional_crop_availability.csv   (committed)

Run from repo root:
    python scripts/phase03_s05_optional_crops.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.log_utils import log, ok, section, subsection  # noqa: E402
from src.processing.optional_crops import (  # noqa: E402
    cotton_variables,
    sorghum_availability,
    write_availability,
)
from src.processing.yield_stats import MIN_YEARS  # noqa: E402


def main() -> int:
    section("Phase 03 - Step 05: optional-crop decision evidence")

    subsection("Cotton — region-level FDP variables")
    cvars = cotton_variables()
    log(f"  cotton variables in FDP regional: {cvars}")
    log(
        "  -> no area/production/yield; only receipts. Region yield-risk analysis impossible."
    )

    subsection("Sorghum — per-region coverage & survey reliability")
    av = sorghum_availability()
    broad = av[av.broadacre]
    adq = broad[broad.adequate]
    for r in av.itertuples(index=False):
        tag = "broadacre" if r.broadacre else "non-broad"
        flag = " *adequate" if (r.broadacre and r.adequate) else ""
        log(
            f"  {r.region:<46s} n={r.n_years:2d}  y={r.median_yield:.2f}  "
            f"RSE={r.median_prod_rse:.0f}  [{tag}]{flag}"
        )
    log(
        f"  broadacre with sorghum: {int(av.broadacre.sum())}/20  "
        f">= {MIN_YEARS}yr: {len(adq)}  | median prod RSE (all): {av.median_prod_rse.median():.0f}"
    )

    out = write_availability(av)
    subsection("Decision")
    log("  cotton: EXCLUDE (no yield data; irrigated).")
    log("  sorghum: DEFER to future work (narrow footprint, high RSE, summer-season).")
    ok(f"s05 complete: availability -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
