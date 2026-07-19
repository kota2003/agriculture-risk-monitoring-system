"""Tests for src/processing/silo_climatology.py (Phase 03, Step 02)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.processing.silo_climatology import (  # noqa: E402
    ANNUAL_FULL_RECORD_NAME,
    EVAP_PAN_START,
    FULL_RECORD_END,
    FULL_RECORD_START,
    check_full_record,
    compute_baselines,
    load_annual_full_record,
    variable_year_start,
    variable_years,
)
from src.processing.silo_region_aggregation import REGION_MEANS_DIR  # noqa: E402

PRODUCT = REGION_MEANS_DIR / f"{ANNUAL_FULL_RECORD_NAME}.csv"
requires_product = pytest.mark.skipif(
    not PRODUCT.exists(), reason="full-record annual series not yet generated (run s02)"
)


# --- pure logic ---
def test_variable_year_start():
    assert variable_year_start("evap_pan") == EVAP_PAN_START == 1970
    assert variable_year_start("max_temp") == FULL_RECORD_START == 1961


def test_variable_years_inclusive():
    assert list(variable_years("evap_pan"))[0] == 1970
    assert list(variable_years("max_temp"))[0] == 1961
    assert list(variable_years("max_temp"))[-1] == FULL_RECORD_END == 2024


def _synthetic_annual() -> pd.DataFrame:
    """Two regions, constant fields, full record; tmax>tmin, rain positive."""
    rows = []
    for code, name in [("121", "R1"), ("521", "R2")]:
        for v, base in [("max_temp", 25.0), ("min_temp", 10.0), ("daily_rain", 400.0)]:
            start = variable_year_start(v)
            for y in range(start, FULL_RECORD_END + 1):
                rows.append(
                    {
                        "aagis_code": code,
                        "region_name": name,
                        "value": base,
                        "n_cells": 5,
                        "year": y,
                        "variable": v,
                    }
                )
    return pd.DataFrame(rows)


def test_compute_baselines_means_and_counts():
    df = _synthetic_annual()
    b = compute_baselines(df)
    # constant field -> baseline mean equals the constant
    r1_tmax = b[(b.aagis_code == "121") & (b.variable == "max_temp")].set_index(
        "baseline"
    )
    assert np.isclose(r1_tmax.loc["1961-1990", "value"], 25.0)
    assert r1_tmax.loc["1961-1990", "n_years"] == 30
    assert r1_tmax.loc["1991-2020", "n_years"] == 30


def test_check_full_record_flags_unphysical_temp():
    df = _synthetic_annual()
    # break physicality: force max_temp below min_temp
    df.loc[df.variable == "max_temp", "value"] = 5.0
    results = dict((name, ok) for name, ok, _ in check_full_record(df))
    assert results["tmax_gt_tmin"] is False


# --- data-backed (skip until the ~1h aggregation has produced the product) ---
@requires_product
def test_product_structure():
    df = load_annual_full_record()
    assert df["aagis_code"].astype(str).nunique() == 30
    ev = df[df.variable == "evap_pan"]
    assert int(ev.year.min()) == 1970 and int(ev.year.max()) == 2024
    mt = df[df.variable == "max_temp"]
    assert int(mt.year.min()) == 1961 and int(mt.year.max()) == 2024
    assert int(df["value"].isna().sum()) == 0


@requires_product
def test_product_passes_all_checks():
    fails = [
        name for name, ok, _ in check_full_record(load_annual_full_record()) if not ok
    ]
    assert not fails, f"failed checks: {fails}"
