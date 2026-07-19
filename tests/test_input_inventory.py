"""Tests for src/processing/input_inventory.py (Phase 03, Step 01)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.paths import DATA_PROCESSED  # noqa: E402
from src.processing.input_inventory import (  # noqa: E402
    BROADACRE_ZONES,
    COMMODITIES,
    PRODUCT_SPECS,
    RELIABLE_YIELD_START,
    broadacre_regions,
    build_inventory,
    check_invariants,
    load_products,
    reliable_yield_summary,
)

DATA_AVAILABLE = (DATA_PROCESSED / "region_mapping.csv").exists()
requires_data = pytest.mark.skipif(
    not DATA_AVAILABLE, reason="processed data not present"
)


# --- pure logic ---
def test_broadacre_partition_pure():
    m = pd.DataFrame(
        {
            "aagis_code": ["121", "111", "631", "711"],
            "region_name": ["a", "b", "c", "d"],
            "zone": ["Wheat Sheep", "Pastoral", "High Rainfall", "Pastoral"],
            "state": ["NSW", "NSW", "TAS", "NT"],
        }
    )
    assert set(broadacre_regions(m)["aagis_code"]) == {"121", "631"}


def test_reliable_start_constants():
    assert RELIABLE_YIELD_START == {"wheat": 1990, "barley": 1990, "canola": 1994}


def test_specs_cover_core_products():
    keys = {s.key for s in PRODUCT_SPECS}
    assert {"region_mapping", "silo_annual", "silo_monthly", "silo_cell_map"} <= keys
    for c in COMMODITIES:
        assert c in keys and f"{c}_totals" in keys


# --- data-backed (skip when the gitignored processed data is absent) ---
@requires_data
def test_inventory_row_counts():
    inv = build_inventory()
    bad = inv[inv["exists"] & ~inv["row_ok"]]
    assert (
        bad.empty
    ), f"row mismatch: {bad[['product', 'n_rows', 'expected_rows']].to_dict('records')}"


@requires_data
def test_all_invariants_pass():
    fails = [c.name for c in check_invariants() if not c.ok]
    assert not fails, f"failed invariants: {fails}"


@requires_data
def test_broadacre_joinable_across_yield_and_climate():
    p = load_products()
    m = p["region_mapping"].copy()
    m["aagis_code"] = m["aagis_code"].astype(str)
    broad_names = set(m[m["zone"].isin(BROADACRE_ZONES)]["region_name"])
    broad_codes = set(m[m["zone"].isin(BROADACRE_ZONES)]["aagis_code"])
    assert len(broad_names) == 20
    assert broad_names <= set(p["wheat"]["region"])
    assert broad_codes <= set(p["silo_annual"]["aagis_code"].astype(str))


@requires_data
def test_canola_reliable_window_is_1994():
    rel = reliable_yield_summary().set_index("commodity")
    assert rel.loc["canola", "reliable_start"] == 1994
