"""
Phase 02, Step 06 — OpenWeather vs SILO comparison study (Task D; scope §5.6.4).

Goal:
    Quantify agreement between the OpenWeather day-summary API and SILO at the
    10 sampled AAGIS region centroids over 2022-2024 — RMSE, bias
    (OpenWeather - SILO), correlation for daily tmax / tmin / rain / humidity.

Pipeline:
    1. For each centroid, pair OpenWeather daily records with SILO at the
       nearest cropping cell (humidity via SILO-derived RH, Tetens).
    2. Per-centroid x variable metrics + pooled-over-centroids metrics.
    3. Persist outputs/tables/s06_openweather_silo_metrics.csv (per centroid)
       and print the pooled summary.

This is an auxiliary methodological study (not a pass/fail gate); exits 0.

Run from repo root:
    python scripts/phase02_s06_openweather_silo.py
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

from src.log_utils import log, ok, section, subsection  # noqa: E402
from src.paths import TABLES_DIR  # noqa: E402
from src.processing.openweather_silo_compare import (  # noqa: E402
    build_comparison,
    compute_metrics,
    compute_pooled_metrics,
)


def main() -> int:
    section("Phase 02 - Step 06: OpenWeather vs SILO comparison (centroids)")

    subsection("Pairing OpenWeather with SILO (nearest cropping cell)")
    paired = build_comparison()

    metrics = compute_metrics(paired)
    pooled = compute_pooled_metrics(paired)

    subsection("Pooled metrics (all centroids, per variable)")
    log("  variable      n      RMSE     bias(OW-SILO)   corr")
    for r in pooled.itertuples(index=False):
        log(
            f"  {r.variable:<10s} {int(r.n):>6d}  {r.rmse:7.2f}   "
            f"{r.bias_ow_minus_silo:+8.2f}      {r.corr:5.2f}"
        )

    subsection("Per-centroid metrics (tmax / rain highlights)")
    for var in ("tmax", "rain"):
        sub = metrics[metrics["variable"] == var].sort_values("aagis_code")
        log(f"  [{var}]")
        for r in sub.itertuples(index=False):
            log(
                f"    {r.aagis_code}  n={int(r.n):>4d}  rmse={r.rmse:6.2f}  "
                f"bias={r.bias_ow_minus_silo:+6.2f}  corr={r.corr:5.2f}"
            )

    subsection("Persist table")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / "s06_openweather_silo_metrics.csv"
    tmp = out.with_suffix(out.suffix + ".part")
    metrics.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out)
    ok(f"  wrote {out}")

    ok("s06 complete: OpenWeather-SILO agreement quantified (RMSE / bias / corr).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
