"""
src/processing/acornsat_coverage.py — ACORN-SAT station coverage by AAGIS region.

Phase 02, Step 05 (Task E). Assesses the impact of the 18 unavailable
ACORN-SAT stations on regional SILO validation (Phase 01 s05 finding #5;
scope v5 §4.2, §12.2). ACORN-SAT is the homogenised station "truth" used to
sanity-check SILO's interpolated grids; a broadacre region with no available
ACORN-SAT station can only be validated indirectly.

Method:
  1. Load the 112-station ACORN-SAT list (lat/lon) and mark each station
     available or unavailable (18 unavailable per
     src.ingestion.bom_acornsat.ACORN_SAT_UNAVAILABLE_STATIONS).
  2. Point-in-polygon assign each station to its AAGIS region.
  3. Per region, count available / unavailable / total stations.
  4. Flag broadacre (Wheat-Sheep / High-Rainfall) regions with zero available
     stations (no direct station truth) or a single station (sparse).
  5. Surface the broadacre-relevant unavailable stations (the ones whose loss
     most degrades broadacre SILO validation, e.g. WA Wheatbelt, NSW Riverina).

The 18 unavailable are documented in bom_acornsat.py; three carry an explicit
"broadacre relevance: HIGH" note (008039, 008051 WA Wheatbelt; 073054 NSW
Riverina).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.bom_acornsat import ACORN_SAT_UNAVAILABLE_STATIONS
from src.log_utils import warn
from src.paths import DATA_PROCESSED, DATA_RAW

# ---------------------------------------------------------------------------
# Locations & constants
# ---------------------------------------------------------------------------

STATION_LIST_CSV: Path = DATA_RAW / "acorn_sat" / "station_list.csv"
AAGIS_GPKG: Path = DATA_PROCESSED / "aagis_regions_repaired.gpkg"

BROADACRE_ZONES: tuple[str, ...] = ("Wheat Sheep", "High Rainfall")
EXPECTED_N_STATIONS: int = 112
SPARSE_AVAILABLE_MAX: int = 1  # <= this many available -> "sparse"

# Broadacre-relevant unavailable stations (explicit HIGH note in bom_acornsat).
BROADACRE_RELEVANT_UNAVAILABLE: dict[str, str] = {
    "008039": "WA Wheatbelt",
    "008051": "WA Wheatbelt margin",
    "073054": "NSW Riverina",
}


# ---------------------------------------------------------------------------
# Loading / assignment
# ---------------------------------------------------------------------------


def load_stations(
    station_list_csv: str | Path = STATION_LIST_CSV,
    unavailable: frozenset[str] = ACORN_SAT_UNAVAILABLE_STATIONS,
) -> pd.DataFrame:
    """
    Load the ACORN-SAT station list and mark availability.

    Returns
    -------
    pandas.DataFrame
        Columns: ``station_id`` (str, 6-digit), ``name``, ``latitude``,
        ``longitude``, ``available`` (bool).
    """
    station_list_csv = Path(station_list_csv)
    if not station_list_csv.exists():
        raise FileNotFoundError(f"Station list not found: {station_list_csv}")

    df = pd.read_csv(station_list_csv, dtype={"station_id": str})
    df["station_id"] = df["station_id"].astype(str).str.strip().str.zfill(6)
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["available"] = ~df["station_id"].isin(set(unavailable))
    return df[["station_id", "name", "latitude", "longitude", "available"]]


def assign_stations_to_regions(
    stations: pd.DataFrame,
    aagis_gpkg: str | Path = AAGIS_GPKG,
) -> pd.DataFrame:
    """
    Point-in-polygon assign each station to its AAGIS region.

    Returns the station frame with added ``aagis_code`` and ``region_name``
    (NaN if a station falls outside every region).
    """
    import geopandas as gpd

    pts = gpd.GeoDataFrame(
        stations.copy(),
        geometry=gpd.points_from_xy(stations["longitude"], stations["latitude"]),
        crs="EPSG:4326",
    )
    regions = gpd.read_file(aagis_gpkg)
    if regions.crs is None:
        raise RuntimeError(f"AAGIS gpkg has no CRS: {aagis_gpkg}")
    if regions.crs.to_epsg() != 4326:
        regions = regions.to_crs(epsg=4326)
    regions = regions[["class", "name", "geometry"]].rename(
        columns={"class": "aagis_code", "name": "region_name"}
    )
    regions["aagis_code"] = regions["aagis_code"].astype(str).str.strip()
    regions["region_name"] = regions["region_name"].astype(str).str.strip()

    joined = gpd.sjoin(pts, regions, how="left", predicate="within")
    n_out = int(joined["aagis_code"].isna().sum())
    if n_out:
        warn(f"  {n_out} station(s) fall outside all AAGIS regions")
    return pd.DataFrame(joined.drop(columns=["geometry", "index_right"]))


# ---------------------------------------------------------------------------
# Coverage assessment
# ---------------------------------------------------------------------------


def compute_region_coverage(
    assigned: pd.DataFrame,
    region_mapping: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per-region station coverage over all 32 AAGIS regions.

    Parameters
    ----------
    assigned : output of :func:`assign_stations_to_regions`.
    region_mapping : the 32-region mapping (aagis_code, region_name, zone).

    Returns
    -------
    pandas.DataFrame
        One row per region: ``n_available``, ``n_unavailable``, ``n_total``,
        ``zone``, and boolean flags ``is_broadacre``, ``no_station``,
        ``sparse``. Regions with no station appear with zero counts.
    """
    avail = (
        assigned[assigned["available"]]
        .groupby("aagis_code")
        .size()
        .rename("n_available")
    )
    unavail = (
        assigned[~assigned["available"]]
        .groupby("aagis_code")
        .size()
        .rename("n_unavailable")
    )

    cov = region_mapping[["aagis_code", "region_name", "zone"]].copy()
    cov = cov.merge(avail.reset_index(), on="aagis_code", how="left")
    cov = cov.merge(unavail.reset_index(), on="aagis_code", how="left")
    cov["n_available"] = cov["n_available"].fillna(0).astype(int)
    cov["n_unavailable"] = cov["n_unavailable"].fillna(0).astype(int)
    cov["n_total"] = cov["n_available"] + cov["n_unavailable"]

    cov["is_broadacre"] = cov["zone"].isin(BROADACRE_ZONES)
    cov["no_station"] = cov["is_broadacre"] & (cov["n_available"] == 0)
    cov["sparse"] = (
        cov["is_broadacre"]
        & (cov["n_available"] > 0)
        & (cov["n_available"] <= SPARSE_AVAILABLE_MAX)
    )
    return cov.sort_values(["is_broadacre", "n_available"], ascending=[False, True])


