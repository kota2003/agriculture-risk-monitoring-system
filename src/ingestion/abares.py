"""
ABARES Farm Data Portal — Historical Estimates ingestion.

Retrieves the three "Historical Estimates" bulk-download CSVs that
underpin the ABARES Farm Data Portal:

    1. fdp-regional-historical.csv  ~9.6 MB   AAGIS region level   PRIMARY
    2. fdp-national-historical.csv  ~1.5 MB   National level       sanity-check
    3. fdp-state-historical.csv     ~11.4 MB  State level          cross-validation

The Regional CSV is the primary source for Project 5 scope v4 §3.1
yield data (AAGIS region × commodity × annual, 1990–2024). National and
state CSVs are retrieved for sanity-check (national vs sum-of-regional)
and cross-validation.

Source:
    ABARES Farm Data Portal
    https://www.agriculture.gov.au/abares/data/farm-data-portal

URL pattern (verified via DevTools 2026-05-15):
    https://www.agriculture.gov.au/sites/default/files/documents/<filename>

Distinct schemas across the three levels (verified empirically 2026-05-15):

    Regional:  Variable, Year, ABARES region, Value, RSE
               -> spatial dim: ABARES region (32 values, broadacre aggregate
                  per region, no Industry breakdown at this level)

    National:  Variable, Year, Value, RSE, Industry
               -> industry dim only: Industry takes 7 values:
                  ['All Broadacre', 'Beef', 'Cropping', 'Dairy', 'Mixed',
                   'Sheep', 'Sheep-Beef']
                  The 'All Broadacre' value is the appropriate counterpart
                  to the regional (broadacre-aggregate) values for sanity
                  checks.

    State:     Variable, Year, Value, RSE, State, Industry
               -> spatial dim: State (e.g. 'New South Wales') x
                  industry dim: Industry (same 7 values)

Data semantics:
    Variable: free-text label including unit, e.g. "Wheat area sown (ha)".
              136 distinct variables in the regional CSV (financial,
              physical, demographic).
    Year:     ABARES financial year ending year (integer; 1989-90 -> 1990).
              Range: 1990–2024 (35 years).
    Value:    numeric. May be 0 for sparse cells.
    RSE:      Relative Standard Error (%). May be blank for cells where
              ABARES does not publish a precision estimate. Preserve as NA;
              do not coerce to 0 (Project 4 lesson 9).

License: Creative Commons (per ABARES standard data licensing).
    https://www.agriculture.gov.au/abares/products/citations
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from src.io_utils import read_csv_safe
from src.log_utils import log

# ----- Canonical configuration --------------------------------------------

ABARES_BASE_URL = "https://www.agriculture.gov.au/sites/default/files/documents"

FDP_FILES: dict[str, dict] = {
    "regional": {
        "filename": "fdp-regional-historical.csv",
        "size_mb_approx": 9.6,
        "role": "primary",
        "spatial_unit": "ABARES region",
        # Per-level upstream schema (column names exactly as ABARES ships them).
        "upstream_columns": ["Variable", "Year", "ABARES region", "Value", "RSE"],
        # Per-level rename map -> project-canonical snake_case
        "rename": {
            "Variable": "variable",
            "Year": "year",
            "ABARES region": "region",
            "Value": "value",
            "RSE": "rse",
        },
    },
    "national": {
        "filename": "fdp-national-historical.csv",
        "size_mb_approx": 1.5,
        "role": "sanity-check",
        "spatial_unit": "Australia",
        "upstream_columns": ["Variable", "Year", "Value", "RSE", "Industry"],
        "rename": {
            "Variable": "variable",
            "Year": "year",
            "Value": "value",
            "RSE": "rse",
            "Industry": "industry",
        },
    },
    "state": {
        "filename": "fdp-state-historical.csv",
        "size_mb_approx": 11.4,
        "role": "cross-validation",
        "spatial_unit": "State",
        "upstream_columns": ["Variable", "Year", "Value", "RSE", "State", "Industry"],
        "rename": {
            "Variable": "variable",
            "Year": "year",
            "Value": "value",
            "RSE": "rse",
            "State": "state",
            "Industry": "industry",
        },
    },
}

# The Industry value that represents the broadacre aggregate counterpart
# to the regional CSV's per-region values. Used as a filter when comparing
# national / state aggregates against regional sums.
BROADACRE_AGGREGATE_INDUSTRY = "All Broadacre"

# Browser-like User-Agent.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


# ----- Download -----------------------------------------------------------


def fdp_url(level: str) -> str:
    if level not in FDP_FILES:
        raise ValueError(
            f"Unknown FDP level '{level}'; expected one of {list(FDP_FILES)}"
        )
    return f"{ABARES_BASE_URL}/{FDP_FILES[level]['filename']}"


def fdp_local_path(raw_dir: Path, level: str) -> Path:
    return Path(raw_dir) / FDP_FILES[level]["filename"]


def download_fdp_csv(level: str, raw_dir: Path) -> dict | None:
    """
    Idempotent download of one FDP CSV file.

    Returns:
        - None if file already exists (skipped)
        - dict with stats on success
        - dict with ``error`` key on HTTP failure
    """
    dst = fdp_local_path(raw_dir, level)
    if dst.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)

    url = fdp_url(level)
    tmp = dst.with_suffix(dst.suffix + ".part")
    log(
        f"  downloading {level}: {FDP_FILES[level]['filename']} "
        f"(~{FDP_FILES[level]['size_mb_approx']} MB)"
    )
    try:
        with requests.get(url, headers=HTTP_HEADERS, stream=True, timeout=120) as resp:
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

    tmp.rename(dst)
    return {"size_bytes": dst.stat().st_size, "url": url}


# ----- Parsing ------------------------------------------------------------


def _normalise_columns(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Validate upstream schema for the given level and rename to canonical."""
    spec = FDP_FILES[level]
    expected = set(spec["upstream_columns"])
    actual = set(df.columns)
    missing = expected - actual
    if missing:
        raise RuntimeError(
            f"Unexpected ABARES FDP schema for level '{level}'. "
            f"Missing columns: {missing}. Got: {list(df.columns)}. "
            f"Expected: {spec['upstream_columns']}"
        )
    return df.rename(columns=spec["rename"])


