"""
Phase 03, Step 04 — climate × yield linkage + historical-event sanity.

Goal:
    Join the full-record climate region series to the observed yields and quantify
    (descriptively) the within-region year-to-year climate–yield correlation, the
    across-region variability relationship, and the mean yield anomaly in known
    drought / heat years (decision gate ③ = A+: sanity + a light quantitative
    anchor; formal cross-pillar validation stays in Phase 09).

Outputs:
    outputs/tables/s04_climate_yield_linkage.csv   (committed)
    outputs/tables/s04_event_year_anomaly.csv      (committed)

Exit code:
    0 on success; 1 if a panel cannot be built.

Run from repo root:
    python scripts/phase03_s04_climate_yield.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

import pandas as pd  # noqa: E402

from src.log_utils import error, log, ok, section, subsection  # noqa: E402
from src.processing.climate_yield import (  # noqa: E402
    cross_region_cv_corr,
    event_year_summary,
    write_events,
    write_linkage,
)
from src.processing.yield_stats import COMMODITIES  # noqa: E402


def main() -> int:
    section("Phase 03 - Step 04: climate x yield linkage + event sanity")

    linkage_all, events_all = [], []

    subsection("Within-region (detrended) & across-region linkage")
    for c in COMMODITIES:
        cv_corr, table = cross_region_cv_corr(c)
        if table.empty:
            error(f"empty panel for {c}")
            return 1
        med_rain = table.corr_detr_rain_yield.median()
        med_tmax = table.corr_detr_tmax_yield.median()
        log(
            f"  {c:<7s} regions={len(table):>2d}  "
            f"corr(detr rain,yield) median={med_rain:+.2f}  "
            f"corr(detr tmax,yield) median={med_tmax:+.2f}  "
            f"cross-region corr(rainCV, yieldCV)={cv_corr:+.2f}"
        )
        linkage_all.append(table)

    subsection("Historical-event sanity (mean detrended-yield residual, t/ha)")
    for c in COMMODITIES:
        ev = event_year_summary(c)
        events_all.append(ev)
        parts = "  ".join(
            f"{r.event.split(' (')[0]}={r.mean_resid_yield:+.3f}"
            for r in ev.itertuples()
        )
        log(f"  {c:<7s} {parts}")

    out1 = write_linkage(pd.concat(linkage_all, ignore_index=True))
    out2 = write_events(pd.concat(events_all, ignore_index=True))
    ok(f"s04 complete: linkage -> {out1.name}; events -> {out2.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
