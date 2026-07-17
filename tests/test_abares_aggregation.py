"""
Tests for src/processing/abares_aggregation.py (Phase 02 s02, Task B).

Pure-logic tests always run. Data-backed tests exercise the real Phase 01
processed tables + FDP CSVs and skip if that (gitignored) data is absent.

Run from repo root:
    python -m pytest tests/test_abares_aggregation.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.processing.abares_aggregation import (  # noqa: E402
    DEFAULT_TOLERANCE,
    EXPECTED_N_REGIONS,
    FDP_NATIONAL_CSV,
    FDP_REGIONAL_CSV,
    PROCESSED_ABARES_DIR,
    build_and_validate_commodity,
    load_population,
    validate_reconstruction,
    weight_to_region_totals,
)

_WHEAT_CSV = PROCESSED_ABARES_DIR / "wheat.csv"
_DATA_AVAILABLE = (
    FDP_REGIONAL_CSV.exists() and FDP_NATIONAL_CSV.exists() and _WHEAT_CSV.exists()
)
_needs_data = pytest.mark.skipif(
    not _DATA_AVAILABLE, reason="FDP CSVs and/or processed wheat.csv not present"
)


# ---------------------------------------------------------------------------
# Pure-logic tests
# ---------------------------------------------------------------------------


def test_weighting_multiplies_extensive_only():
    """area/production scale by Population; yield_t_ha is left intact."""
    perfarm = pd.DataFrame(
        {
            "region": ["R1", "R2"],
            "year": [2020, 2020],
            "area_ha": [100.0, 200.0],
            "production_t": [300.0, 400.0],
            "yield_t_ha": [3.0, 2.0],
        }
    )
    population = pd.DataFrame(
        {"region": ["R1", "R2"], "year": [2020, 2020], "population": [10.0, 5.0]}
    )

    out = weight_to_region_totals(perfarm, population)

    assert list(out["area_total_ha"]) == [1000.0, 1000.0]
    assert list(out["production_total_t"]) == [3000.0, 2000.0]
    # intensive column unchanged
    assert list(out["yield_t_ha"]) == [3.0, 2.0]


def test_missing_population_yields_nan_total():
    """A region-year with no Population match must not silently become 0."""
    perfarm = pd.DataFrame(
        {
            "region": ["R1"],
            "year": [1991],
            "area_ha": [100.0],
            "production_t": [300.0],
            "yield_t_ha": [3.0],
        }
    )
    population = pd.DataFrame({"region": ["R1"], "year": [1990], "population": [10.0]})

    out = weight_to_region_totals(perfarm, population)
    assert np.isnan(out.loc[0, "production_total_t"])


def _full_coverage_weighted(year: int, per_region_t: float) -> pd.DataFrame:
    n = EXPECTED_N_REGIONS
    return pd.DataFrame(
        {
            "region": [f"R{i}" for i in range(n)],
            "year": [year] * n,
            "production_total_t": [per_region_t] * n,
        }
    )


def test_validate_reconstruction_pass_and_fail():
    """Full-coverage, low-RSE reconstruction within tolerance passes; gap fails."""
    weighted = _full_coverage_weighted(2020, 1.0e6)  # sum = 32 Mt
    good = pd.DataFrame(
        {"year": [2020], "national_total_t": [32.0e6], "national_rse": [4.0]}
    )
    bad = pd.DataFrame(
        {"year": [2020], "national_total_t": [50.0e6], "national_rse": [4.0]}
    )

    assert validate_reconstruction(weighted, good)["valid"] is True
    assert validate_reconstruction(weighted, bad)["valid"] is False


def test_high_rse_year_excluded_from_grading():
    """A full-coverage year whose national RSE exceeds the gate is not graded."""
    # region-sum vs national disagree grossly (would fail if graded), but the
    # survey-reliability gate excludes the year, so it is reported not graded.
    weighted = _full_coverage_weighted(1992, 1.0e6)  # sum = 32 Mt
    national = pd.DataFrame(
        {"year": [1992], "national_total_t": [50.0e6], "national_rse": [23.0]}
    )

    report = validate_reconstruction(weighted, national)  # gate default 20%
    assert report["n_graded_years"] == 0
    assert 1992 in report["high_rse_years"]
    assert report["valid"] is False  # nothing graded -> not a pass


def test_partial_coverage_year_is_excluded_from_grading():
    """A year with < 32 regions is reported, not graded."""
    weighted = pd.DataFrame(
        {
            "region": ["R1", "R2"],
            "year": [2019, 2019],
            "production_total_t": [1.0e6, 1.0e6],
        }
    )
    national = pd.DataFrame(
        {"year": [2019], "national_total_t": [2.0e6], "national_rse": [4.0]}
    )

    report = validate_reconstruction(weighted, national)
    assert report["n_graded_years"] == 0
    assert 2019 in report["partial_coverage_years"]
    assert report["valid"] is False  # nothing graded -> not a pass


# ---------------------------------------------------------------------------
# Data-backed test (Task B exit criterion on the real data)
# ---------------------------------------------------------------------------


@_needs_data
@pytest.mark.parametrize("commodity", ["wheat", "barley", "canola"])
def test_reconstruction_within_tolerance(commodity):
    population = load_population()
    _weighted, report = build_and_validate_commodity(
        commodity, population_df=population
    )

    assert report["n_graded_years"] > 0
    assert report["worst_rel_error"] <= DEFAULT_TOLERANCE, report["per_year"]
    assert report["valid"] is True


@_needs_data
def test_canola_early_years_excluded_by_rse_gate():
    """Early canola (1992/1993, RSE 22-23%) must be gated out, not graded."""
    population = load_population()
    _weighted, report = build_and_validate_commodity("canola", population_df=population)

    assert 1992 in report["high_rse_years"]
    assert 1993 in report["high_rse_years"]
