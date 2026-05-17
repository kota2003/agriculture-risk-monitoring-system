"""
Phase 01, Step 02 - Initialise ACLUMP land-use raster.

Goal:
    Retrieve the ACLUMP Catchment Scale Land Use of Australia raster
    package (clum_50m_2023_v2.zip), extract the GeoTIFF, fetch the
    descriptive metadata document, and validate the broadacre cropping
    coverage against scope v4 sec. 4.1 expectations.

Out of scope (deferred to Step 03):
    Construction of the broadacre cropping mask aligned to the SILO 0.05
    deg grid. That step performs the reproject + classify operation in
    src.processing.cropping_mask.

Idempotency:
    All download and extraction steps check for existing artefacts and
    skip when sizes match. Safe to re-run.

Run from repo root:
    python scripts/phase01_s02_init_aclump.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path so `import src.X` works regardless of CWD.
# This is required when running `python scripts/...` directly: Python sets
# sys.path[0] to the scripts/ directory by default, which does not see src/.
# This is the same pattern that should be used by all phaseXX_sYY_*.py
# orchestration scripts.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------------

from src.paths import DATA_RAW
from src.log_utils import log, ok, warn, section, subsection
from src.ingestion.aclump import (
    download_aclump_zip,
    download_aclump_metadata,
    unpack_clum_raster,
    inspect_raster,
    compute_alum_code_distribution,
    validate_broadacre_coverage,
    record_download_provenance,
    ALUM_BROADACRE_CROPPING_CODES,
    ALUM_IRRIGATED_CROPPING_CODES,
    ALUM_LAND_IN_TRANSITION_CODES,
    EXPECTED_RASTER_CONTENT_LENGTH,
)


def main() -> int:
    section("Phase 01, Step 02 - ACLUMP land-use raster ingestion")

    aclump_dir = DATA_RAW / "aclump"
    aclump_dir.mkdir(parents=True, exist_ok=True)
    log(f"Target directory: {aclump_dir}")

    # ----- (1) Download raster ZIP --------------------------------------
    subsection("1. Download CLUM raster package")
    zip_path = download_aclump_zip(aclump_dir)
    zip_prov = record_download_provenance(zip_path)
    log(f"  size:   {zip_prov['size_bytes']:,} bytes")
    log(f"  sha256: {zip_prov['sha256']}")
    if zip_prov["size_bytes"] != EXPECTED_RASTER_CONTENT_LENGTH:
        warn(
            f"Raster ZIP size {zip_prov['size_bytes']:,} does not match "
            f"pre-verified Content-Length {EXPECTED_RASTER_CONTENT_LENGTH:,}. "
            f"This may indicate an ABARES re-release; check Last-Modified."
        )

    # ----- (2) Download metadata docx -----------------------------------
    subsection("2. Download descriptive metadata document")
    meta_path = download_aclump_metadata(aclump_dir)
    meta_prov = record_download_provenance(meta_path)
    log(f"  size:   {meta_prov['size_bytes']:,} bytes")
    log(f"  sha256: {meta_prov['sha256']}")

    # ----- (3) Extract main GeoTIFF -------------------------------------
    subsection("3. Extract clum_50m_2023_v2.tif from ZIP")
    tif_path = unpack_clum_raster(zip_path, aclump_dir)
    tif_prov = record_download_provenance(tif_path)
    log(f"  size:   {tif_prov['size_bytes']:,} bytes")

    # ----- (4) Inspect raster header -----------------------------------
    subsection("4. Inspect raster header")
    info = inspect_raster(tif_path)
    for k, v in info.items():
        log(f"  {k:14s}: {v}")

    # Sanity check on CRS and resolution against scope v4 expectations.
    if info["crs"] != "EPSG:3577":
        warn(f"Expected CRS EPSG:3577 (GDA94 / Australian Albers), got {info['crs']}")
    else:
        ok("CRS matches expectation (EPSG:3577)")

    res_x = info["res_x_metres"]
    res_y = info["res_y_metres"]
    if abs(res_x - 50.0) > 0.1 or abs(res_y - 50.0) > 0.1:
        warn(f"Expected 50 m x 50 m pixels, got {res_x:.2f} x {res_y:.2f}")
    else:
        ok(f"Pixel size matches expectation ({res_x:.1f} m x {res_y:.1f} m)")

    # ----- (5) ALUM code distribution -----------------------------------
    subsection("5. Compute ALUM 8 code distribution")
    log("This pass reads every raster block once; expect a few minutes.")
    dist = compute_alum_code_distribution(tif_path)
    log(f"  unique ALUM codes seen: {len(dist)}")

    # Aggregate to secondary class for human-readable summary.
    secondary_summary = (
        dist.groupby("secondary", sort=False)["count"]
        .sum()
        .sort_values(ascending=False)
    )
    total = secondary_summary.sum()
    subsection("   ALUM secondary class summary (top 15)")
    for label, cnt in secondary_summary.head(15).items():
        log(f"  {cnt / total:>7.3%}  {cnt:>14,}  {label}")

    # ----- (6) Validate broadacre coverage ------------------------------
    subsection("6. Validate broadacre cropping coverage")
    val = validate_broadacre_coverage(dist)
    log(
        f"  3.3 Cropping (broadacre): "
        f"{val['broadacre_fraction']:.3%} ({val['broadacre_count']:,} pixels)"
    )
    log(f"  4.3 Irrigated cropping (excluded): {val['irrigated_fraction']:.3%}")
    log(f"  3.6 Land in transition (excluded): {val['transition_fraction']:.3%}")
    log(
        f"  Expected broadacre fraction range: "
        f"[{val['expected_min']:.2%}, {val['expected_max']:.2%}]"
    )

    if val["in_expected_range"]:
        ok("Broadacre coverage within expected range (per scope v4 sec. 4.1)")
    else:
        warn(
            "Broadacre coverage outside expected range. This is the "
            "trigger for the s02 contingency review per PROJECT_LOG "
            "2026-05-14 decisions 1-4: check ALUM lookup, consider "
            "including 3.6 Land in transition, or supplement with "
            "ACLUMP commodities vector."
        )

    # ----- (7) Provenance recap -----------------------------------------
    subsection("7. Provenance summary (for manifest update)")
    log(f"  ZIP    sha256: {zip_prov['sha256']}")
    log(f"  TIF    sha256: {tif_prov['sha256']}")
    log(f"  Meta   sha256: {meta_prov['sha256']}")

    # ----- (8) Next-step reminder --------------------------------------
    subsection("8. Handoff to Step 03")
    log("Step 03 (src/processing/cropping_mask.py) will:")
    log("  - reproject the ACLUMP raster from EPSG:3577 to EPSG:4326")
    log("  - resample/aggregate to the SILO 0.05 deg grid")
    log("  - classify pixels as broadacre cropping using ALUM codes:")
    log(f"      include: {list(ALUM_BROADACRE_CROPPING_CODES)}")
    log(f"      exclude: 4.3 = {list(ALUM_IRRIGATED_CROPPING_CODES)}")
    log(f"      exclude: 3.6 = {list(ALUM_LAND_IN_TRANSITION_CODES)}")
    log("  - persist data/processed/cropping_mask.nc")
    log("Before s03: append the s02 PROJECT_LOG entry per draft in chat.")

    ok("Phase 01 Step 02 complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
