"""
Tests for src/processing/acornsat_coverage.py (Phase 02 s05, Task E).

Pure-logic coverage/flag tests always run. Data-backed tests exercise the real
station list / AAGIS gpkg and skip if absent.

Run from repo root:
    python -m pytest tests/test_acornsat_coverage.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.processing.acornsat_coverage import (  # noqa: E402
    EXPECTED_N_STATIONS,
    STATION_LIST_CSV,
    compute_region_coverage,
    load_stations,
    summarize,
)

_MAPPING = pd.DataFrame(
    {
        "aagis_code": ["521", "421", "631", "111"],
        "region_name": [
            "WA Central and Southern Wheat Belt",
            "SA Eyre Peninsula",
            "TAS Tasmania",
            "NSW Far West",
        ],
        "zone": ["Wheat Sheep", "Wheat Sheep", "High Rainfall", "Pastoral"],
    }
)

# 521: 2 available + 1 unavailable; 421: 1 available (sparse); 631: none;
# 111 (pastoral): 1 available.
_ASSIGNED = pd.DataFrame(
    {
        "station_id": ["a1", "a2", "u1", "a3", "a4"],
        "name": ["A1", "A2", "U1", "A3", "A4"],
        "available": [True, True, False, True, True],
        "aagis_code": ["521", "521", "521", "421", "111"],
        "region_name": [
            "WA Central and Southern Wheat Belt",
            "WA Central and Southern Wheat Belt",
            "WA Central and Southern Wheat Belt",
            "SA Eyre Peninsula",
            "NSW Far West",
        ],
    }
)


def test_compute_region_coverage_counts_and_flags():
    cov = compute_region_coverage(_ASSIGNED, _MAPPING).set_index("aagis_code")

    assert int(cov.loc["521", "n_available"]) == 2
    assert int(cov.loc["521", "n_unavailable"]) == 1
    assert bool(cov.loc["521", "no_station"]) is False
    assert bool(cov.loc["521", "sparse"]) is False

    # TAS broadacre with zero available -> no_station
    assert int(cov.loc["631", "n_available"]) == 0
    assert bool(cov.loc["631", "no_station"]) is True

    # SA Eyre broadacre with a single available -> sparse
    assert bool(cov.loc["421", "sparse"]) is True

    # Pastoral region never flagged
    assert bool(cov.loc["111", "no_station"]) is False
    assert bool(cov.loc["111", "sparse"]) is False


def test_summarize_reports_broadacre_gaps():
    cov = compute_region_coverage(_ASSIGNED, _MAPPING)
    summ = summarize(cov, _ASSIGNED)
    assert "TAS Tasmania" in summ["broadacre_no_station"]
    assert "SA Eyre Peninsula" in summ["broadacre_sparse"]
    assert summ["n_available_total"] == 4
    assert summ["n_unavailable_total"] == 1


# ---------------------------------------------------------------------------
# Data-backed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not STATION_LIST_CSV.exists(), reason="station list not present")
def test_real_station_list_totals():
    stations = load_stations()
    assert len(stations) == EXPECTED_N_STATIONS
    assert int(stations["available"].sum()) == 94  # 112 - 18 unavailable
    assert int((~stations["available"]).sum()) == 18
