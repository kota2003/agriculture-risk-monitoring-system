"""
Regression test for src/ingestion/abares.py::cross_check_aagis_region_names
(Phase 02 s03).

Before the s03 fix, the helper selected the AAGIS region field by substring
match on "aagis"/"region"; given the actual GeoPackage columns
[aagis, class, name, zone] it picked the numeric CODE column `aagis` and
compared codes against FDP names, so it always reported n_matching == 0 and
never validated name equality. This test locks the corrected behaviour: the
`name` field is selected and all 32 region names match with zero orphans.

Data-backed; skips if the (gitignored) Phase 01 data is absent.

Run from repo root:
    python -m pytest tests/test_abares_region_name_check.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ingestion.abares import (  # noqa: E402
    cross_check_aagis_region_names,
    load_fdp_csv,
)
from src.paths import DATA_PROCESSED, DATA_RAW  # noqa: E402

_GPKG = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
_FDP_REGIONAL = DATA_RAW / "abares" / "fdp-regional-historical.csv"
_DATA_AVAILABLE = _GPKG.exists() and _FDP_REGIONAL.exists()
_needs_data = pytest.mark.skipif(
    not _DATA_AVAILABLE, reason="AAGIS GeoPackage / FDP regional CSV not present"
)


@_needs_data
def test_cross_check_selects_name_field_and_matches_all_32():
    df_regional = load_fdp_csv(_FDP_REGIONAL, "regional")
    result = cross_check_aagis_region_names(df_regional, _GPKG)

    assert result["valid"] is True
    # The fix must select the text name column, not the numeric `aagis` code.
    assert result["aagis_field_used"] == "name"
    assert result["n_aagis_regions"] == 32
    assert result["n_fdp_regions"] == 32
    assert result["n_matching"] == 32
    assert result["only_in_fdp"] == []
    assert result["only_in_aagis"] == []
