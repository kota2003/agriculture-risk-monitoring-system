"""
Phase 01, Step 03 - Build broadacre cropping mask on the SILO grid.

Goal:
    Convert the ACLUMP land-use raster (EPSG:3577, 50 m) into a binary
    broadacre cropping mask at SILO grid resolution (EPSG:4326, 0.05 deg).
    Persist the result as ``data/processed/cropping_mask.nc`` containing:

        cropping_fraction   : float32, broadacre fraction in each SILO cell
        cropping_mask_t005  : bool,   primary cropping mask (fraction >= 0.05)
        cropping_mask_t010  : bool,   robustness mask     (fraction >= 0.10)
        cropping_mask_t020  : bool,   robustness mask     (fraction >= 0.20)

    The t010 and t020 masks support the Phase 09 threshold-sensitivity
    analysis (scope v4 sec. 5.6.2 robustness study; methodologically
    parallel to the MAUP robustness check).

Sanity checks performed:
    1. Conservation: total broadacre area on SILO grid must match the
       ACLUMP broadacre pixel count to within 5%.
    2. AAGIS regional intersection: each of the 20 cropping AAGIS regions
       must contain at least 50 cropping SILO cells (for downstream
       grid-level EVT fitting).
    3. Threshold consistency: t010 must be subset of t005, t020 subset of t010.

Prereqs:
    - Phase 01 Step 01 complete (AAGIS GeoPackage at data/processed/)
    - Phase 01 Step 02 complete (ACLUMP raster at data/raw/aclump/)

Idempotency:
    The intermediate binary raster is reused if it already exists. The
    final NetCDF is rebuilt every run (cheap; ~3 MB output).

Run from repo root:
    python scripts/phase01_s03_build_cropping_mask.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path so `import src.X` works regardless of CWD.
# Same pattern as phase01_s02_init_aclump.py.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.paths import DATA_RAW, DATA_PROCESSED
from src.log_utils import log, ok, warn, error, section, subsection
from src.ingestion.aclump import (
    ALUM_BROADACRE_CROPPING_CODES,
    EXPECTED_RASTER_ETAG,
)
from src.processing.cropping_mask import (
    build_broadacre_binary_raster,
    reproject_to_silo_grid,
    apply_thresholds,
    build_cropping_mask_dataset,
    save_dataset,
    validate_conservation,
    validate_aagis_intersection,
    validate_threshold_consistency,
    CROPPING_THRESHOLDS_DEFAULT,
    PRIMARY_THRESHOLD,
    threshold_var_name,
    SILO_LAT_N_CELLS,
    SILO_LON_N_CELLS,
)

# Empirical from Phase 01 Step 02 (5.131% of non-NODATA pixels):
EXPECTED_BROADACRE_PIXEL_COUNT = 157_793_822


def _delete_quiet(path: Path) -> None:
    try:
        path.unlink()
        ok(f"Removed temporary file: {path.name}")
    except FileNotFoundError:
        pass
    except Exception as e:
        warn(f"Could not delete {path}: {e}")


def main() -> int:
    section("Phase 01, Step 03 - Build broadacre cropping mask on SILO grid")

    # ----- Path setup ----------------------------------------------------
    aclump_tif = DATA_RAW / "aclump" / "clum_50m_2023_v2.tif"
    aagis_gpkg = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
    tmp_binary_tif = DATA_RAW / "aclump" / "_tmp_broadacre_binary.tif"
    out_nc = DATA_PROCESSED / "cropping_mask.nc"

    log(f"ACLUMP raster:   {aclump_tif}")
    log(f"AAGIS gpkg:      {aagis_gpkg}")
    log(f"Output NetCDF:   {out_nc}")
    log(f"Temp binary tif: {tmp_binary_tif}")

    if not aclump_tif.exists():
        error(f"Missing ACLUMP raster at {aclump_tif}. Run phase01_s02 first.")
        return 1
    if not aagis_gpkg.exists():
        error(f"Missing AAGIS GeoPackage at {aagis_gpkg}. Run phase01_s01 first.")
        return 1

    # ----- (1) Build broadacre binary raster ----------------------------
    subsection("1. Build broadacre binary raster from ACLUMP")
    log("Reading ACLUMP windowed; writing 1=broadacre, 0=other, 255=nodata")
    build_broadacre_binary_raster(
        src_aclump_tif=aclump_tif,
        dst_binary_tif=tmp_binary_tif,
        broadacre_codes=ALUM_BROADACRE_CROPPING_CODES,
    )

    # ----- (2) Reproject to SILO grid -----------------------------------
    subsection("2. Reproject + resample to SILO 0.05 deg grid (EPSG:4326)")
    fraction_da = reproject_to_silo_grid(tmp_binary_tif)
    log(
        f"  SILO grid shape: {fraction_da.shape} (expected {SILO_LAT_N_CELLS}, {SILO_LON_N_CELLS})"
    )
    log(
        f"  cropping_fraction min/mean/max: "
        f"{float(fraction_da.min()):.4f} / "
        f"{float(fraction_da.mean()):.4f} / "
        f"{float(fraction_da.max()):.4f}"
    )

    if fraction_da.shape != (SILO_LAT_N_CELLS, SILO_LON_N_CELLS):
        error("SILO grid shape mismatch; aborting before persistence.")
        return 1

    # ----- (3) Apply thresholds -----------------------------------------
    subsection("3. Apply thresholds (primary + robustness)")
    masks = apply_thresholds(fraction_da, CROPPING_THRESHOLDS_DEFAULT)
    for t, mask in masks.items():
        n_true = int(mask.sum())
        n_total = mask.size
        log(
            f"  t={t}: {n_true:,} cropping cells "
            f"({100.0 * n_true / n_total:.3f}% of grid; mask variable "
            f"`{threshold_var_name(t)}`)"
        )

    # ----- (4) Sanity check: conservation -------------------------------
    subsection("4. Sanity check 1 - area conservation across reproject")
    cons = validate_conservation(
        fraction_da=fraction_da,
        expected_aclump_broadacre_pixels=EXPECTED_BROADACRE_PIXEL_COUNT,
    )
    log(f"  Computed broadacre area: {cons['computed_area_km2']:>12,.1f} km^2")
    log(f"  Expected (ACLUMP-based): {cons['expected_area_km2']:>12,.1f} km^2")
    log(
        f"  Relative difference:     {cons['relative_diff_pct']:>5.2f}% "
        f"(tolerance {cons['tolerance_pct']:.0f}%)"
    )
    if cons["passes"]:
        ok("Conservation check passes")
    else:
        warn(
            "Conservation check FAILED. Reproject may be misconfigured; "
            "inspect cropping_fraction before proceeding to s04."
        )

    # ----- (5) Sanity check: threshold consistency ----------------------
    subsection("5. Sanity check 2 - threshold monotonicity")
    cons_t = validate_threshold_consistency(masks)
    for label, result in cons_t.items():
        if result["passes"]:
            ok(f"{label}: ok (0 violations)")
        else:
            warn(f"{label}: FAILED ({result['violations']} violations)")

    # ----- (6) Sanity check: AAGIS regional intersection ----------------
    subsection("6. Sanity check 3 - AAGIS regional cropping cell counts")
    log(
        f"  Using primary mask (t={PRIMARY_THRESHOLD}). Cropping zones only "
        f"(scope v4 sec. 3.1: 20 regions in Wheat Sheep + High Rainfall)."
    )
    primary_mask = masks[PRIMARY_THRESHOLD]
    region_df = validate_aagis_intersection(
        mask_da=primary_mask,
        aagis_gpkg_path=aagis_gpkg,
    )
    log("  Per-region cropping-cell counts (descending):")
    log(f"  {'aagis':>6s}  {'zone':<14s}  {'name':<30s}  {'cells':>8s}")
    for _, row in region_df.iterrows():
        log(
            f"  {str(row['aagis']):>6s}  {row['zone']:<14s}  "
            f"{str(row['name'])[:30]:<30s}  {row['cells_above_threshold']:>8,}"
        )

    n_below_min = int((~region_df["meets_min"]).sum())
    if n_below_min == 0:
        ok(f"All {len(region_df)} cropping regions meet the >=50 cells minimum")
    else:
        warn(
            f"{n_below_min} of {len(region_df)} cropping regions below the "
            f">=50 cells minimum. Phase 05 grid-level EVT fitting in those "
            f"regions will be unstable; consider t005 -> t002 or include 3.6 "
            f"Land in transition (s02 contingency)."
        )

    # ----- (7) Build dataset and persist --------------------------------
    subsection("7. Assemble NetCDF dataset and persist")
    source_attrs = {
        "title": "Broadacre cropping mask on SILO grid",
        "project": "agriculture-risk-monitoring-system",
        "phase": "01",
        "step": "03",
        "source_aclump_etag": EXPECTED_RASTER_ETAG,
        "source_aclump_alum_codes": "3.3 Cropping = "
        + ",".join(str(c) for c in ALUM_BROADACRE_CROPPING_CODES),
        "silo_grid_spec_source": "https://www.longpaddock.qld.gov.au/silo/faq/",
        "silo_grid_resolution_deg": 0.05,
        "silo_grid_bbox_centre_deg": "lon 112-154, lat -10 to -44",
    }
    ds = build_cropping_mask_dataset(
        fraction_da=fraction_da,
        masks=masks,
        primary_threshold=PRIMARY_THRESHOLD,
        source_attrs=source_attrs,
    )
    save_dataset(ds, out_nc)
    ok(f"Saved {out_nc} ({out_nc.stat().st_size:,} bytes)")

    # ----- (8) Clean up temp binary raster ------------------------------
    subsection("8. Clean up temporary intermediate raster")
    _delete_quiet(tmp_binary_tif)

    # ----- (9) Handoff to s04 -------------------------------------------
    subsection("9. Handoff to Step 04 (SILO grid ingestion)")
    log("Step 04 (src/ingestion/silo.py) will:")
    log("  - use cropping_mask_t005 in this NetCDF as the spatial subset")
    log("  - download SILO yearly NetCDFs (1961-present)")
    log("  - persist masked SILO grid as data/processed/silo_<var>_<year>.nc")
    log("Before s04: verify cropping_mask.nc opens correctly:")
    log(
        '  python -c "import xarray as xr; '
        "print(xr.open_dataset('data/processed/cropping_mask.nc'))\""
    )

    ok("Phase 01 Step 03 complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
