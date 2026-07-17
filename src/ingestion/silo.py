"""
SILO (Long Paddock) gridded data ingestion.

Retrieves SILO daily gridded climate data via the AWS Public Data
endpoint and persists cropping-masked NetCDF files at the SILO 0.05 deg
grid resolution. The cropping mask (data/processed/cropping_mask.nc,
variable `cropping_mask_t005`) determines which grid cells are kept;
the rest are written as NaN so that disk size stays manageable under
zlib compression.

Source:
    Queensland Government, LongPaddock SILO.
    https://www.longpaddock.qld.gov.au/silo/gridded-data/
    https://registry.opendata.aws/silo/
    Data: CC BY 4.0.

Access pattern:
    Each (variable, year) is a single annual NetCDF file containing all
    daily grids for that year. We fetch via HTTPS from the AWS S3 bucket
    `silo-open-data` (no auth required).

    URL pattern (verified at longpaddock.qld.gov.au/silo/gridded-data/):
        https://s3-ap-southeast-2.amazonaws.com/silo-open-data/Official/
            annual/<variable>/<year>.<variable>.nc

    Each daily-variable file is approximately 410 MB.

Pipeline per (variable, year):
    1. Download raw annual NetCDF to a temporary location.
    2. Open with xarray, validate grid shape matches the SILO spec
       (lat=681, lon=841), confirm CF time axis.
    3. Apply cropping mask (where=mask, non-cropping -> NaN), retaining
       the full spatial structure.
    4. Persist masked NetCDF to data/processed/silo/<variable>/<year>.nc
       with zlib compression.
    5. Delete the raw download to keep disk usage bounded.

Variable-specific effective periods (Master-grade discipline):
    Per SILO documentation (longpaddock.qld.gov.au/silo/about/climate-variables/):
        "Evaporation data prior to 1970 ... are all long term averages."
    Therefore, `evap_pan` is treated as **observed only from 1970 onward**.
    Years 1961-1969 are skipped to avoid introducing a structural break
    at 1970 into the time series, which would distort Pillar 1 SPEI and
    Pillar 2 EVT analyses (scope v4 sec. 5.1, sec. 5.2).

    Per the same SILO documentation:
        "Temperatures, Solar Radiation, and Vapour Pressure data prior to
         1957 are all long term averages."
    Our analytical period starts at 1961 (scope v4 sec. 3.3), so these
    variables (max_temp, min_temp, vp, radiation) are unaffected.

    `daily_rain` is observational from BoM stations from 1889 (no
    long-term-average period in our window).
"""

from __future__ import annotations

from pathlib import Path

import requests
import xarray as xr
from tqdm import tqdm

from src.log_utils import log, warn

# ----- Canonical configuration --------------------------------------------

SILO_S3_BASE_URL = (
    "https://s3-ap-southeast-2.amazonaws.com/silo-open-data/Official/annual"
)

# Mapping of project-canonical variable labels to SILO API names.
# Aligned with scope v4 sec. 4.1 (six daily variables).
SILO_VARIABLES: dict[str, str] = {
    "max_temp": "max_temp",  # daily maximum temperature, degC
    "min_temp": "min_temp",  # daily minimum temperature, degC
    "daily_rain": "daily_rain",  # daily rainfall, mm
    "vp": "vp",  # daily vapour pressure, hPa
    "evap_pan": "evap_pan",  # Class A pan evaporation, mm
    "radiation": "radiation",  # daily solar radiation, MJ/m^2
}

# Default analytical period. The lower bound (1961) is the SILO
# high-quality cutoff per scope v4 sec. 3.3. The upper bound (2024)
# excludes the rolling 12-month window where SILO grids may change,
# preserving reproducibility (see module docstring).
SILO_YEAR_MIN_DEFAULT = 1961
SILO_YEAR_MAX_DEFAULT = 2024

# Variable-specific effective start year overrides.
# Per SILO documentation, these variables have a long-term-average
# regime prior to the listed year and should not be treated as
# observed data before then. See module docstring for citations.
SILO_VARIABLE_EFFECTIVE_START: dict[str, int] = {
    "evap_pan": 1970,
}

# SILO grid shape (per longpaddock.qld.gov.au/silo/faq/, cross-checked
# against src.processing.cropping_mask constants):
SILO_LAT_N_CELLS_EXPECTED = 681
SILO_LON_N_CELLS_EXPECTED = 841


# ----- URL and path helpers ----------------------------------------------


