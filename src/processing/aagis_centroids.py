"""
AAGIS region centroid computation for OpenWeather sampling (Phase 01 Step 08).

Computes representative lat/lon centroids for the 10 AAGIS regions selected
in scope §4.5 (OpenWeather–SILO validation comparison study). The centroids
are derived from the s01-validated AAGIS shapefile
(data/processed/aagis_regions_repaired.gpkg).

Approved region selection (s08a, 2026-05-15):

  121  NSW Riverina                              Wheat-Sheep    semi-arid
  122  NSW North West Slopes and Plains          Wheat-Sheep    subtropical
  123  NSW Central West                          Wheat-Sheep    temperate-dry
  221  VIC Wimmera                               Wheat-Sheep    Mediterranean
  222  VIC Mallee                                Wheat-Sheep    semi-arid
  322  QLD Eastern Darling Downs                 Wheat-Sheep    subtropical
  421  SA Eyre Peninsula                         Wheat-Sheep    Mediterranean
  521  WA Central and Southern Wheat Belt        Wheat-Sheep    Mediterranean
  522  WA Northern and Eastern Wheat Belt        Wheat-Sheep    semi-arid
  631  TAS Tasmania                              High Rainfall  cool-temperate

Centroid method:
  Use the *representative point* (shapely.geometry.representative_point())
  rather than the geometric centroid. For irregular AAGIS polygons (some
  with disconnected islands or narrow extensions), the geometric centroid
  can fall outside the polygon entirely, leaving the OpenWeather query
  outside the actual agricultural area. representative_point() is
  guaranteed to lie inside the polygon and is a more honest "anywhere
  inside this region" coordinate for a single-point query.

  As a sanity check, we also report the geometric centroid distance and
  flag any region where representative_point and centroid differ by more
  than 100 km (indicates highly irregular polygon — informational only,
  not a failure).

Reproducibility:
  Centroid values depend only on the AAGIS shapefile vintage recorded in
  data/raw/manifest.yaml; re-running this module on the same shapefile
  returns identical centroids (single-precision float exactness).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import geopandas as gpd

from src.log_utils import log, warn

# ----- Approved region selection ----------------------------------------

# Ordering follows the s08a approval list (state-grouped for readability).
APPROVED_REGION_CODES: list[str] = [
    "121",  # NSW Riverina
    "122",  # NSW North West Slopes and Plains
    "123",  # NSW Central West
    "221",  # VIC Wimmera
    "222",  # VIC Mallee
    "322",  # QLD Eastern Darling Downs
    "421",  # SA Eyre Peninsula
    "521",  # WA Central and Southern Wheat Belt
    "522",  # WA Northern and Eastern Wheat Belt
    "631",  # TAS Tasmania
]


@dataclass(frozen=True)
class RegionCentroid:
    code: str
    name: str
    lat: float
    lon: float


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    from math import asin, cos, radians, sin, sqrt

    r1, r2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(r1) * cos(r2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def compute_centroids(
    aagis_gpkg: Path,
    region_codes: Iterable[str] = APPROVED_REGION_CODES,
    name_field_candidates: tuple[str, ...] = (
        "AAGISregion",
        "AAGIS_NAME",
        "AAGISnam",
        "name",
        "region_name",
    ),
    code_field_candidates: tuple[str, ...] = (
        "aagis",
        "AAGIS",
        "AAGIScode",
        "AAGIS_CODE",
        "region",
        "region_code",
    ),
) -> list[RegionCentroid]:
    """
    Compute representative-point centroids for the given AAGIS region codes.

    Args:
        aagis_gpkg: Path to data/processed/aagis_regions_repaired.gpkg.
        region_codes: AAGIS 3-digit codes to extract (default = approved 10).
        name_field_candidates / code_field_candidates: shapefile field
            names; first match wins.

    Returns:
        list[RegionCentroid], in the order of `region_codes`.

    Raises:
        RuntimeError if a region code is not found in the shapefile.
    """
    if not Path(aagis_gpkg).exists():
        raise FileNotFoundError(f"AAGIS gpkg not found: {aagis_gpkg}")

    gdf = gpd.read_file(aagis_gpkg)

    # Resolve which field holds the AAGIS code and which holds the name.
    code_field = next((c for c in code_field_candidates if c in gdf.columns), None)
    name_field = next((c for c in name_field_candidates if c in gdf.columns), None)
    if code_field is None:
        raise RuntimeError(
            f"No AAGIS code field found in shapefile. Tried {code_field_candidates}. "
            f"Available columns: {list(gdf.columns)}"
        )
    if name_field is None:
        # Fall back to code as label
        name_field = code_field

    # Normalise code dtype to string (AAGIS shapefile uses int-like strings).
    gdf[code_field] = gdf[code_field].astype(str).str.strip()

    # Ensure WGS84 for lat/lon centroids.
    if gdf.crs is None:
        raise RuntimeError(f"AAGIS gpkg has no CRS: {aagis_gpkg}")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    out: list[RegionCentroid] = []
    for code in region_codes:
        sub = gdf[gdf[code_field] == str(code)]
        if sub.empty:
            available = sorted(gdf[code_field].unique())
            raise RuntimeError(
                f"AAGIS region code '{code}' not found in shapefile. "
                f"Available codes: {available}"
            )
        # Dissolve in case the region is split across multiple rows.
        geom = sub.unary_union
        rep = geom.representative_point()
        cen = geom.centroid
        # Sanity check (informational only)
        dist_km = _haversine_km(rep.y, rep.x, cen.y, cen.x)
        if dist_km > 100:
            warn(
                f"  region {code}: representative_point and centroid differ by "
                f"{dist_km:.1f} km (likely a highly irregular polygon)"
            )
        name = str(sub.iloc[0].get(name_field, code))
        out.append(
            RegionCentroid(
                code=str(code),
                name=name,
                lat=float(rep.y),
                lon=float(rep.x),
            )
        )
        log(f"  {code:<4s} {name:<45s} lat={rep.y:+.4f} lon={rep.x:+.4f}")
    return out
