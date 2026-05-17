"""
BoM ACORN-SAT (Australian Climate Observations Reference Network -
Surface Air Temperature) ingestion.

Retrieves homogenised daily Tmax/Tmin records for the 112 ACORN-SAT
reference stations. The dataset is used for **SILO sanity-checking
only** (scope v4 sec. 4.2): regional SILO aggregates are compared to
the homogenised station truth to confirm SILO's interpolated grids are
physically plausible. ACORN-SAT is NEVER used as a primary input to
Pillars 3-5 (yield models), and is NEVER substituted for SILO grid data.

Source:
    Australian Bureau of Meteorology (BoM).
    https://www.bom.gov.au/climate/data/acorn-sat/

Access pattern (verified via DevTools 2026-05-15):
    Machine-readable station list (CSV):
        https://www.bom.gov.au/climate/change/acorn-sat/map/stations-acorn-sat.txt
    Per-station daily CSVs:
        https://www.bom.gov.au/climate/change/hqsites/data/temp/<var>.<id>.daily.csv
    Where:
        <var> = "tmin" or "tmax"
        <id>  = 6-digit zero-padded BoM station number (e.g. 023000 for Adelaide)

Pipeline:
    1. Fetch the machine-readable station list CSV and cache as
       data/raw/acorn_sat/station_list.csv for reproducibility.
    2. For each (station, variable) pair, download the daily CSV to
       data/processed/bom_acornsat/<variable>/<station_id>.daily.csv.
       Stations in ACORN_SAT_UNAVAILABLE_STATIONS are skipped without
       attempting download (per Master-grade discipline parallel to
       SILO evap_pan pre-1970 handling in src/ingestion/silo.py).
    3. Validate basic structure (header presence, date column, expected
       row count for a ~115-year record).

The total payload is ~50-100 MB across ~188 files; runtime is a few
minutes on a typical broadband connection.

License: Australian Bureau of Meteorology Default Terms of Use.
    https://www.bom.gov.au/other/copyright.shtml
    Attribution required.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from src.log_utils import log, warn

# ----- Canonical configuration --------------------------------------------

ACORN_SAT_STATION_LIST_URL = (
    "https://www.bom.gov.au/climate/change/acorn-sat/map/stations-acorn-sat.txt"
)

ACORN_SAT_CSV_BASE_URL = "https://www.bom.gov.au/climate/change/hqsites/data/temp"

ACORN_SAT_VARIABLES: tuple[str, ...] = ("tmin", "tmax")
EXPECTED_N_STATIONS = 112

# ---------------------------------------------------------------------------
# Stations listed in the ACORN-SAT 112-network metadata but for which BoM
# does not publish a daily homogenised CSV at the canonical hqsites URL.
#
# Confirmed unavailable by HTTP 404 across all four station-id zero-padding
# variants (2012, 02012, 002012, 0002012) on 2026-05-15. This is a
# structural data-publish gap on the BoM side, not a URL-pattern issue.
#
# Master-grade discipline (cf. SILO evap_pan pre-1970 handling in
# src/ingestion/silo.py): these stations are skipped before any download
# attempt, so they appear as "skipped (unavailable)" in the summary rather
# than as errors. Their absence is documented for scope v4 sec. 4.2
# (SILO sanity-check coverage of broadacre regions) in PROJECT_LOG at
# Phase 01 closure.
# ---------------------------------------------------------------------------
ACORN_SAT_UNAVAILABLE_STATIONS: frozenset[str] = frozenset(
    {
        "002012",  # WA Kimberley
        "005026",  # WA Pilbara
        "008039",  # WA Wheatbelt   - broadacre relevance: HIGH
        "008051",  # WA Wheatbelt margin - broadacre relevance: HIGH
        "009510",  # WA SW coast
        "009741",  # WA south coast
        "010579",  # WA south
        "017031",  # SA arid interior
        "023090",  # SA Adelaide region (urban)
        "030045",  # QLD NW inland
        "046037",  # NSW far NW (arid)
        "046043",  # NSW interior
        "059040",  # NSW coast
        "060139",  # NSW
        "066062",  # NSW (likely Sydney Observatory Hill, urban)
        "073054",  # NSW Riverina    - broadacre relevance: HIGH
        "086071",  # VIC (likely Melbourne Regional Office, urban)
        "094010",  # TAS island
    }
)


# Browser-like header to avoid BoM site blocking generic Python User-Agent.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


# ----- Station list (machine-readable CSV) --------------------------------


# Canonical column name -> list of source-column synonyms accepted from BoM.
# Lower-case match; the first synonym found in the upstream header wins.
_CANONICAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "station_id": ("stn_num", "stnnum", "station_id", "number", "id"),
    "name": ("stn_name", "stnname", "station_name", "name"),
    "latitude": ("lat", "latitude"),
    "longitude": ("lon", "lng", "longitude"),
    "elevation_m": ("elevation", "elevation_m", "elev"),
    "start_year": ("start", "start_year", "first_year"),
}


def _resolve_columns(upstream_columns: list[str]) -> dict[str, str]:
    """Map upstream column names to project-canonical names."""
    lower_to_orig = {c.lower(): c for c in upstream_columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical, synonyms in _CANONICAL_COLUMNS.items():
        match = None
        for syn in synonyms:
            if syn.lower() in lower_to_orig:
                match = lower_to_orig[syn.lower()]
                break
        if match is None:
            missing.append(canonical)
        else:
            resolved[canonical] = match
    if missing:
        raise RuntimeError(
            f"Unexpected ACORN-SAT station list schema. Could not locate "
            f"upstream columns for canonical names {missing}. "
            f"Got upstream columns: {upstream_columns}."
        )
    return resolved


def fetch_station_list(cache_path: Path | None = None) -> pd.DataFrame:
    """
    Fetch the ACORN-SAT 112-station list from the BoM machine-readable endpoint.

    Returns a DataFrame with columns:
        station_id, name, latitude, longitude, elevation_m, start_year
    """
    if cache_path is not None and Path(cache_path).exists():
        log(f"Using cached station list at {cache_path}")
        return pd.read_csv(cache_path, dtype={"station_id": str})

    log(f"Fetching ACORN-SAT station list from {ACORN_SAT_STATION_LIST_URL}")
    resp = requests.get(ACORN_SAT_STATION_LIST_URL, headers=HTTP_HEADERS, timeout=60)
    resp.raise_for_status()

    df_raw = pd.read_csv(io.StringIO(resp.text))
    log(f"  parsed {len(df_raw)} rows from BoM endpoint")
    log(f"  upstream columns: {list(df_raw.columns)}")

    col_map = _resolve_columns(list(df_raw.columns))
    df = pd.DataFrame(
        {canonical: df_raw[upstream] for canonical, upstream in col_map.items()}
    )

    df["station_id"] = df["station_id"].astype(int).map(lambda n: f"{n:06d}")
    df["start_year"] = df["start_year"].astype(int)
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["elevation_m"] = df["elevation_m"].astype(float)

    if len(df) != EXPECTED_N_STATIONS:
        warn(
            f"Got {len(df)} stations, expected {EXPECTED_N_STATIONS}. "
            f"BoM may have updated the network; manual review recommended."
        )

    if cache_path is not None:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)
        log(f"  cached to {cache_path}")

    return df


def is_unavailable_station(station_id: str) -> bool:
    """
    Return True if the station has no published daily CSV at BoM hqsites.

    See ACORN_SAT_UNAVAILABLE_STATIONS for the list and rationale.
    """
    sid = f"{int(station_id):06d}"
    return sid in ACORN_SAT_UNAVAILABLE_STATIONS


# ----- Per-station CSV download ------------------------------------------


def acornsat_csv_url(variable: str, station_id: str) -> str:
    if variable not in ACORN_SAT_VARIABLES:
        raise ValueError(
            f"Unknown variable '{variable}'; expected one of {ACORN_SAT_VARIABLES}"
        )
    sid = f"{int(station_id):06d}"
    return f"{ACORN_SAT_CSV_BASE_URL}/{variable}.{sid}.daily.csv"


def acornsat_local_path(processed_dir: Path, variable: str, station_id: str) -> Path:
    sid = f"{int(station_id):06d}"
    return Path(processed_dir) / "bom_acornsat" / variable / f"{sid}.daily.csv"


def download_one_csv(variable: str, station_id: str, dst_path: Path) -> dict | None:
    """
    Idempotent download of one (variable, station) CSV.

    Returns:
        - dict with ``skipped_reason="unavailable"`` for known-unavailable
          stations (ACORN_SAT_UNAVAILABLE_STATIONS), without attempting any HTTP.
        - None if the file already exists (idempotent skip)
        - dict with stats on success
        - dict with ``error`` key on HTTP failure
    """
    # Pre-download skip for known-unavailable stations.
    if is_unavailable_station(station_id):
        return {"skipped_reason": "unavailable"}

    dst_path = Path(dst_path)
    if dst_path.exists():
        return None
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    url = acornsat_csv_url(variable, station_id)
    tmp = dst_path.with_suffix(dst_path.suffix + ".part")
    try:
        with requests.get(url, headers=HTTP_HEADERS, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        fh.write(chunk)
    except requests.HTTPError as e:
        if tmp.exists():
            tmp.unlink()
        return {"error": f"HTTP {e.response.status_code}", "url": url}
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        return {"error": str(e), "url": url}

    tmp.rename(dst_path)
    return {"size_bytes": dst_path.stat().st_size, "url": url}


def validate_csv(csv_path: Path) -> dict:
    """Light structural validation of a downloaded per-station CSV."""
    csv_path = Path(csv_path)
    size_bytes = csv_path.stat().st_size
    if size_bytes < 100:
        return {"valid": False, "reason": f"too small ({size_bytes} bytes)"}

    df = None
    for skip in (1, 0, 2):
        try:
            df = pd.read_csv(csv_path, skiprows=skip)
            if len(df) >= 100:
                break
        except Exception:
            continue

    if df is None or len(df) < 100:
        return {"valid": False, "reason": "insufficient rows or unparseable"}

    first_col = df.iloc[:, 0].astype(str)
    if not first_col.str.match(r"\d{4}-\d{2}-\d{2}").any():
        return {"valid": False, "reason": "first column does not look like dates"}

    return {
        "valid": True,
        "n_rows": int(len(df)),
        "first_date": str(first_col.iloc[0]),
        "last_date": str(first_col.iloc[-1]),
        "size_bytes": size_bytes,
    }


# ----- Driver -------------------------------------------------------------


def ingest_all_stations(
    stations: pd.DataFrame,
    processed_dir: Path,
    variables: tuple[str, ...] = ACORN_SAT_VARIABLES,
) -> dict:
    """
    Download all (station, variable) CSVs sequentially.

    Returns per-variable summary dict with counts for done, skipped
    (already-downloaded), skipped (unavailable), and errors.
    """
    summary = {
        v: {
            "done": 0,
            "skipped_already_done": 0,
            "skipped_unavailable": 0,
            "errors": [],
            "total_bytes": 0,
        }
        for v in variables
    }
    total_units = len(stations) * len(variables)
    log(
        f"ACORN-SAT ingestion: {len(stations)} stations x "
        f"{len(variables)} variables = {total_units} files"
    )

    with tqdm(total=total_units, desc="ACORN-SAT", unit="file") as pbar:
        for variable in variables:
            for _, row in stations.iterrows():
                sid = row["station_id"]
                dst = acornsat_local_path(processed_dir, variable, sid)
                result = download_one_csv(variable, sid, dst)
                if result is None:
                    summary[variable]["skipped_already_done"] += 1
                elif "skipped_reason" in result:
                    summary[variable]["skipped_unavailable"] += 1
                elif "error" in result:
                    summary[variable]["errors"].append({"station_id": sid, **result})
                else:
                    summary[variable]["done"] += 1
                    summary[variable]["total_bytes"] += result["size_bytes"]
                pbar.update(1)

    return summary
