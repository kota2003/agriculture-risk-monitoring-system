"""
src/processing/region_aggregation.py — AAGIS region code <-> FDP name mapping.

Phase 02, Step 01 (Task A). Provides the canonical bridge between the two
region keys used in Project 5:

  - The AAGIS shapefile / GeoPackage identifies regions by a 3-digit code
    (field ``class``; a duplicate ``aagis`` field carries the same value).
  - The ABARES Farm Data Portal (FDP) regional CSV identifies the same
    regions by text name (column ``ABARES region``).

Empirical findings that shaped this module (Phase 02 s01, verified against
data/processed/aagis_regions_repaired.gpkg and
data/raw/abares/fdp-regional-historical.csv):

  1. The GeoPackage feature table ``aagis_regions`` already carries BOTH the
     code (``class``) and the text name (``name``), plus a ``zone`` label.
     So the mapping is *read directly from the shapefile*, not reconstructed
     by fuzzy cross-referencing. (phase01_summary §4 assumed an ``AAGISname``
     field; the real field is ``name``.)
  2. The shapefile ``name`` values match the FDP ``ABARES region`` values
     EXACTLY — 32/32, zero orphans in either direction. Task A therefore
     reduces to *reading the canonical table and validating it*.
  3. ``aagis`` == ``class`` for all 32 rows (redundant code columns).
  4. The 3-digit code is hierarchical: 1st digit = state (1=NSW, 2=VIC,
     3=QLD, 4=SA, 5=WA, 6=TAS, 7=NT); 2nd = zone; 3rd = index. The leading
     digit is cross-checked against the state prefix of the region name.

Note (Phase 01 latent bug this module supersedes): the s06 helper
``src.ingestion.abares.cross_check_aagis_region_names`` selects its region
field by substring match on "region"/"aagis", which — given the actual
columns [aagis, class, name, zone] — picks the CODE column ``aagis`` rather
than the NAME column ``name``. It therefore compared codes against names and
never actually validated name equality. ``validate_region_mapping`` below
performs the intended name-vs-name check explicitly.

Usage:
    from src.processing.region_aggregation import (
        load_region_mapping,
        load_fdp_region_names,
        validate_region_mapping,
        write_region_mapping,
    )

    mapping = load_region_mapping()
    report = validate_region_mapping(mapping, load_fdp_region_names())
    assert report["valid"], report
    write_region_mapping(mapping)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.io_utils import read_csv_safe
from src.log_utils import log, ok, warn
from src.paths import DATA_PROCESSED, DATA_RAW

# ---------------------------------------------------------------------------
# Canonical file locations
# ---------------------------------------------------------------------------

AAGIS_GPKG: Path = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
FDP_REGIONAL_CSV: Path = DATA_RAW / "abares" / "fdp-regional-historical.csv"
REGION_MAPPING_CSV: Path = DATA_PROCESSED / "region_mapping.csv"

# ---------------------------------------------------------------------------
# Constants (empirically confirmed at Phase 02 s01)
# ---------------------------------------------------------------------------

EXPECTED_N_REGIONS: int = 32

# Leading digit of the 3-digit AAGIS code -> state / territory prefix.
STATE_BY_LEADING_DIGIT: dict[str, str] = {
    "1": "NSW",
    "2": "VIC",
    "3": "QLD",
    "4": "SA",
    "5": "WA",
    "6": "TAS",
    "7": "NT",
}

# GeoPackage attribute fields.
_CODE_FIELD: str = "class"
_ALT_CODE_FIELD: str = "aagis"
_NAME_FIELD: str = "name"
_ZONE_FIELD: str = "zone"

# FDP regional CSV region-name column.
_FDP_REGION_COL: str = "ABARES region"

# Output column order for the persisted mapping table.
OUTPUT_COLUMNS: list[str] = ["aagis_code", "region_name", "zone", "state"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_region_mapping(gpkg_path: str | Path = AAGIS_GPKG) -> pd.DataFrame:
    """
    Read the canonical code<->name<->zone mapping from the AAGIS GeoPackage.

    Parameters
    ----------
    gpkg_path : str or Path
        Path to ``aagis_regions_repaired.gpkg`` (Phase 01 s01 output).

    Returns
    -------
    pandas.DataFrame
        Columns: ``aagis_code`` (str, 3-digit), ``region_name`` (str),
        ``zone`` (str), ``state`` (str, derived from the leading digit).
        Sorted by ``aagis_code``. Carries a private ``_aagis_alt`` column
        (the duplicate ``aagis`` field) used only for the redundancy check
        in :func:`validate_region_mapping`; it is dropped on write.

    Raises
    ------
    FileNotFoundError
        If the GeoPackage does not exist.
    KeyError
        If the expected attribute fields are absent.
    """
    gpkg_path = Path(gpkg_path)
    if not gpkg_path.exists():
        raise FileNotFoundError(f"AAGIS GeoPackage not found: {gpkg_path}")

    gdf = gpd.read_file(gpkg_path)

    required = {_CODE_FIELD, _NAME_FIELD, _ZONE_FIELD}
    missing = required - set(gdf.columns)
    if missing:
        raise KeyError(
            f"AAGIS GeoPackage missing expected field(s) {sorted(missing)}. "
            f"Available columns: {list(gdf.columns)}"
        )

    mapping = pd.DataFrame(
        {
            "aagis_code": gdf[_CODE_FIELD].astype(str).str.strip(),
            "region_name": gdf[_NAME_FIELD].astype(str).str.strip(),
            "zone": gdf[_ZONE_FIELD].astype(str).str.strip(),
        }
    )

    # Duplicate code column, retained only for the redundancy assertion.
    if _ALT_CODE_FIELD in gdf.columns:
        mapping["_aagis_alt"] = gdf[_ALT_CODE_FIELD].astype(str).str.strip()

    mapping["state"] = mapping["aagis_code"].str[0].map(STATE_BY_LEADING_DIGIT)
    mapping = mapping.sort_values("aagis_code").reset_index(drop=True)

    log(f"  loaded {len(mapping)} AAGIS regions from {gpkg_path.name}")
    return mapping


def load_fdp_region_names(fdp_csv: str | Path = FDP_REGIONAL_CSV) -> set[str]:
    """
    Return the set of unique region names from the ABARES FDP regional CSV.

    Parameters
    ----------
    fdp_csv : str or Path
        Path to ``fdp-regional-historical.csv``.

    Returns
    -------
    set of str
        Unique, whitespace-stripped ``ABARES region`` names.

    Raises
    ------
    FileNotFoundError
        If the CSV does not exist.
    KeyError
        If the region-name column is absent.
    """
    fdp_csv = Path(fdp_csv)
    if not fdp_csv.exists():
        raise FileNotFoundError(f"FDP regional CSV not found: {fdp_csv}")

    df = read_csv_safe(fdp_csv, usecols=[_FDP_REGION_COL])
    return set(df[_FDP_REGION_COL].astype(str).str.strip())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_region_mapping(
    mapping: pd.DataFrame,
    fdp_names: set[str],
) -> dict:
    """
    Validate the region mapping against the Task A exit criterion.

    Checks performed:
      1. Row count equals :data:`EXPECTED_N_REGIONS` (32).
      2. ``aagis_code`` values are unique and all exactly 3 digits.
      3. ``region_name`` values are unique.
      4. ``_aagis_alt`` == ``aagis_code`` for every row (code redundancy).
      5. Every ``region_name`` starts with the state prefix implied by the
         leading digit of its code (geographic sanity).
      6. Name-set equality with the FDP: zero orphans in either direction
         (this is the core Task A exit criterion, 32/32).

    Parameters
    ----------
    mapping : pandas.DataFrame
        Output of :func:`load_region_mapping`.
    fdp_names : set of str
        Output of :func:`load_fdp_region_names`.

    Returns
    -------
    dict
        Report with a top-level ``valid`` boolean and per-check detail.
        ``only_in_shapefile`` / ``only_in_fdp`` list any orphan names.
    """
    shp_names = set(mapping["region_name"])

    only_in_shapefile = sorted(shp_names - fdp_names)
    only_in_fdp = sorted(fdp_names - shp_names)

    bad_code_len = sorted(
        c for c in mapping["aagis_code"] if not (len(c) == 3 and c.isdigit())
    )

    if "_aagis_alt" in mapping.columns:
        code_redundancy_ok = bool(
            (mapping["_aagis_alt"] == mapping["aagis_code"]).all()
        )
    else:
        code_redundancy_ok = True  # alt column absent; nothing to contradict

    state_prefix_mismatches = [
        {"aagis_code": row.aagis_code, "region_name": row.region_name}
        for row in mapping.itertuples(index=False)
        if not str(row.region_name).startswith(
            STATE_BY_LEADING_DIGIT.get(str(row.aagis_code)[0], "\x00")
        )
    ]

    checks = {
        "row_count_ok": len(mapping) == EXPECTED_N_REGIONS,
        "codes_unique": mapping["aagis_code"].is_unique,
        "codes_well_formed": len(bad_code_len) == 0,
        "names_unique": mapping["region_name"].is_unique,
        "code_redundancy_ok": code_redundancy_ok,
        "state_prefix_ok": len(state_prefix_mismatches) == 0,
        "fdp_zero_orphans": len(only_in_shapefile) == 0 and len(only_in_fdp) == 0,
    }

    return {
        "valid": all(checks.values()),
        "checks": checks,
        "n_regions": len(mapping),
        "n_fdp_names": len(fdp_names),
        "n_matching": len(shp_names & fdp_names),
        "only_in_shapefile": only_in_shapefile,
        "only_in_fdp": only_in_fdp,
        "bad_codes": bad_code_len,
        "state_prefix_mismatches": state_prefix_mismatches,
    }


# ---------------------------------------------------------------------------
# Persistence (atomic .part -> rename, mirroring src/ingestion/abares.py)
# ---------------------------------------------------------------------------


def write_region_mapping(
    mapping: pd.DataFrame,
    out_path: str | Path = REGION_MAPPING_CSV,
) -> Path:
    """
    Persist the mapping table as CSV using an atomic ``.part`` -> rename.

    Only :data:`OUTPUT_COLUMNS` are written (the private ``_aagis_alt``
    helper column is dropped). Re-running overwrites atomically, so a
    crashed write never leaves a partial ``region_mapping.csv`` in place.

    Parameters
    ----------
    mapping : pandas.DataFrame
        Output of :func:`load_region_mapping`.
    out_path : str or Path
        Destination CSV path.

    Returns
    -------
    Path
        The written path.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    to_write = mapping[OUTPUT_COLUMNS].copy()

    tmp = out_path.with_suffix(out_path.suffix + ".part")
    to_write.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(out_path)

    ok(f"  wrote {len(to_write)} rows -> {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def build_and_validate(
    gpkg_path: str | Path = AAGIS_GPKG,
    fdp_csv: str | Path = FDP_REGIONAL_CSV,
) -> tuple[pd.DataFrame, dict]:
    """
    Load the mapping and validate it in one call.

    Returns
    -------
    (pandas.DataFrame, dict)
        The mapping table and the validation report. The report should be
        checked (``report["valid"]``) before the mapping is persisted or
        used downstream.
    """
    mapping = load_region_mapping(gpkg_path)
    fdp_names = load_fdp_region_names(fdp_csv)
    report = validate_region_mapping(mapping, fdp_names)
    if not report["valid"]:
        warn("  region mapping validation FAILED; see report for details")
    return mapping, report


__all__ = [
    "AAGIS_GPKG",
    "FDP_REGIONAL_CSV",
    "REGION_MAPPING_CSV",
    "EXPECTED_N_REGIONS",
    "STATE_BY_LEADING_DIGIT",
    "OUTPUT_COLUMNS",
    "load_region_mapping",
    "load_fdp_region_names",
    "validate_region_mapping",
    "write_region_mapping",
    "build_and_validate",
]