def silo_annual_url(variable: str, year: int) -> str:
    """Return the AWS S3 HTTPS URL for one (variable, year) annual file."""
    if variable not in SILO_VARIABLES:
        raise ValueError(
            f"Unknown SILO variable '{variable}'. " f"Allowed: {sorted(SILO_VARIABLES)}"
        )
    api_name = SILO_VARIABLES[variable]
    return f"{SILO_S3_BASE_URL}/{api_name}/{year}.{api_name}.nc"


def masked_output_path(processed_dir: Path, variable: str, year: int) -> Path:
    """Return the destination path for a masked annual file."""
    return Path(processed_dir) / "silo" / variable / f"{year}.{variable}.nc"


def is_pre_effective_year(variable: str, year: int) -> bool:
    """
    Return True if a (variable, year) pair is before the variable's
    Master-grade effective start year.

    For most variables this is False (no restriction beyond the
    analytical period). For `evap_pan`, pre-1970 data is climatological
    long-term-average rather than observed; we skip those years to
    avoid a structural break at 1970 in the time series.
    """
    threshold = SILO_VARIABLE_EFFECTIVE_START.get(variable)
    if threshold is None:
        return False
    return year < threshold


# ----- Download ----------------------------------------------------------


def _stream_download(url: str, dst_path: Path, label: str | None = None) -> Path:
    """
    Stream-download a URL to ``dst_path`` with a tqdm progress bar.

    Writes to ``<dst>.part`` first and renames on success. Raises
    ``requests.HTTPError`` for non-2xx responses (the caller decides
    how to handle missing years etc.).
    """
    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst_path.with_suffix(dst_path.suffix + ".part")
    if tmp.exists():
        tmp.unlink()

    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        desc = label or dst_path.name
        with (
            open(tmp, "wb") as fh,
            tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=desc,
                leave=False,
            ) as pbar,
        ):
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                pbar.update(len(chunk))

    tmp.rename(dst_path)
    return dst_path


# ----- Mask application + persist ----------------------------------------


def load_cropping_mask(
    mask_nc_path: Path, variable_name: str = "cropping_mask_t005"
) -> xr.DataArray:
    """
    Load the cropping mask DataArray from data/processed/cropping_mask.nc.

    Returns a 2-D bool DataArray with (lat, lon) coordinates matching
    the SILO grid.
    """
    mask_nc_path = Path(mask_nc_path)
    if not mask_nc_path.exists():
        raise FileNotFoundError(
            f"Cropping mask not found at {mask_nc_path}. Run phase01_s03 first."
        )
    ds = xr.open_dataset(mask_nc_path)
    if variable_name not in ds.data_vars:
        raise KeyError(
            f"Variable '{variable_name}' not in {mask_nc_path}. "
            f"Available: {list(ds.data_vars)}"
        )
    mask = ds[variable_name].astype(bool).load()
    ds.close()
    return mask


def validate_silo_grid(raw_ds: xr.Dataset) -> None:
    """
    Check that a downloaded SILO raw NetCDF has the expected grid shape.

    SILO standard is lat=681, lon=841 (per longpaddock.qld.gov.au/silo/faq).
    Raises if either dimension is unexpected.
    """
    if "lat" not in raw_ds.dims or "lon" not in raw_ds.dims:
        raise ValueError(
            f"SILO file has unexpected dimensions {dict(raw_ds.dims)}; "
            "expected at least lat, lon, time"
        )
    n_lat = raw_ds.sizes["lat"]
    n_lon = raw_ds.sizes["lon"]
    if n_lat != SILO_LAT_N_CELLS_EXPECTED or n_lon != SILO_LON_N_CELLS_EXPECTED:
        raise ValueError(
            f"SILO grid shape (lat={n_lat}, lon={n_lon}) does not match "
            f"expected ({SILO_LAT_N_CELLS_EXPECTED}, {SILO_LON_N_CELLS_EXPECTED})"
        )


# Latitude tolerance (deg) for the post-alignment sanity guard.
_MASK_CENTROID_TOL_DEG = 1.0


def _assert_masking_sane(mask_da: xr.DataArray, mask_aligned: xr.DataArray) -> None:
    """
    Fail loudly if grid alignment moved the cropping cells (e.g. a north-south
    flip). Compares the latitude centroid of the cropping cells before and
    after alignment; a positional coordinate substitution on oppositely
    ordered axes mirrors this centroid about ~-27 deg (the Phase 02 s04a bug).

    Raises
    ------
    RuntimeError
        If the cropping-cell count changes materially or the latitude centroid
        shifts by more than ``_MASK_CENTROID_TOL_DEG``.
    """
    n_ref = int(mask_da.sum().item())
    n_new = int(mask_aligned.sum().item())
    if n_ref == 0:
        raise RuntimeError("cropping mask has no True cells")
    if abs(n_new - n_ref) > 0.01 * n_ref:
        raise RuntimeError(
            f"cropping-cell count changed during alignment ({n_ref} -> {n_new})"
        )
    ref_lat = float((mask_da["lat"] * mask_da).sum().item() / n_ref)
    new_lat = float((mask_aligned["lat"] * mask_aligned).sum().item() / n_new)
    if abs(new_lat - ref_lat) > _MASK_CENTROID_TOL_DEG:
        raise RuntimeError(
            f"cropping-mask latitude centroid moved {new_lat - ref_lat:+.1f} deg "
            f"during alignment (ref {ref_lat:.1f}, aligned {new_lat:.1f}); likely a "
            f"north-south grid flip (cf. Phase 02 s04a)"
        )


