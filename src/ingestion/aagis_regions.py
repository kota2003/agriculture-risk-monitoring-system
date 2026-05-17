"""
AAGIS region shapefile ingestion (Project 5, Phase 01).

The Australian Agricultural and Grazing Industries Survey (AAGIS) region
shapefile is the canonical spatial unit for broadacre commodity
statistics published by ABARES. Per scope v4 section 3.1, AAGIS regions
are Project 5's primary yield spatial unit (used by Pillars 3, 4, 5, 6).

This module provides a pure-function ingestion pipeline:

    fetch_aagis_zip(url)           -> Path to downloaded ZIP
    unpack_aagis_zip(zip_path)     -> Path to .shp file inside
    load_aagis_geodataframe(shp)   -> GeoDataFrame
    repair_aagis_geometries(gdf)   -> (repaired_gdf, n_before, n_after)
    validate_aagis_regions(gdf)    -> raises on failure, logs on success
    persist_repaired_aagis(gdf)    -> Path to GeoPackage written

The top-level orchestration function ingest_aagis(url) chains all of
the above and returns an IngestResult dataclass suitable for updating
data/raw/manifest.yaml.

Known quirk handled here: the source shapefile contains self-
intersecting polygons and invalid ring orientations, documented by
the read.abares R package. GeoSeries.make_valid() (vectorized through
shapely 2.x) is applied as a standard repair step (scope v4 section
3.1, section 12.2).

Empirical findings from s01 first successful execution (2026-05-14):
  - ASGS16 v1 vintage contains 32 features (scope v4 section 3.1's
    "~60 regions" claim was wrong and is corrected in-place; see
    PROJECT_LOG Phase 01 Step 01 entry).
  - CRS: EPSG:4283 (GDA94 geographic).
  - Columns: aagis, class, name, zone, geometry (all lowercase).
  - 2 of 32 geometries invalid on input; both repaired by make_valid().
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests

from src.log_utils import error, log, ok, section, subsection, warn
from src.paths import DATA_PROCESSED, DATA_RAW

# Filesystem locations
AAGIS_RAW_DIR = DATA_RAW / "aagis_regions"
AAGIS_REPAIRED_PATH = DATA_PROCESSED / "aagis_regions_repaired.gpkg"

# Sanity-check bounds. The ASGS16 v1 vintage shapefile contains 32
# features (confirmed empirically in s01 first execution 2026-05-14).
# Range allows reasonable vintage drift. Earlier scope v4 estimate of
# "~60 regions" was empirically wrong and is corrected in-place; see
# PROJECT_LOG entry 2026-05-14 Phase 01 Step 01.
EXPECTED_REGION_COUNT_RANGE = (28, 38)

# Expected zone names (scope v4 section 3.1).
EXPECTED_ZONES = frozenset({"Pastoral", "Wheat Sheep", "High Rainfall"})
# Candidate column names for the zone attribute (varies by vintage and casing).
# Empirical: ASGS16 v1 uses lowercase 'zone'.
ZONE_COLUMN_CANDIDATES = (
    "AAGIS_ZONE",
    "ZONE",
    "Zone",
    "AAGIS_Zone",
    "aagis_zone",
    "zone",
)

# Candidate column names for the region-name attribute.
NAME_COLUMN_CANDIDATES = (
    "AAGIS_NAME",
    "Name",
    "name",
    "REGION_NAME",
    "region_name",
)


@dataclass
class IngestResult:
    """Summary of an AAGIS ingestion run, used to update manifest.yaml."""

    resolved_url: str
    retrieved_at: str  # ISO 8601 UTC timestamp
    raw_zip_path: Path
    raw_shapefile_path: Path
    repaired_geopackage_path: Path
    region_count: int
    zone_names: list[str] = field(default_factory=list)
    crs: str = ""
    bounding_box: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    invalid_geometries_before: int = 0
    invalid_geometries_after: int = 0


def fetch_aagis_zip(resolved_url: str, target_dir: Path = AAGIS_RAW_DIR) -> Path:
    """
    Download the AAGIS shapefile ZIP from a resolved direct-download URL.

    Idempotent: if the ZIP already exists at the target path, the
    download is skipped and the existing file is returned.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "aagis_regions.zip"

    if zip_path.exists():
        log(
            f"AAGIS ZIP already present at {zip_path.relative_to(DATA_RAW.parent)}, "
            f"skipping download"
        )
        return zip_path

    log(f"Downloading AAGIS shapefile ZIP from {resolved_url}")
    response = requests.get(resolved_url, stream=True, timeout=60)
    response.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1 << 14):
            f.write(chunk)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    ok(f"Downloaded {zip_path.name} ({size_mb:.2f} MB)")
    return zip_path


