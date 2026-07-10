"""
Phase 01 Step 01 — Initialise data/raw/manifest.yaml and ingest AAGIS
region shapefile.

This script runs once at the start of Phase 01. It:
    1. Reads data/raw/manifest.yaml (which must already exist; the
       initial schema is created by hand from the template provided
       in chat for this step).
    2. Calls src.ingestion.aagis_regions.ingest_aagis() to download,
       repair, validate, and persist the AAGIS region shapefile.
    3. Updates the aagis_regions entry in manifest.yaml with run-time
       metadata: resolved_url, retrieved_date, field_dictionary,
       persisted paths, validation results.

The script is idempotent: rerunning skips the download if the ZIP is
already on disk, and overwrites the manifest entry with current state.

AAGIS URL CAPTURE PROCEDURE
---------------------------
The AAGIS shapefile is published behind a JavaScript-constructed
download link, so the direct URL must be captured manually one time
and pinned in this script. Procedure:

    1. Open the page in a browser (Chrome / Firefox / Edge):
       https://www.agriculture.gov.au/abares/research-topics/surveys/farm-survey-data
    2. Open DevTools (F12) -> Network tab.
    3. Enable "Preserve log" to retain entries across navigation.
    4. Filter by ".zip" to surface only ZIP requests.
    5. Scroll to "AAGIS region mapping files" and click the
       "Download AAGIS region shape files (ZIP 2.6 MB)" link.
    6. Find the .zip request in the Network tab.
    7. Right-click that request -> Copy -> Copy URL.
    8. The download itself can be cancelled — only the URL is needed.
    9. Paste the URL into AAGIS_RESOLVED_URL below.

If the URL stops working in the future (government site
reorganisation), repeat the capture procedure to obtain a fresh URL.

USAGE
-----
    python scripts/phase01_s01_init_manifest_and_fetch_aagis.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Allow `from src.* import ...` when invoked as a top-level script.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.aagis_regions import IngestResult, ingest_aagis  # noqa: E402
from src.log_utils import error, log, ok, section  # noqa: E402
from src.paths import DATA_RAW  # noqa: E402


MANIFEST_PATH = DATA_RAW / "manifest.yaml"

# >>> PASTE the AAGIS resolved URL here, captured via DevTools (see docstring above):
AAGIS_RESOLVED_URL = "https://www.agriculture.gov.au/sites/default/files/documents/aagis_asgs16v1_g5a.shp_.zip"
# <<<


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict:
    """Read manifest.yaml; raise with a clear message if missing."""
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Expected manifest at {manifest_path}, but the file is missing. "
            f"Create data/raw/manifest.yaml from the schema template "
            f"(provided in chat for Phase 01 step 01) before running "
            f"this script."
        )
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def update_aagis_entry(manifest: dict, result: IngestResult) -> dict:
    """Patch the aagis_regions entry with this run's metadata."""
    entry = manifest["sources"]["aagis_regions"]
    entry["access"]["resolved_url"] = result.resolved_url
    entry["vintage"]["retrieved_date"] = result.retrieved_at
    entry["field_dictionary"] = {
        "pending_first_ingest": False,
        "region_count": result.region_count,
        "zones_present": result.zone_names,
        "crs": result.crs,
        "bounding_box_xyxy": list(result.bounding_box),
        "geometry_repair_log": {
            "invalid_before": result.invalid_geometries_before,
            "invalid_after": result.invalid_geometries_after,
        },
    }
    entry["persisted_paths"]["processed"] = result.repaired_geopackage_path.relative_to(
        REPO_ROOT
    ).as_posix()
    manifest["project"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    return manifest


def write_manifest(manifest: dict, manifest_path: Path = MANIFEST_PATH) -> None:
    """Atomically write the manifest back to YAML.

    Writes to a sibling .tmp file then renames, so a crash mid-write
    cannot leave a half-formed manifest.
    """
    tmp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            manifest,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=88,
        )
    tmp_path.replace(manifest_path)
    ok(f"Manifest updated at {manifest_path.relative_to(REPO_ROOT)}")


def main() -> int:
    section("Phase 01 Step 01: manifest init + AAGIS region ingestion")

    if not AAGIS_RESOLVED_URL:
        error(
            "AAGIS_RESOLVED_URL is empty. Capture the direct download URL "
            "via browser DevTools (procedure in module docstring) and paste "
            "it into AAGIS_RESOLVED_URL near the top of this script."
        )
        return 1

    log(f"Loading manifest from {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    manifest = load_manifest()

    result = ingest_aagis(AAGIS_RESOLVED_URL)
    manifest = update_aagis_entry(manifest, result)
    write_manifest(manifest)

    ok("Phase 01 Step 01 complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
