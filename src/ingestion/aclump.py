"""
ACLUMP (Catchment Scale Land Use of Australia) ingestion.

This module retrieves the ACLUMP raster package (clum_50m_2023_v2.zip),
unpacks the GeoTIFF land-use raster, and provides utilities for inspecting
its structure and the ALUM 8 code distribution.

Reference: ABARES 2024, Catchment Scale Land Use of Australia - Update
December 2023 version 2, CC BY 4.0, DOI: 10.25814/2w2p-ph98.

The raster pixel value is a three-digit ALUM 8 integer code. The hundreds
digit is the primary class, the tens digit is the secondary class, and the
units digit is the tertiary class. For the broadacre cropping mask used by
this project (scope v4 sec. 4.4), the relevant codes are the
ALUM 3.3 Cropping secondary class: 330-338.

This module performs ingestion and inspection only. Construction of the
broadacre cropping mask aligned to the SILO grid is performed by
``src.processing.cropping_mask`` in Phase 01 Step 03.
"""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from tqdm import tqdm

from src.log_utils import log, ok, warn

# ----- Canonical source URLs (pinned to December 2023 version 2 release) -----

ACLUMP_RASTER_URL = (
    "https://www.agriculture.gov.au/sites/default/files/documents/"
    "clum_50m_2023_v2.zip"
)

# Metadata docx (Kota-confirmed canonical format; see PROJECT_LOG 2026-05-14).
ACLUMP_METADATA_URL = (
    "https://www.agriculture.gov.au/sites/default/files/documents/"
    "CLUM_DescriptiveMetadata_December2023_v2.docx"
)

# Verified via DevTools Headers capture, 2026-05-14:
EXPECTED_RASTER_CONTENT_LENGTH = 158_077_503  # bytes (~150.7 MB)
EXPECTED_RASTER_ETAG = '"667cf4a9-96c123f"'
EXPECTED_RASTER_LAST_MODIFIED = "Thu, 27 Jun 2024 05:12:09 GMT"

# Filename of the GeoTIFF inside the ZIP (per Table 1 of metadata docx):
RASTER_TIF_NAME = "clum_50m_2023_v2.tif"

# ----- ALUM 8 broadacre cropping codes (Table A1 of metadata docx) -----

# ALUM secondary class 3.3 Cropping = the broadacre cropping mask target.
# Used for constructing the cropping mask in src.processing.cropping_mask.
ALUM_BROADACRE_CROPPING_CODES: tuple[int, ...] = (
    330,
    331,
    332,
    333,
    334,
    335,
    336,
    337,
    338,
)

# Explicitly excluded from the cropping mask (scope v4 sec. 3.2, sec. 4.4):
ALUM_IRRIGATED_CROPPING_CODES: tuple[int, ...] = tuple(range(430, 440))
ALUM_LAND_IN_TRANSITION_CODES: tuple[int, ...] = tuple(range(360, 366))

# All ALUM 8 secondary class code ranges, for distribution accounting.
# Per Table A1 of the metadata docx.
ALUM_SECONDARY_CLASSES: dict[str, tuple[int, ...]] = {
    "1.1 Nature conservation": (110, 111, 112, 113, 114, 115, 116, 117),
    "1.2 Managed resource protection": (120, 121, 122, 123, 124, 125),
    "1.3 Other minimal use": (130, 131, 132, 133, 134),
    "2.1 Grazing native vegetation": (210,),
    "2.2 Production native forests": (220, 221, 222),
    "3.1 Plantation forests": (310, 311, 312, 313, 314),
    "3.2 Grazing modified pastures": (320, 321, 322, 323, 324, 325),
    "3.3 Cropping": ALUM_BROADACRE_CROPPING_CODES,
    "3.4 Perennial horticulture": tuple(range(340, 350)),
    "3.5 Seasonal horticulture": (350, 351, 352, 353),
    "3.6 Land in transition": ALUM_LAND_IN_TRANSITION_CODES,
    "4.1 Irrigated plantation forests": (410, 411, 412, 413, 414),
    "4.2 Grazing irrigated modified pastures": (420, 421, 422, 423, 424),
    "4.3 Irrigated cropping": ALUM_IRRIGATED_CROPPING_CODES,
    "4.4 Irrigated perennial horticulture": tuple(range(440, 450)),
    "4.5 Irrigated seasonal horticulture": (450, 451, 452, 453, 454),
    "4.6 Irrigated land in transition": tuple(range(460, 466)),
    "5.1 Intensive horticulture": (510, 511, 512, 513, 514, 515),
    "5.2 Intensive animal production": tuple(range(520, 529)),
    "5.3 Manufacturing and industrial": tuple(range(530, 539)),
    "5.4 Urban / rural residential": (540, 541, 542, 543, 544, 545),
    "5.5 Services": (550, 551, 552, 553, 554, 555),
    "5.6 Utilities": tuple(range(560, 568)),
    "5.7 Transport and communication": (570, 571, 572, 573, 574, 575),
    "5.8 Mining": (580, 581, 582, 583, 584),
    "5.9 Waste treatment and disposal": (590, 591, 592, 593, 594, 595),
    "6.1 Lake": (610, 611, 612, 613, 614),
    "6.2 Reservoir/dam": (620, 621, 622, 623),
    "6.3 River": (630, 631, 632, 633),
    "6.4 Channel/aqueduct": (640, 641, 642, 643),
    "6.5 Marsh/wetland": (650, 651, 652, 653, 654),
    "6.6 Estuary/coastal waters": (660, 661, 662, 663),
}