def apply_mask_and_persist(
    raw_nc_path: Path,
    variable: str,
    mask_da: xr.DataArray,
    dst_nc_path: Path,
    zlib_level: int = 4,
) -> dict:
    """
    Open a raw SILO annual NetCDF, apply the cropping mask, persist.

    Strategy:
        - Open lazy with xarray, load only the variable we need.
        - Use ``where(mask)`` so non-cropping cells become NaN; spatial
          structure (lat, lon) is preserved so downstream xarray
          operations work natively.
        - Encode with zlib level 4 (good ratio, fast).
        - Returns a small summary dict for logging.
    """
    raw_nc_path = Path(raw_nc_path)
    dst_nc_path = Path(dst_nc_path)
    dst_nc_path.parent.mkdir(parents=True, exist_ok=True)

    api_name = SILO_VARIABLES[variable]

    with xr.open_dataset(raw_nc_path) as ds_raw:
        validate_silo_grid(ds_raw)
        if api_name not in ds_raw.data_vars:
            raise KeyError(
                f"Variable '{api_name}' not in SILO file {raw_nc_path.name}. "
                f"Available: {list(ds_raw.data_vars)}"
            )
        # Subset to the single variable of interest:
        da_raw = ds_raw[api_name]
        n_days = int(da_raw.sizes.get("time", 0))

        # Align the cropping mask onto the raw SILO grid BY COORDINATE VALUE.
        #
        # The mask is stored latitude-DESCENDING (cropping_mask.py builds it
        # with np.linspace(-10, -44, ...)) while SILO data files are latitude-
        # ASCENDING. The earlier implementation substituted coordinates
        # positionally (assign_coords), which silently FLIPPED the mask north-
        # south: cropping cells landed on their latitude mirror (WA wheat-belt
        # -> Pilbara, Tasmania -> tropical ocean), so the true cropping cells
        # were masked to NaN. Discovered at Phase 02 s04a. `reindex` matches on
        # coordinate LABELS and is robust to axis ordering; nearest + half-cell
        # tolerance absorbs any float rounding between the two grids.
        mask_aligned = (
            mask_da.reindex(
                lat=da_raw["lat"],
                lon=da_raw["lon"],
                method="nearest",
                tolerance=0.025,  # half of the 0.05 deg grid spacing
            )
            .fillna(False)
            .astype(bool)
        )
        _assert_masking_sane(mask_da, mask_aligned)

        # Apply mask; keep spatial shape, non-cropping -> NaN.
        da_masked = da_raw.where(mask_aligned)

        # Preserve essential attrs/encoding.
        da_masked.attrs.update(da_raw.attrs)
        da_masked.name = api_name

        # Build a fresh dataset (avoid carrying over uneeded extras).
        ds_out = xr.Dataset({api_name: da_masked})
        # Copy time + coord attrs:
        for coord in ("time", "lat", "lon"):
            if coord in ds_raw.coords:
                ds_out[coord].attrs.update(ds_raw[coord].attrs)
        # Stamp provenance:
        ds_out.attrs.update(
            {
                "project": "agriculture-risk-monitoring-system",
                "phase": "01",
                "step": "04",
                "source": "SILO (Long Paddock, Queensland Government)",
                "source_url": SILO_S3_BASE_URL,
                "license": "CC BY 4.0",
                "cropping_mask_variable": "cropping_mask_t005",
                "cropping_mask_threshold": 0.05,
                "masking_convention": "non-cropping cells = NaN; structure preserved",
            }
        )

        encoding = {
            api_name: {
                "zlib": True,
                "complevel": zlib_level,
                "shuffle": True,
            }
        }
        ds_out.to_netcdf(dst_nc_path, encoding=encoding)

    # Post-write quick stats:
    masked_size = dst_nc_path.stat().st_size
    raw_size = raw_nc_path.stat().st_size
    return {
        "raw_bytes": raw_size,
        "masked_bytes": masked_size,
        "compression_ratio": (
            raw_size / masked_size if masked_size > 0 else float("inf")
        ),
        "n_days": n_days,
    }