def summarize(cov: pd.DataFrame, assigned: pd.DataFrame) -> dict:
    """Return a small summary dict for logging / the data quality report."""
    broad = cov[cov["is_broadacre"]]
    no_station = broad[broad["no_station"]]
    sparse = broad[broad["sparse"]]

    # Where would the broadacre-relevant unavailable stations have counted?
    relevant = assigned[assigned["station_id"].isin(BROADACRE_RELEVANT_UNAVAILABLE)][
        ["station_id", "name", "aagis_code", "region_name"]
    ]

    return {
        "n_available_total": int(assigned["available"].sum()),
        "n_unavailable_total": int((~assigned["available"]).sum()),
        "n_broadacre_regions": int(len(broad)),
        "broadacre_no_station": no_station["region_name"].tolist(),
        "broadacre_sparse": sparse["region_name"].tolist(),
        "broadacre_relevant_unavailable": relevant.to_dict("records"),
    }


__all__ = [
    "STATION_LIST_CSV",
    "AAGIS_GPKG",
    "BROADACRE_ZONES",
    "EXPECTED_N_STATIONS",
    "SPARSE_AVAILABLE_MAX",
    "BROADACRE_RELEVANT_UNAVAILABLE",
    "load_stations",
    "assign_stations_to_regions",
    "compute_region_coverage",
    "summarize",
]
