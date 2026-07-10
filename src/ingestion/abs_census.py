"""
ABS Agricultural Census 2020-21 — SA2-level ingestion.

Retrieves the ABS Agricultural Census 2020-21 cross-section at ASGS
Edition 3 region granularity (National + State + SA4 + SA3 + SA2),
filters to SA2 level for downstream region-importance weighting in
Pillar 4-5 (scope v4 §4.3).

Structural note: The 2020-21 Agricultural Census was the FINAL ABS
Agricultural Census (per ABS publication, July 2022). Future ABS
agricultural statistics use a modernised pipeline (Levy Payer Register
+ satellite crop mapping) released annually from 2022-23. Project 5
v1.0 freezes Census-derived weighting at this 2020-21 vintage. Future
extensions should incorporate the modernised pipeline if SA2 spatial
unit and 2022-23+ vintage are required.

Source:
    Australian Bureau of Statistics (ABS).
    Catalogue: Agricultural Commodities, Australia, 2020-21 financial year
    (previously cat. no. 7121.0).
    Released 26/07/2022.
    https://www.abs.gov.au/statistics/industry/agriculture/agricultural-commodities-australia/2020-21

URL pattern (verified via DevTools 2026-05-15):
    https://www.abs.gov.au/statistics/industry/agriculture/agricultural-commodities-australia/2020-21/AGCDCASGS202021.xlsx
    Size: ~3.87 MB

Data structure (verified empirically 2026-05-15):
    Workbook has 2 sheets:
        "Contents"  — metadata only, ignored on ingest
        "Table 1"   — single data table, long-form

    "Table 1" structure:
        Rows 1–6:  Workbook metadata (title, release info, table title)
        Row 7:     Header row
        Row 8+:    Data rows

    Header (row 7):
        A: Region code         (int; 0 = Australia, 9-digit = SA2)
        B: Region label        (str)
        C: Commodity code      (str, e.g. 'WHEAT_YIELD_F', 'AGCEREAL_AHAWHT_F')
        D: Commodity description (str, e.g. 'Cereal crops - Wheat for grain - Yield (t/ha)')
        E: Estimate
        F: Estimate - Relative Standard Error (Percent)
        G: Number of agricultural businesses
        H: Number of agricultural businesses - Relative Standard Error (Percent)

    Region hierarchy via Region code digit count (ABS ASGS Edition 3):
        0           -> National (Australia)
        1 digit     -> State / Territory
        3 digits    -> SA4 (Statistical Area 4)
        5 digits    -> SA3 (Statistical Area 3)
        9 digits    -> SA2 (Statistical Area 2)  <-- primary target

    Special values:
        '..'  -> not available  (treated as NA)
        'np'  -> not published (confidentiality)
        '-'   -> nil rounded

    Yield variables already provided by ABS (no derivation needed):
        WHEAT_YIELD_F   (t/ha)
        BARLEY_YIELD_F  (t/ha)
        CANOLA_YIELD_F  (t/ha)   (verified on inspection of canola section)
        ...

License: Creative Commons (per ABS Default Terms of Use).
    https://www.abs.gov.au/about/data-services/licensing
    Attribution: "Australian Bureau of Statistics (ABS)".
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from src.log_utils import log

# ----- Canonical configuration --------------------------------------------

ABS_AGCENSUS_URL = (
    "https://www.abs.gov.au/statistics/industry/agriculture/"
    "agricultural-commodities-australia/2020-21/AGCDCASGS202021.xlsx"
)

ABS_AGCENSUS_FILENAME = "AGCDCASGS202021.xlsx"
DATA_SHEET = "Table 1"
HEADER_ROW_INDEX = 6  # 0-indexed; in Excel terms this is row 7

# ABS Census NA conventions
ABS_NA_VALUES = ["..", "np", "-", "nil"]

# Commodity code -> per-commodity variable codes.
# The ABS schema names each commodity-variable combination separately as
# e.g. 'AGCEREAL_AHAWHT_F' (Wheat area), 'AGCEREAL_ATOWHT_F' (Wheat
# production), 'WHEAT_YIELD_F' (Wheat yield). These were observed in
# the XLSX inspection; codes verified for wheat/barley empirically, the
# canola variant pattern follows the same naming convention.
COMMODITY_CODES: dict[str, dict[str, str]] = {
    "wheat": {
        "area_ha": "AGCEREAL_AHAWHT_F",
        "production_t": "AGCEREAL_ATOWHT_F",
        "yield_t_ha": "WHEAT_YIELD_F",
    },
    "barley": {
        "area_ha": "AGCEREAL_AHABAR_F",
        "production_t": "AGCEREAL_ATOBAR_F",
        "yield_t_ha": "BARLEY_YIELD_F",
    },
    "canola": {
        # Canola is in ABS classification "Other crops - Oilseeds - Canola"
        # (verified via XLSX inspection 2026-05-15). The AGOTHCROP prefix
        # groups oilseeds under the "Other crops" category; yield variables
        # have their own namespace (CANOLA_YIELD_F) outside the AGOTHCROP
        # hierarchy.
        "area_ha": "AGOTHCROP_AHACAN_F",
        "production_t": "AGOTHCROP_ATOCAN_F",
        "yield_t_ha": "CANOLA_YIELD_F",
    },
}

# Browser-like User-Agent.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/octet-stream,*/*"
    ),
}


# ----- Download -----------------------------------------------------------


def abs_census_local_path(raw_dir: Path) -> Path:
    return Path(raw_dir) / ABS_AGCENSUS_FILENAME


def download_abs_census(raw_dir: Path) -> dict | None:
    """
    Idempotent download of the ABS Agricultural Census 2020-21 XLSX.

    Returns:
        - None if file already exists (skipped)
        - dict with stats on success
        - dict with ``error`` key on HTTP failure
    """
    dst = abs_census_local_path(raw_dir)
    if dst.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)

    tmp = dst.with_suffix(dst.suffix + ".part")
    log(f"  downloading {ABS_AGCENSUS_FILENAME} (~3.87 MB)")
    try:
        with requests.get(
            ABS_AGCENSUS_URL, headers=HTTP_HEADERS, stream=True, timeout=120
        ) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        fh.write(chunk)
    except requests.HTTPError as e:
        if tmp.exists():
            tmp.unlink()
        return {"error": f"HTTP {e.response.status_code}", "url": ABS_AGCENSUS_URL}
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        return {"error": str(e), "url": ABS_AGCENSUS_URL}

    tmp.rename(dst)
    return {"size_bytes": dst.stat().st_size, "url": ABS_AGCENSUS_URL}


# ----- Parsing ------------------------------------------------------------


# Canonical column rename (upstream -> snake_case)
_COLUMN_RENAME = {
    "Region code": "region_code",
    "Region label": "region_label",
    "Commodity code": "commodity_code",
    "Commodity description": "commodity_description",
    "Estimate": "estimate",
    "Estimate - Relative Standard Error (Percent)": "estimate_rse",
    "Number of agricultural businesses": "n_businesses",
    "Number of agricultural businesses - Relative Standard Error (Percent)": "n_businesses_rse",
}


def load_abs_census(xlsx_path: Path) -> pd.DataFrame:
    """
    Load the ABS Agricultural Census XLSX (sheet "Table 1") into a long-form
    DataFrame with canonical column names.

    Returns columns:
        region_code (int as str — preserved leading zeros NOT needed; ABS
                     uses integer codes without leading zeros, but stored
                     as object to avoid mixing types with the special
                     'Total' rows if any),
        region_label (str),
        commodity_code (str),
        commodity_description (str),
        estimate (float, NA-aware),
        estimate_rse (float, NA-aware),
        n_businesses (float, NA-aware),
        n_businesses_rse (float, NA-aware)

    ABS special-value handling: '..', 'np', '-' are coerced to NaN.
    """
    xlsx_path = Path(xlsx_path)
    log(f"  parsing {xlsx_path.name} (sheet='{DATA_SHEET}')")

    # Read the entire sheet; skip the 6 leading metadata rows so row 7 (index 6)
    # becomes the header.
    raw = pd.read_excel(
        xlsx_path,
        sheet_name=DATA_SHEET,
        header=HEADER_ROW_INDEX,
        engine="openpyxl",
        na_values=ABS_NA_VALUES,
        keep_default_na=True,  # ABS '..' / 'np' captured by na_values; safer than full keep_default_na=False
        dtype={
            "Region code": "object"
        },  # preserve as string to avoid int cast surprises
    )

    # ABS XLSX headers ship with surrounding whitespace (e.g. ' Estimate ').
    # Normalise column names to canonical (stripped) form.
    raw.columns = [str(c).strip() for c in raw.columns]

    # Strip whitespace from string columns defensively.
    for c in raw.columns:
        if raw[c].dtype == object:
            raw[c] = raw[c].astype(str).str.strip()
            raw[c] = raw[c].replace({"nan": pd.NA, "NaN": pd.NA, "None": pd.NA})

    # Rename to canonical snake_case
    missing = set(_COLUMN_RENAME) - set(raw.columns)
    if missing:
        raise RuntimeError(
            f"Unexpected ABS Census schema. Missing columns: {missing}. "
            f"Got: {list(raw.columns)}"
        )
    df = raw.rename(columns=_COLUMN_RENAME)

    # Numeric coercion for the value columns
    for col in ("estimate", "estimate_rse", "n_businesses", "n_businesses_rse"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # region_code as str (so '0' for Australia and '101011001' for SA2
    # are uniformly stringy)
    df["region_code"] = df["region_code"].astype(str).str.strip()

    log(
        f"    rows: {len(df):,}, regions: {df['region_code'].nunique():,}, "
        f"commodity codes: {df['commodity_code'].nunique():,}"
    )
    return df


# ----- Region hierarchy ---------------------------------------------------


def classify_region_level(region_code: str) -> str:
    """
    Classify an ABS region code into ASGS Edition 3 hierarchy level
    based on its digit count.

    Returns: 'national', 'state', 'sa4', 'sa3', 'sa2', or 'unknown'.
    """
    s = str(region_code).strip()
    # Strip any trailing '.0' artefact from int->str conversion
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit():
        return "unknown"
    n = len(s)
    if n == 1 and s == "0":
        return "national"
    if n == 1:
        return "state"
    if n == 3:
        return "sa4"
    if n == 5:
        return "sa3"
    if n == 9:
        return "sa2"
    return "unknown"


def add_region_level_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["region_level"] = df["region_code"].map(classify_region_level)
    return df


# ----- Commodity extraction (SA2 + supplementary national/state) ----------


def extract_commodity_wide(
    df_long: pd.DataFrame,
    commodity: str,
    region_level: str = "sa2",
) -> pd.DataFrame:
    """
    Reshape long-form ABS rows for one commodity into wide form, filtered
    to a single region_level.

    Output columns:
        region_code, region_label, area_ha, production_t, yield_t_ha,
        area_rse, production_rse, yield_rse,
        n_businesses_area, n_businesses_production, n_businesses_yield

    NB: ABS publishes 'Number of agricultural businesses' per
    commodity-variable; we keep one column per role for traceability.
    """
    if commodity not in COMMODITY_CODES:
        raise ValueError(
            f"Unknown commodity '{commodity}'; "
            f"expected one of {list(COMMODITY_CODES)}"
        )

    codes = COMMODITY_CODES[commodity]
    target_codes = list(codes.values())

    # Validate target codes exist in the data
    available = set(df_long["commodity_code"].dropna().unique())
    missing = [c for c in target_codes if c not in available]
    if missing:
        # Help debug: suggest similar codes (commodity stem substring match)
        stem = commodity.upper()[:4]
        suggestions = sorted(c for c in available if stem in str(c).upper())[:10]
        raise RuntimeError(
            f"ABS commodity codes missing for '{commodity}': {missing}. "
            f"Suggested codes containing '{stem}' substring: {suggestions}. "
            f"Total available codes: {len(available)}"
        )

    # Filter to target region level
    df_lvl = df_long[df_long["region_level"] == region_level].copy()
    if df_lvl.empty:
        raise RuntimeError(f"No rows for region_level='{region_level}'")

    # Filter to the 3 target commodity codes
    sub = df_lvl[df_lvl["commodity_code"].isin(target_codes)].copy()

    # Build wide form via role-tagged pivot.
    # First map commodity_code -> role
    code_to_role = {v: k for k, v in codes.items()}
    sub["role"] = sub["commodity_code"].map(code_to_role)

    # Role-based rename maps for the rse / n_businesses pivots
    rse_rename = {
        "area_ha": "area_rse",
        "production_t": "production_rse",
        "yield_t_ha": "yield_rse",
    }
    nb_rename = {
        "area_ha": "n_businesses_area",
        "production_t": "n_businesses_production",
        "yield_t_ha": "n_businesses_yield",
    }

    # Pivot estimate / RSE / n_businesses on role
    val_wide = sub.pivot_table(
        index=["region_code", "region_label"],
        columns="role",
        values="estimate",
        aggfunc="first",
    )
    rse_wide = sub.pivot_table(
        index=["region_code", "region_label"],
        columns="role",
        values="estimate_rse",
        aggfunc="first",
    ).rename(columns=rse_rename)
    nb_wide = sub.pivot_table(
        index=["region_code", "region_label"],
        columns="role",
        values="n_businesses",
        aggfunc="first",
    ).rename(columns=nb_rename)

    out = val_wide.join(rse_wide).join(nb_wide).reset_index()

    # Column ordering (only those that exist; defensive)
    ordered = [
        "region_code",
        "region_label",
        "area_ha",
        "production_t",
        "yield_t_ha",
        "area_rse",
        "production_rse",
        "yield_rse",
        "n_businesses_area",
        "n_businesses_production",
        "n_businesses_yield",
    ]
    keep = [c for c in ordered if c in out.columns]
    out = out[keep].sort_values("region_code").reset_index(drop=True)
    return out


# ----- Sanity checks ------------------------------------------------------


def sanity_check_national_yield(
    df_long: pd.DataFrame,
    yield_code: str,
    expected_value: float,
    tolerance_frac: float = 0.05,
) -> dict:
    """
    Verify that the national-row (region_code='0') value for a given
    yield commodity_code matches an expected value within tolerance.

    Returned by inspection of the XLSX on 2026-05-15:
        WHEAT_YIELD_F national = 2.5 (t/ha)
        BARLEY_YIELD_F national = 2.7 (t/ha)
    """
    df_nat = df_long[
        (df_long["region_code"] == "0") & (df_long["commodity_code"] == yield_code)
    ]
    if df_nat.empty:
        return {"valid": False, "reason": f"no national row for {yield_code}"}
    actual = float(df_nat["estimate"].iloc[0])
    diff = (actual - expected_value) / expected_value if expected_value else None
    within = abs(diff) <= tolerance_frac if diff is not None else False
    return {
        "valid": True,
        "yield_code": yield_code,
        "expected": expected_value,
        "actual": actual,
        "frac_diff": diff,
        "within_tolerance": within,
    }