# ----- Per (variable, year) orchestration --------------------------------


def ingest_one(
    variable: str,
    year: int,
    mask_da: xr.DataArray,
    raw_dir: Path,
    processed_dir: Path,
    delete_raw: bool = True,
) -> dict | None:
    """
    Idempotent ingestion of one (variable, year).

    Order of operations:
        1. Pre-effective-year skip: if the (variable, year) pair is
           before the variable's Master-grade effective start year
           (e.g. evap_pan before 1970), skip without downloading.
        2. If the masked output already exists, skip everything.
        3. Otherwise download the raw annual NetCDF (skipping if already
           present from a prior interrupted run).
        4. Apply the mask and persist.
        5. Optionally delete the raw download to bound disk usage.

    Returns:
        - dict with stats on success
        - dict with ``error`` key on failure
        - dict with ``skipped_reason="pre_effective_year"`` on intentional skip
        - ``None`` if the masked file already exists
    """
    # Step 1: scope-level skip for pre-effective-year data.
    if is_pre_effective_year(variable, year):
        return {
            "skipped_reason": "pre_effective_year",
            "effective_start": SILO_VARIABLE_EFFECTIVE_START[variable],
        }

    url = silo_annual_url(variable, year)
    raw_path = Path(raw_dir) / "silo" / variable / f"{year}.{variable}.nc"
    masked_path = masked_output_path(processed_dir, variable, year)

    if masked_path.exists():
        return None  # already done

    # Step 2: download raw (unless already present from prior interrupt)
    if not raw_path.exists():
        try:
            _stream_download(url, raw_path, label=f"{variable} {year}")
        except requests.HTTPError as e:
            warn(f"HTTP {e.response.status_code} for {url}; skipping {variable} {year}")
            return {"error": f"HTTP {e.response.status_code}", "url": url}
        except Exception as e:
            warn(f"Download failed for {variable} {year}: {e}")
            return {"error": str(e), "url": url}

    # Step 3: apply mask and persist
    try:
        stats = apply_mask_and_persist(
            raw_nc_path=raw_path,
            variable=variable,
            mask_da=mask_da,
            dst_nc_path=masked_path,
        )
    except Exception as e:
        warn(f"Mask/persist failed for {variable} {year}: {e}")
        # Leave raw on disk for debugging.
        return {"error": str(e), "url": url}

    # Step 4: delete raw if requested
    if delete_raw:
        try:
            raw_path.unlink()
        except Exception:
            pass

    return stats


# ----- Multi-year, multi-variable driver ---------------------------------


def ingest_all(
    variables: tuple[str, ...] | None,
    year_min: int,
    year_max: int,
    mask_da: xr.DataArray,
    raw_dir: Path,
    processed_dir: Path,
    delete_raw: bool = True,
) -> dict:
    """
    Ingest every (variable, year) combination sequentially.

    Returns a dict with per-variable summary stats: count succeeded,
    count skipped, total masked-bytes, total raw-bytes processed,
    and a per-year error list (if any). Also tracks pre-effective-year
    skips separately from "already-done" skips so the operator sees
    why each year was bypassed.
    """
    variables = variables or tuple(SILO_VARIABLES.keys())
    years = list(range(year_min, year_max + 1))
    total_units = len(variables) * len(years)

    log(
        f"SILO ingestion: {len(variables)} variables x {len(years)} years = {total_units} files"
    )
    summary = {
        v: {
            "done": 0,
            "skipped_already_done": 0,
            "skipped_pre_effective": 0,
            "errors": [],
            "masked_bytes": 0,
            "raw_bytes": 0,
        }
        for v in variables
    }

    with tqdm(total=total_units, desc="SILO files", unit="file") as pbar:
        for variable in variables:
            for year in years:
                result = ingest_one(
                    variable=variable,
                    year=year,
                    mask_da=mask_da,
                    raw_dir=raw_dir,
                    processed_dir=processed_dir,
                    delete_raw=delete_raw,
                )
                if result is None:
                    summary[variable]["skipped_already_done"] += 1
                elif "skipped_reason" in result:
                    summary[variable]["skipped_pre_effective"] += 1
                elif "error" in result:
                    summary[variable]["errors"].append({"year": year, **result})
                else:
                    summary[variable]["done"] += 1
                    summary[variable]["masked_bytes"] += result["masked_bytes"]
                    summary[variable]["raw_bytes"] += result["raw_bytes"]
                pbar.update(1)

    return summary
