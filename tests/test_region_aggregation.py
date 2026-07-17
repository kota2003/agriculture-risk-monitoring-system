"""
Tests for src/processing/region_aggregation.py (Phase 02 s01, Task A).

These tests exercise the real Phase 01 data products
(data/processed/aagis_regions_repaired.gpkg and
data/raw/abares/fdp-regional-historical.csv). On a fresh clone where the
gitignored data has not yet been regenerated, the data-dependent tests
skip rather than fail — the pure-logic test always runs.

Run from repo root:
    python -m pytest tests/test_region_aggregation.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.processing.region_aggregation import (  # noqa: E402
    AAGIS_GPKG,
    EXPECTED_N_REGIONS,
    FDP_REGIONAL_CSV,
    STATE_BY_LEADING_DIGIT,
    load_fdp_region_names,
    load_region_mapping,
    validate_region_mapping,
)

_DATA_AVAILABLE = AAGIS_GPKG.exists() and FDP_REGIONAL_CSV.exists()
_needs_data = pytest.mark.skipif(
    not _DATA_AVAILABLE,
    reason="AAGIS GeoPackage and/or FDP regional CSV not present locally",
)


# ---------------------------------------------------------------------------
# Pure-logic test (no data files required)
# ---------------------------------------------------------------------------


def test_validate_flags_orphans_on_synthetic_mismatch():
    """A deliberately mismatched name must fail the zero-orphans check."""
    mapping = pd.DataFrame(
        {
            "aagis_code": ["111", "123"],
            "region_name": ["NSW Far West", "NSW Riverina"],
            "zone": ["Pastoral", "Wheat Sheep"],
            "state": ["NSW", "NSW"],
            "_aagis_alt": ["111", "123"],
        }
    )
    # FDP set disagrees on the second name -> one orphan each direction.
    fdp_names = {"NSW Far West", "NSW Riverina TYPO"}

    report = validate_region_mapping(mapping, fdp_names)

    assert report["valid"] is False
    assert report["checks"]["fdp_zero_orphans"] is False
    assert report["only_in_shapefile"] == ["NSW Riverina"]
    assert report["only_in_fdp"] == ["NSW Riverina TYPO"]


def test_state_prefix_map_is_complete():
    """All seven state/territory leading digits are covered."""
    assert set(STATE_BY_LEADING_DIGIT) == {"1", "2", "3", "4", "5", "6", "7"}


# ---------------------------------------------------------------------------
# Data-backed tests (Task A exit criterion on the real Phase 01 products)
# ---------------------------------------------------------------------------


@_needs_data
def test_load_region_mapping_shape():
    mapping = load_region_mapping()
    assert len(mapping) == EXPECTED_N_REGIONS
    for col in ("aagis_code", "region_name", "zone", "state"):
        assert col in mapping.columns
    assert mapping["aagis_code"].map(lambda c: len(c) == 3 and c.isdigit()).all()


@_needs_data
def test_task_a_exit_criterion_all_pass():
    """32/32 mapping, zero orphans, all validation checks pass."""
    mapping = load_region_mapping()
    fdp_names = load_fdp_region_names()
    report = validate_region_mapping(mapping, fdp_names)

    assert report["valid"] is True, report
    assert report["n_matching"] == EXPECTED_N_REGIONS
    assert report["only_in_shapefile"] == []
    assert report["only_in_fdp"] == []
    assert all(report["checks"].values())