def load_fdp_csv(csv_path: Path, level: str) -> pd.DataFrame:
    """
    Load one FDP CSV at the given level (regional / national / state).

    Returns a normalised long-form DataFrame. Always has columns:
        variable (str), year (Int64), value (float, NA-aware),
        rse (float, NA-aware)
    Plus level-specific dimension columns:
        regional -> region (str)
        national -> industry (str)
        state    -> state (str), industry (str)
    """
    csv_path = Path(csv_path)
    log(f"  parsing {csv_path.name} (level={level})")
    df = read_csv_safe(csv_path)
    df = _normalise_columns(df, level)

    # Numeric coercion
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["rse"] = pd.to_numeric(df["rse"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    # Strip whitespace defensively for all str cols
    df["variable"] = df["variable"].astype(str).str.strip()
    for str_col in ("region", "industry", "state"):
        if str_col in df.columns:
            df[str_col] = df[str_col].astype(str).str.strip()

    # Concise diagnostic line
    parts = [
        f"rows: {len(df):,}",
        f"years: {df['year'].min()}–{df['year'].max()}",
        f"variables: {df['variable'].nunique()}",
    ]
    if "region" in df.columns:
        parts.append(f"regions: {df['region'].nunique()}")
    if "industry" in df.columns:
        parts.append(f"industries: {df['industry'].nunique()}")
    if "state" in df.columns:
        parts.append(f"states: {df['state'].nunique()}")
    log("    " + ", ".join(parts))
    return df


# ----- Commodity extraction (regional CSV only) ---------------------------


# Canonical (commodity, role) -> ABARES Variable label.
# Verified visible in 2026-05-15 CSV inspection.
COMMODITY_VARIABLES: dict[str, dict[str, str]] = {
    "wheat": {
        "area_ha": "Wheat area sown (ha)",
        "production_t": "Wheat produced (t)",
    },
    "barley": {
        "area_ha": "Barley area sown (ha)",
        "production_t": "Barley produced (t)",
    },
    "canola": {
        "area_ha": "Canola area sown (ha)",
        "production_t": "Canola produced (t)",
    },
}


def extract_commodity_wide(
    df_regional: pd.DataFrame,
    commodity: str,
) -> pd.DataFrame:
    """
    Reshape regional long-form rows for a single commodity into wide form
    with derived yield (t/ha).

    Output columns:
        region (str), year (int), area_ha (float), production_t (float),
        yield_t_ha (float), area_rse (float), production_rse (float)

    yield_t_ha is computed as production_t / area_ha, with NaN where
    either input is NaN or area_ha is 0.
    """
    if commodity not in COMMODITY_VARIABLES:
        raise ValueError(
            f"Unknown commodity '{commodity}'; "
            f"expected one of {list(COMMODITY_VARIABLES)}"
        )
    var_area = COMMODITY_VARIABLES[commodity]["area_ha"]
    var_prod = COMMODITY_VARIABLES[commodity]["production_t"]

    available_vars = set(df_regional["variable"].unique())
    missing = {v for v in (var_area, var_prod) if v not in available_vars}
    if missing:
        lower_to_orig = {v.lower(): v for v in available_vars}
        suggestions = [lower_to_orig.get(v.lower()) for v in missing]
        sample = [v for v in available_vars if commodity.split()[0].capitalize() in v][
            :5
        ]
        raise RuntimeError(
            f"ABARES variables missing for commodity '{commodity}': {missing}. "
            f"Case-insensitive suggestions: {suggestions}. "
            f"Sample variables with stem: {sample}"
        )

    sub = df_regional[df_regional["variable"].isin([var_area, var_prod])].copy()

    wide_val = sub.pivot_table(
        index=["region", "year"],
        columns="variable",
        values="value",
        aggfunc="first",
    ).rename(columns={var_area: "area_ha", var_prod: "production_t"})

    wide_rse = sub.pivot_table(
        index=["region", "year"],
        columns="variable",
        values="rse",
        aggfunc="first",
    ).rename(columns={var_area: "area_rse", var_prod: "production_rse"})

    wide = wide_val.join(wide_rse).reset_index()

    safe_area = wide["area_ha"].where(wide["area_ha"] > 0)
    wide["yield_t_ha"] = wide["production_t"] / safe_area

    wide = wide[
        [
            "region",
            "year",
            "area_ha",
            "production_t",
            "yield_t_ha",
            "area_rse",
            "production_rse",
        ]
    ]
    wide = wide.sort_values(["region", "year"]).reset_index(drop=True)
    return wide


# ----- Sanity checks ------------------------------------------------------


def sanity_check_regional_vs_national(
    df_regional: pd.DataFrame,
    df_national: pd.DataFrame,
    variable: str,
    industry: str = BROADACRE_AGGREGATE_INDUSTRY,
    tolerance_frac: float = 0.05,
) -> dict:
    """
    For a given Variable (e.g. "Wheat produced (t)"), compare the sum of
    regional values against the national value (filtered by Industry =
    "All Broadacre"), per year.

    The regional CSV publishes broadacre-aggregate values per AAGIS
    region (no Industry breakdown), so the appropriate national
    counterpart is the Industry='All Broadacre' value.

    Returns a summary dict with the per-year discrepancy distribution.
    A discrepancy within ±5% is treated as consistent (some divergence
    is expected because ABARES uses survey-weighted aggregation, and
    national vs regional weighting schemes may differ slightly).
    """
    reg = df_regional[df_regional["variable"] == variable]
    nat = df_national[
        (df_national["variable"] == variable) & (df_national["industry"] == industry)
    ]
    if reg.empty or nat.empty:
        return {
            "valid": False,
            "reason": f"variable '{variable}' / industry '{industry}' "
            f"missing in one of regional / national",
        }

    reg_sum_by_year = reg.groupby("year")["value"].sum(min_count=1)
    nat_by_year = nat.groupby("year")["value"].sum(min_count=1)

    common_years = sorted(set(reg_sum_by_year.index) & set(nat_by_year.index))
    if not common_years:
        return {"valid": False, "reason": "no overlapping years"}

    diffs = []
    for y in common_years:
        r = reg_sum_by_year.get(y)
        n = nat_by_year.get(y)
        if pd.isna(r) or pd.isna(n) or n == 0:
            continue
        frac = (r - n) / n
        diffs.append((y, r, n, frac))

    if not diffs:
        return {"valid": False, "reason": "all comparisons NA or zero"}

    fracs = pd.Series([d[3] for d in diffs])
    within_tol = int((fracs.abs() <= tolerance_frac).sum())
    return {
        "valid": True,
        "variable": variable,
        "industry_filter": industry,
        "n_years_compared": len(diffs),
        "n_years_within_tolerance": within_tol,
        "median_frac_diff": float(fracs.median()),
        "max_abs_frac_diff": float(fracs.abs().max()),
        "tolerance_frac": tolerance_frac,
    }


def cross_check_aagis_region_names(
    df_regional: pd.DataFrame,
    aagis_gpkg_path: Path,
) -> dict:
    """
    Verify that the ABARES region names in the FDP CSV exactly match the
    region names in the AAGIS shapefile from s01.

    Mismatches will block downstream spatial joins. This check catches
    any upstream drift in naming conventions.
    """
    try:
        import geopandas as gpd
    except ImportError:
        return {"valid": False, "reason": "geopandas not available"}

    if not Path(aagis_gpkg_path).exists():
        return {"valid": False, "reason": f"aagis file not found: {aagis_gpkg_path}"}

    gdf = gpd.read_file(aagis_gpkg_path)
    region_field_candidates = [
        c for c in gdf.columns if "region" in c.lower() or "aagis" in c.lower()
    ]
    if not region_field_candidates:
        return {
            "valid": False,
            "reason": f"no region-like field in {list(gdf.columns)}",
        }

    region_field = next(
        (c for c in region_field_candidates if c.lower() == "region"),
        region_field_candidates[0],
    )
    aagis_names = set(gdf[region_field].astype(str).str.strip().unique())
    fdp_names = set(df_regional["region"].astype(str).str.strip().unique())

    only_in_fdp = fdp_names - aagis_names
    only_in_aagis = aagis_names - fdp_names
    common = fdp_names & aagis_names

    return {
        "valid": True,
        "aagis_field_used": region_field,
        "n_aagis_regions": len(aagis_names),
        "n_fdp_regions": len(fdp_names),
        "n_matching": len(common),
        "only_in_fdp": sorted(only_in_fdp),
        "only_in_aagis": sorted(only_in_aagis),
    }