# ----- Download utilities --------------------------------------------------


def _stream_download(
    url: str,
    dest_path: Path,
    expected_content_length: int | None = None,
    progress_label: str | None = None,
) -> Path:
    """
    Stream-download a single URL to ``dest_path``, with idempotency.

    If ``dest_path`` already exists and matches ``expected_content_length``
    (when provided), the existing file is returned without re-downloading.
    Otherwise the URL is fetched with a tqdm progress bar.

    The download is written to a ``.part`` sibling first and renamed on
    success, to avoid leaving a corrupted file on disk if interrupted.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        actual_size = dest_path.stat().st_size
        if expected_content_length is None or actual_size == expected_content_length:
            ok(
                f"{dest_path.name} already on disk ({actual_size:,} bytes); skip download"
            )
            return dest_path
        warn(
            f"{dest_path.name} size mismatch (have {actual_size:,}, "
            f"expect {expected_content_length:,}); re-downloading"
        )
        dest_path.unlink()

    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    if tmp_path.exists():
        tmp_path.unlink()

    log(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        total = (
            int(resp.headers.get("Content-Length", 0)) or expected_content_length or 0
        )
        label = progress_label or dest_path.name
        with (
            open(tmp_path, "wb") as fh,
            tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=label,
                leave=False,
            ) as pbar,
        ):
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                pbar.update(len(chunk))

    actual_size = tmp_path.stat().st_size
    if expected_content_length is not None and actual_size != expected_content_length:
        tmp_path.unlink()
        raise RuntimeError(
            f"Download size mismatch for {url}: got {actual_size:,}, "
            f"expected {expected_content_length:,}"
        )

    tmp_path.rename(dest_path)
    ok(f"Saved {dest_path.name} ({actual_size:,} bytes)")
    return dest_path


def download_aclump_zip(dest_dir: Path) -> Path:
    """Download the ACLUMP raster ZIP to ``dest_dir``."""
    return _stream_download(
        url=ACLUMP_RASTER_URL,
        dest_path=Path(dest_dir) / "clum_50m_2023_v2.zip",
        expected_content_length=EXPECTED_RASTER_CONTENT_LENGTH,
        progress_label="clum_50m_2023_v2.zip",
    )


def download_aclump_metadata(dest_dir: Path) -> Path:
    """Download the ACLUMP descriptive metadata docx to ``dest_dir``."""
    return _stream_download(
        url=ACLUMP_METADATA_URL,
        dest_path=Path(dest_dir) / "CLUM_DescriptiveMetadata_December2023_v2.docx",
        expected_content_length=None,  # not pre-verified; recorded at runtime
        progress_label="metadata.docx",
    )


# ----- Unpack and inspect --------------------------------------------------


def unpack_clum_raster(zip_path: Path, dest_dir: Path) -> Path:
    """
    Extract only the main CLUM GeoTIFF from the ZIP.

    The ZIP also contains layer files (.lyrx/.lyr/.qml) for ArcGIS/QGIS and
    a nested ``scale_date_update.zip`` with date/scale/updates rasters.
    Only ``clum_50m_2023_v2.tif`` is extracted (Phase 01 sec. 4 of scope v4);
    the rest is left compressed inside the ZIP for provenance.
    """
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    tif_dest = dest_dir / RASTER_TIF_NAME

    if tif_dest.exists():
        ok(
            f"{RASTER_TIF_NAME} already extracted ({tif_dest.stat().st_size:,} bytes); skip"
        )
        return tif_dest

    log(f"Extracting {RASTER_TIF_NAME} from {zip_path.name}")
    with zipfile.ZipFile(zip_path) as zf:
        # Locate the target tif (may be at root or nested)
        target_member = None
        for name in zf.namelist():
            if Path(name).name == RASTER_TIF_NAME:
                target_member = name
                break
        if target_member is None:
            raise RuntimeError(
                f"{RASTER_TIF_NAME} not found in {zip_path.name}; "
                f"members: {zf.namelist()[:10]}"
            )
        with zf.open(target_member) as src, open(tif_dest, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)

    ok(f"Extracted to {tif_dest} ({tif_dest.stat().st_size:,} bytes)")
    return tif_dest


def inspect_raster(tif_path: Path) -> dict:
    """
    Read raster metadata without loading pixel data into memory.

    Returns a dict with: CRS, bounding box, dtype, shape, transform,
    nodata sentinel, and resolution.
    """
    tif_path = Path(tif_path)
    with rasterio.open(tif_path) as src:
        return {
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtype": str(src.dtypes[0]),
            "nodata": src.nodata,
            "bounds": {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top,
            },
            "transform": list(src.transform),
            "res_x_metres": abs(src.transform.a),
            "res_y_metres": abs(src.transform.e),
        }


def compute_alum_code_distribution(
    tif_path: Path,
    block_limit: int | None = None,
) -> pd.DataFrame:
    """
    Compute the histogram of ALUM 8 pixel codes by reading the raster in
    windowed blocks (so the full ~21 GB uncompressed image never has to
    fit in memory at once).

    Returns a DataFrame indexed by ALUM code with columns:
        ``count``        : raw pixel count
        ``fraction``     : count / total non-nodata pixels
        ``secondary``    : ALUM secondary class label (e.g. ``3.3 Cropping``)

    If ``block_limit`` is given, only that many blocks are processed
    (useful for quick smoke-tests). When ``None`` the whole raster is read.
    """
    tif_path = Path(tif_path)
    counts: dict[int, int] = {}

    with rasterio.open(tif_path) as src:
        nodata = src.nodata
        total_blocks = sum(1 for _ in src.block_windows(1))
        log(f"Scanning {total_blocks} raster blocks for ALUM code histogram")

        for i, (_, window) in enumerate(
            tqdm(list(src.block_windows(1)), desc="ALUM histogram", leave=False)
        ):
            if block_limit is not None and i >= block_limit:
                break
            arr = src.read(1, window=window)
            if nodata is not None:
                arr = arr[arr != nodata]
            if arr.size == 0:
                continue
            uniq, cts = np.unique(arr, return_counts=True)
            for u, c in zip(uniq.tolist(), cts.tolist()):
                counts[u] = counts.get(u, 0) + c

    if not counts:
        raise RuntimeError("No pixel codes found; raster may be empty or all nodata")

    total = sum(counts.values())
    code_to_secondary = _build_code_to_secondary_lookup()
    rows = [
        {
            "code": code,
            "count": cnt,
            "fraction": cnt / total,
            "secondary": code_to_secondary.get(code, "<unknown>"),
        }
        for code, cnt in sorted(counts.items())
    ]
    df = pd.DataFrame(rows).set_index("code")
    return df


def _build_code_to_secondary_lookup() -> dict[int, str]:
    """Invert ``ALUM_SECONDARY_CLASSES`` into ``{code: secondary_label}``."""
    lookup: dict[int, str] = {}
    for label, codes in ALUM_SECONDARY_CLASSES.items():
        for c in codes:
            lookup[c] = label
    return lookup


# ----- Validation against scope v4 expectations ----------------------------


def validate_broadacre_coverage(
    code_distribution: pd.DataFrame,
    expected_min_fraction: float = 0.04,
    expected_max_fraction: float = 0.15,
) -> dict:
    """
    Sanity-check the cropping coverage against scope v4 sec. 4.1 expectations.

    Per scope v4 sec. 4.1 the broadacre cropping zone is expected to cover
    roughly 5-10% of the continent. We allow a slightly wider window
    (4-15%) here as a sanity bound; tighter checks belong in Phase 02.

    Returns a dict with:
        ``broadacre_fraction``  : fraction of non-nodata pixels in 3.3
        ``broadacre_count``     : raw pixel count in 3.3
        ``in_expected_range``   : bool
        ``irrigated_fraction``  : fraction in 4.3 (for reference, excluded)
        ``transition_fraction`` : fraction in 3.6 (for reference, excluded)
    """
    df = code_distribution
    broadacre_mask = df.index.isin(ALUM_BROADACRE_CROPPING_CODES)
    irrigated_mask = df.index.isin(ALUM_IRRIGATED_CROPPING_CODES)
    transition_mask = df.index.isin(ALUM_LAND_IN_TRANSITION_CODES)

    broadacre_fraction = float(df.loc[broadacre_mask, "fraction"].sum())
    irrigated_fraction = float(df.loc[irrigated_mask, "fraction"].sum())
    transition_fraction = float(df.loc[transition_mask, "fraction"].sum())

    in_range = expected_min_fraction <= broadacre_fraction <= expected_max_fraction
    return {
        "broadacre_count": int(df.loc[broadacre_mask, "count"].sum()),
        "broadacre_fraction": broadacre_fraction,
        "irrigated_fraction": irrigated_fraction,
        "transition_fraction": transition_fraction,
        "in_expected_range": in_range,
        "expected_min": expected_min_fraction,
        "expected_max": expected_max_fraction,
    }


# ----- Provenance recording -----------------------------------------------


def record_download_provenance(file_path: Path) -> dict:
    """
    Return a small provenance dict for a downloaded artefact, suitable for
    appending to manifest.yaml at runtime: size, sha256, and on-disk path.
    """
    file_path = Path(file_path)
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return {
        "path": str(file_path),
        "size_bytes": file_path.stat().st_size,
        "sha256": h.hexdigest(),
    }