def unpack_aagis_zip(zip_path: Path, target_dir: Path = AAGIS_RAW_DIR) -> Path:
    """Extract the AAGIS ZIP and return the path to the primary .shp file."""
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target_dir)

    shp_files = list(target_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(
            f"No .shp file found after unpacking {zip_path} into {target_dir}. "
            f"The ZIP structure may have changed; manual inspection required."
        )
    if len(shp_files) > 1:
        warn(
            f"Multiple .shp files found in {target_dir}: "
            f"{[p.name for p in shp_files]}. Using first: {shp_files[0].name}"
        )

    shp_path = shp_files[0]
    ok(f"Unpacked AAGIS shapefile: {shp_path.name}")
    return shp_path


def load_aagis_geodataframe(shp_path: Path) -> gpd.GeoDataFrame:
    """Load the AAGIS shapefile into a GeoDataFrame, native CRS preserved."""
    gdf = gpd.read_file(shp_path)
    log(
        f"Loaded AAGIS shapefile: {len(gdf)} features, "
        f"CRS={gdf.crs}, columns={list(gdf.columns)}"
    )
    return gdf


def repair_aagis_geometries(
    gdf: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, int, int]:
    """
    Repair known AAGIS geometry errors via vectorized make_valid().

    Uses GeoSeries.make_valid() (geopandas 1.x / shapely 2.x vectorized
    path) which dispatches to shapely's C extension on the underlying
    geometry array.

    Returns
    -------
    tuple
        (repaired_gdf, invalid_count_before, invalid_count_after)
    """
    invalid_mask_before = ~gdf.geometry.is_valid
    invalid_before = int(invalid_mask_before.sum())

    if invalid_before == 0:
        ok("All AAGIS geometries valid as-is; no repair needed")
        return gdf.copy(), 0, 0

    invalid_indices = gdf[invalid_mask_before].index.tolist()
    warn(
        f"{invalid_before} of {len(gdf)} AAGIS geometries invalid at "
        f"indices {invalid_indices}; applying GeoSeries.make_valid() "
        f"(vectorized)"
    )

    log("Calling GeoSeries.make_valid() ...")
    repaired = gdf.copy()
    repaired.geometry = repaired.geometry.make_valid()
    log("GeoSeries.make_valid() returned")

    invalid_after = int((~repaired.geometry.is_valid).sum())

    if invalid_after == 0:
        ok(f"All {invalid_before} invalid geometries successfully repaired")
    else:
        error(
            f"{invalid_after} geometries STILL invalid after make_valid(); "
            f"manual investigation required (likely pathological input)"
        )

    return repaired, invalid_before, invalid_after


def validate_aagis_regions(gdf: gpd.GeoDataFrame) -> None:
    """
    Sanity-check AAGIS regions against scope expectations and surface
    diagnostics.

    Checks:
        - Region count within empirically-validated range [28, 38].
          (Scope v4 section 3.1 originally said "~60", corrected to
          32 after s01 first execution; see PROJECT_LOG.)
        - Zone composition matches the three expected zones (Pastoral,
          Wheat-sheep, High-rainfall).

    Surfaces diagnostic information for downstream documentation:
        - Zone value distribution (counts per zone).
        - First 8 region names.
        - 'class' column value distribution if present.

    Raises
    ------
    ValueError
        If the region count is outside [28, 38].
    """
    n_regions = len(gdf)
    lo, hi = EXPECTED_REGION_COUNT_RANGE
    if not (lo <= n_regions <= hi):
        raise ValueError(
            f"AAGIS region count {n_regions} outside expected range "
            f"[{lo}, {hi}]. Scope expectation may need revision; "
            f"investigate shapefile vintage."
        )
    ok(f"AAGIS region count {n_regions} within expected range [{lo}, {hi}]")

    # Zone column discovery + distribution diagnostic
    zone_col = _find_zone_column(gdf)
    if zone_col is None:
        warn(
            f"Could not identify a zone attribute column among candidates "
            f"{list(ZONE_COLUMN_CANDIDATES)}. Available columns: "
            f"{list(gdf.columns)}."
        )
    else:
        log(f"Zone distribution (column '{zone_col}'):")
        for zone_val, count in gdf[zone_col].value_counts(dropna=False).items():
            log(f"    {zone_val!r}: {count} regions")

        zones_present = set(gdf[zone_col].dropna().unique())
        unexpected = zones_present - EXPECTED_ZONES
        missing = EXPECTED_ZONES - zones_present
        if unexpected:
            warn(f"Unexpected zones present: {sorted(unexpected)}")
        if missing:
            warn(f"Expected zones missing: {sorted(missing)}")
        if not unexpected and not missing:
            ok("AAGIS zones match scope v4 section 3.1 expectation exactly")

    # Region-name diagnostic
    name_col = _find_name_column(gdf)
    if name_col is None:
        warn(
            f"Could not identify a region-name column among candidates "
            f"{list(NAME_COLUMN_CANDIDATES)}. Available columns: "
            f"{list(gdf.columns)}."
        )
    else:
        sample = gdf[name_col].head(8).tolist()
        log(f"Sample region names (column '{name_col}', first 8): {sample}")

    # 'class' column diagnostic — semantics to be discovered & documented
    if "class" in gdf.columns:
        log("'class' column value distribution:")
        for cls_val, count in gdf["class"].value_counts(dropna=False).items():
            log(f"    {cls_val!r}: {count}")


def persist_repaired_aagis(
    gdf: gpd.GeoDataFrame, output_path: Path = AAGIS_REPAIRED_PATH
) -> Path:
    """
    Save the repaired AAGIS regions as a GeoPackage.

    GeoPackage is preferred over re-emitting a shapefile because (a)
    it is a single file, (b) attribute names round-trip without ESRI's
    10-character truncation, (c) it stores CRS in OGC-compliant
    metadata.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()  # remove cleanly to avoid GPKG append-mode confusion

    gdf.to_file(output_path, driver="GPKG", layer="aagis_regions")
    size_mb = output_path.stat().st_size / 1024 / 1024
    ok(
        f"Persisted repaired AAGIS regions to "
        f"{output_path.relative_to(DATA_PROCESSED.parent)} ({size_mb:.2f} MB)"
    )
    return output_path


def ingest_aagis(resolved_url: str) -> IngestResult:
    """
    Full AAGIS ingestion pipeline (orchestration entry point).

    Sequence:
        1. Download ZIP (idempotent — skips if already present).
        2. Unpack and locate .shp file.
        3. Load GeoDataFrame.
        4. Repair invalid geometries (scope v4 section 3.1 known quirk).
        5. Validate region count, zones; surface diagnostics for class
           column and sample names.
        6. Persist repaired GeoDataFrame as GeoPackage.
    """
    section("AAGIS region shapefile ingestion")

    subsection("Step 1/6: Download ZIP")
    zip_path = fetch_aagis_zip(resolved_url)

    subsection("Step 2/6: Unpack shapefile")
    shp_path = unpack_aagis_zip(zip_path)

    subsection("Step 3/6: Load GeoDataFrame")
    gdf = load_aagis_geodataframe(shp_path)

    subsection("Step 4/6: Repair geometries")
    repaired_gdf, n_invalid_before, n_invalid_after = repair_aagis_geometries(gdf)

    subsection("Step 5/6: Validate region count, zones, and surface diagnostics")
    validate_aagis_regions(repaired_gdf)

    subsection("Step 6/6: Persist repaired regions")
    out_path = persist_repaired_aagis(repaired_gdf)

    bbox = tuple(float(b) for b in repaired_gdf.total_bounds)
    result = IngestResult(
        resolved_url=resolved_url,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        raw_zip_path=zip_path,
        raw_shapefile_path=shp_path,
        repaired_geopackage_path=out_path,
        region_count=len(repaired_gdf),
        zone_names=_discover_zones(repaired_gdf),
        crs=str(repaired_gdf.crs),
        bounding_box=bbox,
        invalid_geometries_before=n_invalid_before,
        invalid_geometries_after=n_invalid_after,
    )

    ok(
        f"AAGIS ingestion complete: {result.region_count} regions, "
        f"CRS={result.crs}, zones={result.zone_names}"
    )
    return result


def _find_zone_column(gdf: gpd.GeoDataFrame) -> str | None:
    """Locate the zone attribute column by trying common name variants."""
    for candidate in ZONE_COLUMN_CANDIDATES:
        if candidate in gdf.columns:
            return candidate
    return None


def _find_name_column(gdf: gpd.GeoDataFrame) -> str | None:
    """Locate the region-name attribute column by trying common variants."""
    for candidate in NAME_COLUMN_CANDIDATES:
        if candidate in gdf.columns:
            return candidate
    return None


def _discover_zones(gdf: gpd.GeoDataFrame) -> list[str]:
    """Return sorted unique zone names if the zone column can be found."""
    zone_col = _find_zone_column(gdf)
    if zone_col is None:
        return []
    return sorted(str(z) for z in gdf[zone_col].dropna().unique())
