"""
Phase 03, Step 03 — ABARES region-yield summary (trends, dispersion, lower tail).

Goal:
    Compute per-region descriptive yield statistics (level, OLS trend, CV and
    detrended CV, lower-tail risk, survey RSE) for wheat / barley / canola over
    their reliable windows, flagging regions with sparse coverage — the inputs
    for the Phase 03 yield EDA (notebook §2).

Output:
    outputs/tables/s03_yield_region_summary.csv   (committed)

Exit code:
    0 on success; 1 if the summary is empty or the ABARES inputs are missing.

Run from repo root:
    python scripts/phase03_s03_yield_summary.py
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
from src.processing.yield_stats import (  # noqa: E402
    COMMODITIES,
    MIN_YEARS,
    RELIABLE_YIELD_START,
    load_yield,
    region_yield_summary,
    write_summary,
)


def main() -> int:
    section("Phase 03 - Step 03: ABARES region-yield summary")

    subsection("Coverage (reliable window, broadacre)")
    for c in COMMODITIES:
        df = load_yield(c)
        log(
            f"  {c:<7s} start>={RELIABLE_YIELD_START[c]}  "
            f"non-NA yield region-years={len(df):>4d}  regions={df.region.nunique()}"
        )

    subsection("Per-region summary")
    summary = region_yield_summary()
    if summary.empty:
        error("yield summary is empty; check ABARES inputs")
        return 1

    for c in COMMODITIES:
        sc = summary[summary.commodity == c]
        ad = sc[sc.adequate]
        sparse = sc[~sc.adequate].region.tolist()
        log(
            f"  {c:<7s} regions={len(sc)}  adequate(>= {MIN_YEARS}yr)={len(ad)}  "
            f"trend median={ad.trend_t_ha_decade.median():+.3f} t/ha/decade  "
            f"detrended_cv={ad.detrended_cv.min():.2f}-{ad.detrended_cv.max():.2f}  "
            f"p10/median median={ad.p10_over_median.median():.2f}"
        )
        if sparse:
            log(f"           sparse (flagged): {sparse}")

    out = write_summary(summary)
    ok(f"s03 complete: {len(summary)} region-commodity rows -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
