"""Tests for src/processing/optional_crops.py (Phase 03, Step 05)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from src.processing.optional_crops import (  # noqa: E402
    FDP_REGIONAL,
    cotton_variables,
    sorghum_availability,
)
from src.processing.yield_stats import MIN_YEARS  # noqa: E402

requires_fdp = pytest.mark.skipif(
    not FDP_REGIONAL.exists(), reason="raw FDP regional file not present"
)


@requires_fdp
def test_cotton_has_no_yield_variables():
    cvars = cotton_variables()
    # cotton appears only as receipts; no area/production/yield
    assert cvars, "expected at least the cotton receipts variable"
    joined = " ".join(cvars).lower()
    assert "area" not in joined
    assert "produced" not in joined
    assert "yield" not in joined


@requires_fdp
def test_sorghum_availability_shape_and_flags():
    av = sorghum_availability()
    assert {
        "region",
        "n_years",
        "median_yield",
        "median_prod_rse",
        "broadacre",
        "adequate",
    }.issubset(av.columns)
    # adequate is exactly n_years >= MIN_YEARS
    assert (av.adequate == (av.n_years >= MIN_YEARS)).all()


@requires_fdp
def test_sorghum_footprint_is_narrow_and_noisy():
    av = sorghum_availability()
    adq_broad = av[av.broadacre & av.adequate]
    # narrow footprint: only a handful of broadacre regions clear the bar
    assert 3 <= len(adq_broad) <= 10
    # survey error is materially worse than the core crops (median ~19-32)
    assert av.median_prod_rse.median() > 35
