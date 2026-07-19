# PROJECT_LOG.md

**Project:** Agriculture Risk Monitoring System — A Multi-Method Research Framework for Australian Broadacre Cropping
**Repo:** https://github.com/kota2003/agriculture-risk-monitoring-system
**Author:** Kota
**Convention:** Append-only. Mid-file edits performed via one-off Python script, never by hand (PROJECT_WORKFLOW §8.2).

---

## 2026-05-11 — Phase 00, Step 00: Project scoping initiated

**Context:** Project 5 follows Project 4 (panel econometrics on education and income inequality). The initial scope (v1) framed this project as an operational agricultural risk monitoring system built on OpenWeather + FAOSTAT + ABS, with rule-based scoring.

**Decision:** Refine scope away from operational-monitoring framing toward research-depth-first framing, citing v1 limitations in data quality (OpenWeather historical coverage), spatial granularity (FAOSTAT is country-level), and analytical depth (single-method rule-based scoring is below portfolio-grade for the Project 5 slot).

**Rationale:** Project 4 already demonstrated single-method depth (panel econometrics); Project 5 should demonstrate methodological breadth + integration to complement, not duplicate, the portfolio signal.

**Impact:** Scope rewritten as v2 (research-depth, six methodological pillars, SILO/BoM/ABARES primary data, ABARES regions, broadacre tiered crop scope, 1961+ / 1980+ hybrid temporal design, 11-phase plan).

---

## 2026-05-11 — Phase 00, Step 00: Repo identity reconciled (v3)

**Context:** GitHub repo was created as `agriculture-risk-monitoring-system` (preserving the v1 monitoring vision in the name), while Scope v2 framed the project as a research framework. Mismatch between repo name and scope framing.

**Decision:** Reconcile by treating the multi-method analytical framework as the core deliverable and positioning the monitoring/dashboard layer as a communication surface. Update Scope to v3:
- Formal title: *Agriculture Risk Monitoring System: A Multi-Method Research Framework for Australian Broadacre Cropping*
- Codename: `agriculture-risk-monitoring-system` (matches repo)
- Framing-evolution paragraph added to §1.2

**Rationale:** "I refined an operational monitoring concept into a research-grade framework that can power a monitoring system" is itself a portfolio-grade narrative of scoping discipline. The repo name is preserved (no rename), avoiding wasted git history.

**Impact:** Scope v3 (778 lines) finalised; v1 and v2 archived in document history (Appendix C).

---

## 2026-05-11 — Phase 00, Step 00: Environment stack decided

**Context:** Initial Scope v3 specified Python 3.11 with conda+pip hybrid + GPU. During Phase 00 setup, three competing constraints surfaced: (a) user prefers simple/lightweight tooling, (b) RTX 3060 GPU is available locally, (c) Project 4 was Python 3.12.

**Decision (Python version):** Python 3.12 (matches Project 4, preserving portfolio-wide Python-version consistency). Earlier in-conversation choice of 3.11 was corrected after discovering Project 4's runtime.

**Decision (environment manager):** pip + venv only (no conda). GPU support intentionally dropped.

**Decision (GPU):** Not used. Project 5's analytical stack (EVT, panel regression, tree-based ML on ~60 ABARES regions × ~45 years sample size) is CPU-bound; GPU would not materially change runtimes. pip+venv is incompatible with GPU science-stack (CUDA Toolkit / cuDNN are conda-managed in practice), so dropping GPU enables choosing pip+venv.

**Decision (code quality):** black + ruff + pre-commit, with `requirements-dev.txt` separating dev deps from runtime deps.

**Decision (editor):** `.vscode/settings.json` committed, pinning `python.defaultInterpreterPath` to `.venv` — structural fix for Project 4 lesson 5 (interpreter mismatch).

**Rationale:** Simplicity, transparency, and recruiter-reproducibility prioritised over performance. The CPU-only choice is documented in Scope §9.1 as a deliberate trade-off, not an oversight.

**Impact:** Scope §9 fully rewritten in v3 to pip+venv+CPU-only.

---

## 2026-05-12 — Phase 00, Step 01: Bootstrap script created

**Context:** Repo structure (data/, src/, scripts/, notebooks/, docs/, outputs/, .vscode/) needs to be created idempotently from Scope Appendix A's specification (~15 directories, 9 .gitkeep, 6 __init__.py).

**Decision:** Create `phase00_s01_bootstrap_repo.py` as a one-time bootstrap utility (Python script with idempotency checks and informative logging). PowerShell one-liner was considered but rejected for readability and maintainability reasons.

**Lifecycle decision:** This script is classified as ephemeral build infrastructure per `portfolio_finalisation_playbook §12` (log-only / vestigial script policy). It will be **deleted at v1.0 closure** (Phase 10). The directory structure it produces is the substantive deliverable; the script itself is build infrastructure.

**Impact:** Repo structure created cleanly in one run. Script placed in `scripts/phase00_s01_bootstrap_repo.py`.

---

## 2026-05-12 — Phase 00, Step 02: Config files placed

**Context:** Repo needs `.gitignore`, `LICENSE` (MIT), `.python-version`, `.pre-commit-config.yaml`.

**Decision:** No generator script (avoiding accumulation of ephemeral scripts). File content is provided directly; Kota places via editor.

**Pre-emptive .gitignore patterns added:**
- `*_v[0-9].py`, `*_FINAL*` — Project 4 lesson 3 (backup file accumulation at repo root)
- `*_dump.*`, `scratch_*`, `temp_*`, `wip_*` — Project 4 lesson 4 (scratch file slip-in)
- `outputs/models/*` (with `!outputs/models/.gitkeep`) — Project 4 lesson 2 (large `.joblib` accidentally tracked)
- `data/raw/*` and `data/processed/*` (with `.gitkeep` and `manifest.yaml` exceptions) — reproduce-from-code policy

**Impact:** Config layer complete. `.gitignore` verified working via `scratch_test.txt` exclusion test.

---

## 2026-05-12 — Phase 00, Step 03: Environment setup with Long Path resolution

**Context:** venv creation and `pip install -r requirements.txt -r requirements-dev.txt` was the planned simple path. The install failed on first attempt with:

```
ERROR: Could not install packages due to an OSError: [Errno 2] No such file or directory:
'C:\...\agriculture-risk-monitoring-system\.venv\share\jupyter\labextensions\@jupyter-widgets\jupyterlab-manager\static\packages_base_lib_index_js-webpack_sharing_consume_default_jquery_jquery.5dd13f8e980fa3c50bfe.js'
HINT: This error might have occurred since this system does not have Windows Long Path support enabled.
```

This is the Windows MAX_PATH (260-character) constraint, triggered by the project being located at `C:\Users\kotae\Documents\Portfolio\project\Project 5\agriculture-risk-monitoring-system\` (84 chars) plus jupyterlab-manager's deeply nested webpack chunk filenames.

**Decision:** Enable Windows Long Path support at the registry level via:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

(executed in elevated PowerShell, requires reboot).

**Alternative considered:** Move the project to a shorter path (e.g., `C:\Users\kotae\Projects\agriculture-risk-monitoring-system\`). Rejected because Long Path enablement is a one-time structural fix that prevents the issue from recurring in Phase 04 (geopandas) and Phase 07 (xgboost/lightgbm), which install similarly deep file trees.

**Rationale:** Choose the structural fix once over per-phase path workarounds.

**Impact:** After reboot, `pip install` completed cleanly (113 packages). All subsequent installs (Phase 04+) protected from MAX_PATH issues.

---

## 2026-05-12 — Phase 00, Step 04: src/ utility modules implemented

**Context:** Three foundational modules needed before any downstream phase can begin: path resolution, robust CSV I/O, uniform logging.

**Decision:** Implement `src/paths.py`, `src/io_utils.py`, `src/log_utils.py` directly (these are permanent, substantive code, not ephemeral scripts).

**Project 4 lessons pre-emptively encoded:**
- `src/paths.py`: All paths are `pathlib.Path` objects, anchored at repo root via `Path(__file__).resolve().parent.parent`. No absolute path hardcoding (general Project 4 hygiene).
- `src/io_utils.py::read_csv_safe`: Encoding fallback (utf-8 → cp1252 → latin-1) addressing lesson 8 (UNDP HDR cp1252 file). `keep_default_na=False` + explicit `na_values` addressing lesson 9 (pandas converting "NA" country code to NaN).
- `src/log_utils.py`: Uniform `HH:MM:SS [LEVEL] message` format with stdout/stderr separation. Avoids Python `logging` module to keep phase scripts short and unconditional.

**Impact:** Foundation layer complete. All three modules verified via dedicated test commands (encoding fallback tested with both UTF-8 and cp1252 inputs; NA preservation tested with Namibia country code).

---

## 2026-05-12 — Phase 00, Step 05: Project scope archived in docs/

**Decision:** `p5_ProjectScope_v3.md` placed as `docs/project_scope.md` (universal name; v3 specifier preserved in document history Appendix C).

**Impact:** Scope is now part of the public repo deliverable.

---
## 2026-05-14 — Phase 01, Step 00 (pre-execution scope recalibration)

**Context:** Before launching Phase 01 (Data Acquisition), Kota explicitly recalibrated
the Project 5 quality bar to Master-research-grade portfolio standards. The evaluation
lenses now include research-lab admissions committees, professors, and academically
literate hiring managers — the project must defend itself as a Master researcher's
portfolio piece, not merely as a polished industry artefact. Reviewing the v3 scope and
The preliminary Phase 01 recommendations (point-centroid SILO sampling at AAGIS
region centroids) under this raised bar revealed engineering compromises that would
not withstand research-peer-review scrutiny — specifically (a) Modifiable Areal Unit
Problem (MAUP) exposure from single-unit framing, (b) information loss from
pre-aggregating climate data before indicator computation, (c) absence of observed-vs-
derived data discipline regarding the Australian Gridded Farm Data (AGFD).

**Decision:** Bump scope to v4, with substantive revisions across the following
sections (full v4 document supersedes v3):
1. New §3.6 — Spatial Resolution Strategy (mixed-resolution philosophy).
2. §4.1 rewritten — SILO ingestion via grid-based subsetting with ACLUMP cropping-area
   mask, replacing v3 point-centroid strategy.
3. New §4.4 — ACLUMP land-use mask added as primary data source.
4. New §4.6 — AGFD added as Phase 09 independent validation benchmark, with explicit
   observed-vs-derived discipline.
5. §5.1 + §5.2 clarified — climate indicators computed at SILO grid resolution; EVT
   fitting at grid level with region-level rollup.
6. §5.6 expanded — MAUP robustness study (primary results re-computed at GRDC
   agro-ecological zone aggregation) and AGFD validation added to Pillar 6 synthesis.
7. §3.1 — AAGIS region formally named as primary yield unit, zone × region hierarchy
   documented, known geometry-error caveat noted.
8. §6 phase plan — Phase 01 acquires ACLUMP mask; Phase 02 adds grid-vs-region-
   aggregate consistency check; Phase 09 ingests AGFD and runs MAUP study.
9. §9 tech stack — xarray, netCDF4, rasterio added for grid/raster handling.
10. §12 risks — AAGIS region climate-boundary non-alignment + observed-vs-derived
    data discipline explicitly acknowledged.

**Rationale:** A Master-researcher portfolio must demonstrate (i) explicit MAUP
awareness, (ii) spatial-unit selection defended on methodological grounds rather than
data convenience, (iii) strict observed-vs-derived data discipline, (iv) robustness
across spatial aggregation choices. The v3 single-unit framing and centroid-point
SILO strategy were defensible for an industry portfolio but constituted methodological
undersell for Master-level research framing. The mixed-resolution design adds
engineering work in Phase 01–04 but produces results that survive peer review.

**Impact:**
- Phase 01 ingestion list grows by one primary source (ACLUMP) and SILO ingestion
  shape changes (grid-based with mask, not point-based).
- Phase 02 gains a grid-vs-region-aggregate consistency check.
- Phase 04 climate indicators computed at grid resolution before any region aggregation.
- Phase 05 EVT methodological strength improves substantially via grid-level fitting.
- Phase 09 synthesis includes MAUP robustness section + AGFD independent validation.
- Estimated additional effort: ~1–2 weeks in Phase 01–02; absorbed within v3's
  stated 17–31 week band, no need to widen the band.

**Honesty note:** This recalibration was triggered by explicit user instruction to
raise the quality bar, not by discovery of new technical information. The initial
recommendation in this chat (point-centroid SILO sampling) was below the new bar and
is retracted in favour of the v4 design. Per the Project 4 adaptive-override convention
(documented in portfolio_finalisation_playbook §15), the retraction is documented here
explicitly rather than silently overwritten.
## 2026-05-14 — Phase 01, Step 01: AAGIS regions ingested and manifest initialised

**Context:** First substantive data acquisition step under scope v4. AAGIS
region shapefile selected in pre-Phase 01 recalibration as the primary yield
spatial unit (per scope v4 section 3.1).

**Decisions made during execution:**
- *Persistence format:* GeoPackage (.gpkg) chosen over re-emitting a shapefile
  for the repaired output. Rationale: single-file, OGC standard, no 10-char
  attribute name truncation, CRS in metadata.
- *Geometry repair tool:* shapely.validation.make_valid() (Python equivalent
  of read.abares R package's sf::st_make_valid()). Per scope v4 section 3.1
  / section 12.2 known quirk.
- *URL capture strategy:* manual DevTools URL extraction one time, hardcoded
  in scripts/phase01_s01_*.py. Documented retrieval procedure in script
  docstring for future re-capture if URL rots.
- *Manifest schema:* v1.0, per-source dict with canonical_name, publisher,
  role, access, vintage, license, classification (observed vs derived),
  field_dictionary, known_quirks, persisted_paths, notes.

**Run results (TO BE FILLED FROM EXECUTION LOG):**
- Resolved URL: <paste>
- Region count: <N>
- Zone column: <name>; zones present: <list>
- CRS: <EPSG:...>
- Geometry repair: <N> invalid before, 0 after
- Bounding box: <minx, miny, maxx, maxy>

**Impact:** AAGIS regions available for downstream steps as
`data/processed/aagis_regions_repaired.gpkg`. Used directly in s02 (ACLUMP
land-use raster's clip to AAGIS extent) and s03 (cropping mask spatial
join with SILO grid).


---

## 2026-05-14 — Phase 01, Step 01: AAGIS regions ingested; scope v4 corrections from empirical findings

**Context:** First substantive data acquisition step under scope v4.
AAGIS region shapefile selected in pre-Phase 01 recalibration as the
primary yield spatial unit (per scope v4 section 3.1).

**Execution summary.** Successful s01 run on 2026-05-14:
- URL: https://www.agriculture.gov.au/sites/default/files/documents/aagis_asgs16v1_g5a.shp_.zip
- Vintage: ASGS16 v1 (Last-Modified header 2020-08-04; ABARES page last
  updated 2024-09-09 but underlying file unchanged since 2020-08-04)
- File size: 2,637,311 bytes (2.52 MB compressed)
- ETag at ingest: "5f28c824-283dff"
- 32 features, CRS=EPSG:4283 (GDA94 geographic)
- Columns: aagis, class, name, zone, geometry (all lowercase)
- 2 of 32 geometries invalid on input (indices [26, 31]); both repaired
  successfully by GeoSeries.make_valid() (vectorized via shapely 2.x)
- Persisted as data/processed/aagis_regions_repaired.gpkg (3.84 MB)
- Bounding box (xmin, ymin, xmax, ymax):
  (112.92, -43.74, 153.64, -9.14) — entire Australia continent

**Decisions made during execution:**
- Persistence format: GeoPackage (.gpkg) over re-emitting a shapefile.
  Single-file, OGC standard, no 10-character attribute name truncation,
  CRS in metadata.
- Geometry repair: GeoSeries.make_valid() (vectorized) rather than
  per-feature .apply(make_valid). Python equivalent of read.abares R
  package's sf::st_make_valid().
- URL capture: manual one-time DevTools extraction, hardcoded in
  scripts/phase01_s01_*.py with documented re-capture procedure in
  docstring for resilience to future URL rot.

**Empirical findings requiring scope v4 corrections (made in-place):**

1. *Region count.* Scope v4 section 3.1 stated "~60 regions"; actual
   is **32 regions** in ASGS16 v1 vintage. Of those, 20 are cropping-
   relevant (12 Wheat Sheep + 8 High Rainfall zones); 12 Pastoral-zone
   regions are excluded from broadacre cropping analysis. Scope v4
   section 3.1 corrected in-place.

2. *Zone name spelling.* Scope v4 used hyphenated forms "Wheat-sheep"
   and "High-rainfall"; ABARES official attribute table uses spaces:
   "Wheat Sheep" and "High Rainfall". Scope v4 section 3.1 corrected
   in-place to match ABARES official spelling.

3. *MAUP-study scale caveat.* With 20 cropping AAGIS regions vs
   ~21 GRDC agro-ecological zones, the scope v4 section 5.6.2 MAUP
   robustness study tests **boundary-placement** sensitivity rather
   than **scale** sensitivity. Both are valid MAUP dimensions, but
   the framing of the synthesis-phase write-up must reflect this
   honestly. Scope v4 section 3.6.2 augmented with an "Empirical
   scale caveat" paragraph. A true scale-MAUP extension (e.g.,
   state-level n=7-8 aggregation) is logged as a possible Phase 09
   extension if time permits.

**Structural discovery for downstream use:**

The `class` column (3-digit integer) appears to encode
**state × zone × region** hierarchically:
- 1st digit = state (1=NSW, 2=VIC, 3=QLD, 4=SA, 5=WA, 6=TAS, 7=NT)
- 2nd digit = zone (1=Pastoral, 2=Wheat Sheep, 3=High Rainfall)
- 3rd digit = region index within state × zone combination

All 32 codes are consistent with this decoding. Pattern matches the
empirically-observed zone distribution (12/12/8) and region name
prefixes (NSW Far West has class=111 = NSW/Pastoral/1, VIC Mallee
has class=221 = VIC/Wheat Sheep/1, etc.). Formal verification
deferred to Phase 03 EDA.

**Impact:**
- AAGIS regions available as data/processed/aagis_regions_repaired.gpkg
  for downstream steps (gitignored; reproducible from script).
- Manifest.yaml records resolved URL, retrieval metadata, license,
  observed-vs-derived classification, known quirks, validation results,
  and structural notes.
- Scope v4 section 3.1 + 3.6.2 patched in-place to reflect empirical
  truth; no version bump to v5 since the methodology design is
  unchanged, only the numerical/spelling parameters that backed it.

**Honesty note on prior turn:** The previous-turn hypothesis that
.apply(make_valid) was causing a hang was unverified speculation;
the actual cause of the first run's interruption was likely
output-flush timing being interpreted as hang. The second run with
the original .apply() code would also have completed in seconds had
it been allowed to continue. The switch to vectorized
GeoSeries.make_valid() was retained because it is genuinely a more
appropriate API for shapely 2.x / geopandas 1.x environments, but
this is a code-quality improvement, not a bug fix.


## 2026-05-14 — Phase 01, Step 02: ACLUMP land-use raster ingested

**Context:** Phase 01 Step 02 retrieves the ACLUMP Catchment Scale Land Use
of Australia raster (December 2023 version 2), which serves as the source
of the broadacre cropping mask used to spatially subset SILO grid retrieval
(scope v4 §4.1, §4.4) and to define the spatial scope of Pillar 1–2
grid-level analyses.

**Decisions (locked in pre-execution, summarised here for the audit trail):**

1. **Raster GeoTIFF as primary data** (not commodities vector, not
   simplified 19-class raster). Rationale: closest to raw upstream data;
   ALUM 8 full classification preserved; commodities vector self-declared
   as not nationally complete; simplified raster coarsens broadacre vs
   grazing distinction.
2. **ALUM secondary class `3.3 Cropping` only as mask target** (codes
   330–338). Excluded: `4.3 Irrigated cropping` (430–439) per scope v4
   §3.2 out-of-scope; `3.6 Land in transition` (360–365) due to
   semantically-ambiguous "unknown land use" definition.
3. **s02 (raster acquisition) split from s03 (mask construction)**.
   Rationale: single responsibility; intermediate raw state inspectable;
   diagnostic gate before SILO grid reproject.
4. **Commodities supplementary vector deferred** (not retrieved in s02).
   Revisit only if s03 cropping mask sanity check fails.

**ALUM 8 code lookup** (Table A1 of `CLUM_DescriptiveMetadata_December2023_v2.docx`,
permanently archived to `data/raw/aclump/`):
- `3.3 Cropping`: 330, 331, 332, 333, 334, 335, 336, 337, 338
- `4.3 Irrigated cropping`: 430–439 (EXCLUDED from mask)
- `3.6 Land in transition`: 360–365 (EXCLUDED from mask)

**Empirical findings recorded for future diagnostics:**

*(a) ZIP internal structure:* `clum_50m_2023_v2.zip` contains the main
`clum_50m_2023_v2.tif` plus ArcGIS/QGIS layer files and a nested
`scale_date_update.zip` (date / scale / updates rasters). Only the main
GeoTIFF is extracted; the rest is left compressed for provenance.

*(b) State-level vintage non-uniformity:* The CLUM raster aggregates state
vector datasets of differing vintages: ACT 2012 (v7→v8 converted), NSW
2017 v1.5, SA 2017, WA 2018, NT 2022, VIC 2021, TAS 2021, QLD GBR 2021.
Core broadacre wheat regions (NSW, WA) are mapped at vintages 6–8 years
prior to project execution date. Acceptable under scope v4 §3.3
modern-agronomy framing (1980+ yield window tolerates 5–10 yr
cropping-extent stationarity assumption), but documented here for Phase 03
EDA state-level sanity checks.

*(c) WA visual attribution and SA Adelaide NODATA fill:* WA ALUM 4.0.0 /
5.0.0 / 6.0.0 attributed to secondary level by satellite visual
interpretation; SA Adelaide voids filled from ABS 2021 mesh blocks.
**Neither affects the `3.3 Cropping` broadacre mask** (handled in original
vector layers / not assigned to 3.3 in mesh block translation, Table 8).

*(d) Raster vs advertised size:* HTTP `Content-Length` = 158,077,503 bytes
(150.7 MB); ABARES download page advertises "126 MB" (stale rounding from
the February 2024 release). HTTP header is authoritative.

**Provenance captured at retrieval time:**
- Raster ZIP: 158,077,503 bytes, ETag `"667cf4a9-96c123f"`,
  Last-Modified `Thu, 27 Jun 2024 05:12:09 GMT`, sha256 `<filled by script>`
- Metadata docx: `<size filled by script>`, sha256 `<filled by script>`

**Sanity check result (s03 entry gate):**
- Broadacre 3.3 Cropping coverage: `<broadacre_fraction filled by script>`
  (expected range: 4–15% of non-NODATA pixels per scope v4 §4.1)
- In expected range: `<bool filled by script>`

**Impact:**
- Phase 01 Step 03 can now proceed: `src/processing/cropping_mask.py`
  will reproject the ACLUMP raster from EPSG:3577 to a 0.05° lat/lon grid
  matching SILO, classify pixels using the locked ALUM 3.3 code set, and
  persist a binary cropping mask as `data/processed/cropping_mask.nc`.
- `data/raw/manifest.yaml` updated with full `aclump` source entry,
  including ALUM code lookup, known quirks, and provenance values.

**Future contingency (recorded for traceability):** If s03 mask sanity
checks fail (e.g., cropping pixel count in WA Wheatbelt / NSW Riverina /
VIC Mallee below threshold, or per-AAGIS-region cropping cell count
inadequate for grid-level EVT fitting), the documented backout options are
(in order of preference): (i) expand mask to include `3.6 Land in
transition`; (ii) supplement with ACLUMP commodities vector; (iii) revisit
data source choice. Decision rules pre-committed here so any backout is
documented rather than retroactively justified.


---

## 2026-05-14  EPhase 01, Step 02: ACLUMP land-use raster acquisition

**Context:** Scope v4 §4.4 introduced the ACLUMP land-use raster as the source for constructing the broadacre cropping mask that constrains SILO grid ingestion (§4.1). ACLUMP is the ABARES Australian Collaborative Land Use and Management Program catchment-scale raster.

**Decisions:**

1. **Vintage selected:** `clum_50m_2023_v2` (December 2023 vintage), retrieved directly from the ABARES data portal as a ZIP archive containing GeoTIFF + metadata PDF.
2. **Volume acquired:** 286 MB TIF + 151 MB ZIP archive + descriptive metadata PDF. Native resolution: 50 m. Native CRS: EPSG:3577 (Australian Albers).
3. **Cropping coverage (empirical):** ALUM 3.3 "Cropping" class occupies **5.131% of non-NODATA pixels** across the continental raster, aligned with published Australian broadacre cropping area estimates.
4. **`src/ingestion/aclump.py`** implemented with download, unzip, and CRS-metadata inspection. Persisted at `data/raw/aclump/`.

**Impact:** Enables s03 cropping-mask construction and constrains s04 SILO retrieval to broadacre-relevant grid cells only, reducing SILO volume from an estimated 100+ GB continental-full to ~11.64 GB masked (actual empirical volume, s04).

---

## 2026-05-14  EPhase 01, Step 03: Cropping mask construction at SILO grid resolution

**Context:** Scope v4 §4.4, §5.6.2 require the ACLUMP land-use raster (s02) to be reprojected onto the SILO 0.05° grid to form a binary mask that constrains climate ingestion.

**Decisions:**

1. **Reprojection:** ACLUMP 50 m EPSG:3577 raster reprojected via bilinear resampling onto the SILO 0.05° WGS84 grid using rasterio + pyproj.
2. **Threshold sensitivity study (MAUP-adjacent):** three threshold values applied to test sensitivity of the resulting binary mask to threshold choice  E0.05, 0.10, 0.20 (fraction of the SILO grid cell classified as broadacre cropping in ACLUMP).
3. **Primary threshold selected:** **0.05** (`t005`)  Emost permissive, best captures the boundary of Australia's broadacre cropping zone. The `t010` and `t020` masks are persisted for downstream sensitivity analysis (Phase 02) but not used as the primary ingestion filter.
4. **Mask volume (empirical):** 28,721 True cells at the `t005` threshold across the SILO 0.05° grid. Persisted at `data/processed/cropping_mask.nc` (~226 KB).
5. **`src/processing/cropping_mask.py`** implemented with reprojection, thresholding, and mask construction utilities.

**Impact:** Enables s04 SILO retrieval to be efficiently subsetted to broadacre-relevant cells; provides the spatial scope for Pillar 1 E grid-level analyses per scope v5 §3.6.1.

**Phase 02 task:** Sensitivity analysis comparing indicator computations under `t005` vs `t010` vs `t020` masks (scope v5 §3.6.2).

---

## 2026-05-15  EPhase 01, Step 04: SILO grid climate data acquisition

**Context:** Scope v4 §4.1 requires daily gridded climate data (temperature, rainfall, vapour pressure, radiation, evaporation) at SILO 0.05° resolution over 1961–present, masked to the broadacre cropping area from s03.

**Decisions:**

1. **Source URL pattern (verified):** SILO Long Paddock data is mirrored on AWS S3 at `https://s3-ap-southeast-2.amazonaws.com/silo-open-data/Official/annual/<variable>/<year>.<variable>.nc` (per-year, per-variable NetCDF).
2. **Variables retrieved:** `max_temp`, `min_temp`, `daily_rain`, `vp`, `radiation`, `evap_pan` (6 variables).
3. **Period retrieved:** 1961 E024 for tmax, tmin, rainfall, vp, radiation (64 years).
4. **`evap_pan` empirical finding  Eeffective start = 1970 (not 1961):** Retrieval attempts for years 1961 E969 for the `evap_pan` variable returned files with structurally-sparse or absent data (variable not populated at continental extent for pre-1970 years). This is a **substantive empirical finding**: SPEI computation (which requires evappan) is constrained to 1970+ in downstream phases per updated scope v5 §3.3, §4.1, §5.1. `evap_pan` retrieval was accordingly limited to 1970 E024 (55 years).
5. **Ingestion strategy:** each per-year per-variable NetCDF downloaded to `data/raw/silo/<variable>/<year>.nc`, then cropping-mask-applied and persisted at `data/processed/silo/<variable>/<year>.nc`.
6. **`src/ingestion/silo.py`** implemented with idempotent download + mask application. Atomic write via `.part` ↁErename.

**Volumes (empirical):**
- **375 masked NetCDF files** total (5 variables ÁE64 years + evap_pan ÁE55 years = 375).
- **~11.64 GB** total on-disk after cropping-mask subsetting.
- Nine pre-1970 evap_pan attempts explicitly skipped and logged.

**Impact:** Provides the climate input layer for Pillars 1, 2 (grid-level indicators + EVT) and for Phase 02 OpenWeather–SILO comparison (§5.6.4).

**Phase 02 task:** Grid-vs-region aggregate consistency check (scope v5 §6.2 Phase 02).

---

## 2026-05-16  EPhase 01, Step 05: BoM ACORN-SAT homogenised temperature stations

**Context:** Scope v4 §4.2 identifies BoM ACORN-SAT as the homogenised station-level temperature reference for cross-validating SILO regional aggregates.

**Decisions:**

1. **URL pattern (verified):** BoM hqsites CSV endpoint at `https://www.bom.gov.au/climate/change/hqsites/data/temp/<tmin|tmax>.<6-digit-id>.daily.csv`. Station master list at `https://www.bom.gov.au/climate/change/acorn-sat/map/stations-acorn-sat.txt` (CSV with header `stn_num,stn_name,lat,lon,elevation,start`).
2. **Nominal station count:** 112 stations per ACORN-SAT master list.
3. **Empirical finding  E18 stations unavailable at BoM hqsites endpoint.** Attempts to retrieve the following 18 stations returned HTTP 404 regardless of zero-padding format: `002012, 005026, 008039, 008051, 009510, 009741, 010579, 017031, 023090, 030045, 046037, 046043, 059040, 060139, 066062, 073054, 086071, 094010`. These are encoded as `ACORN_SAT_UNAVAILABLE_STATIONS` in `src/ingestion/bom_acornsat.py::ACORN_SAT_UNAVAILABLE_STATIONS`.
4. **Effective station count = 94.**
5. **Broadacre-region concern (per scope v5 §12.2):** Three of the 18 unavailable stations are broadacre-region-relevant: `008039` (WA Wheatbelt), `008051` (WA Wheatbelt margin), `073054` (NSW Riverina). Impact assessment deferred to Phase 02 quality report.
6. **Files acquired:** 188 CSV files (94 stations ÁE2 variables: tmax + tmin), persisted at `data/processed/bom_acornsat/`.
7. **Column normalisation:** Station list has synonymous column names across BoM's own documentation (`stn_num` / `stnnum`). Implemented a synonym-map in the station-list parser to accept either form.
8. **`src/ingestion/bom_acornsat.py`** implemented with 18-station skip-frozenset, synonym-map column handling, HTTP retry, and idempotent per-station-per-variable file writes.

**Earlier bugs resolved:**
- `lxml` dependency: initial implementation attempted `pandas.read_html` on the BoM ACORN-SAT station master page, which required `lxml`. Replaced with direct CSV endpoint retrieval to eliminate the dependency.
- Schema drift (`stnnum` ↁE`stn_num`): handled via synonym-map.

**Validation:** 10/10 random sample of retrieved CSVs manually inspected; all files structurally valid (date column + temperature column, no obvious corruption).

**Impact:** Provides station-level temperature reference for Phase 02 SILO regional-aggregate sanity check.

**Phase 02 task:** Assess coverage impact of the 18 unavailable stations on regional SILO validation, particularly for broadacre-relevant regions.

---

## 2026-05-17  EPhase 01, Step 06: ABARES Farm Data Portal Historical Estimates

**Context:** Scope v4 §4.3 identifies ABARES Farm Data Portal (FDP) Historical Estimates as the primary source of AAGIS-region yield, area, and production data for wheat, barley, canola.

**Decisions:**

1. **Source URLs (verified):** Three CSVs at `https://www.agriculture.gov.au/sites/default/files/documents/`:
   - `fdp-regional-historical.csv` (9.4 MB, primary, AAGIS region level)
   - `fdp-national-historical.csv` (1.5 MB, sanity-check, has Industry dimension)
   - `fdp-state-historical.csv` (11.4 MB, cross-validation, has State + Industry dimensions)

2. **Empirical finding  Ethree distinct schemas across the CSVs:**
   - Regional: `Variable, Year, ABARES region, Value, RSE` (no Industry dimension)
   - National: `Variable, Year, Value, RSE, Industry` (7 industry values: 'All Broadacre', 'Beef', 'Cropping', 'Dairy', 'Mixed', 'Sheep', 'Sheep-Beef')
   - State: `Variable, Year, Value, RSE, State, Industry`
   Handled via per-level `upstream_columns` + `rename` map in `FDP_FILES` dict.

3. **Empirical finding  Eper-typical-farm semantics (CRITICAL).** ABARES FDP `Value` columns are **survey-weighted per-typical-farm averages, NOT region/national totals**. Triangulation:
   - National `Industry = 'All Broadacre'` wheat 2022 = **656 t/farm**.
   - 656 t/farm ÁE~55,000 broadacre farms ≁E36 Mt total ≁EABS-published national wheat total (~36.6 Mt). ✁Econfirms per-farm semantics.
   - National `Industry = 'Cropping'` wheat 2022 = 3,050 t/farm (~5ÁElarger  Ecropping-specialised farms have larger wheat production per-farm).
   - Regional (`NSW Central West`) wheat 2022 = 807 t/farm (per-typical-broadacre-farm in that region).
   - Initial sanity check compared regional sum to national total, showing +2,400% discrepancy  Eresolved by understanding the per-farm semantics.

   **Implication for Pillars 3 E:**
   - `yield_t_ha = production_t / area_ha` remains dimensionally valid as per-farm ≁Eregional-representative yield (survey-weighted).
   - `production_t` and `area_ha` are per-typical-farm and require **farm-count weighting** for conversion to region totals. This is a Phase 02 processing task per scope v5 §11.6 (`src/processing/abares_aggregation.py`).

4. **Empirical finding  Eregion key mismatch between shapefile and FDP CSV.** The s01 AAGIS shapefile identifies regions by 3-digit hierarchical codes (e.g., `'121'`, `'322'`), while the FDP CSV identifies the same regions by text names (e.g., `'NSW Riverina'`, `'QLD Western Downs and Central Highlands'`). Both encode 32 regions structurally aligned but requires an explicit code-to-name mapping table. This is deferred to Phase 02 per scope v5 §11.6 (`src/processing/region_aggregation.py`).

5. **Empirical finding  Eyear range 1990 E024 (not 1980+).** Scope v4 §3.3 specified "1980+" for yield modeling; ABARES FDP earliest year is 1990. Scope v5 §3.3 updated to reflect the 1990 start.

6. **Commodity table extraction:** For wheat, barley, canola, extracted (region, year, area_ha, production_t, yield_t_ha, area_rse, production_rse) from the regional CSV via role-based pivot. Persisted at `data/processed/abares/<commodity>.csv`.
   - **wheat.csv:** 1,114 rows, 32 regions ÁE35 years, **747 non-NA yields**.
   - **barley.csv:** 1,114 rows, **738 non-NA yields**.
   - **canola.csv:** 1,114 rows, **482 non-NA yields**  Enarrower footprint reflects canola's regional specialisation.

7. **`src/ingestion/abares.py`** implemented with 3-level schema dispatch, per-commodity role-pivot, and idempotent persistence.

**Earlier bugs resolved:**
- Walrus operator syntax error in initial draft: removed unused helper.
- National CSV schema mismatch (missing region dimension) caused initial 3-level dispatch bug; resolved by explicit per-level `upstream_columns` validation.

**Impact:** Provides the primary observed-yield dataset for Pillars 3 E. Two Phase 02 tasks defined: region code-to-name mapping and per-typical-farm-to-region-total farm-count weighting.

**Phase 02 tasks:**
- `src/processing/region_aggregation.py`  EAAGIS 3-digit code ↁEFDP text name mapping table.
- `src/processing/abares_aggregation.py`  EFarm-count weighting utilities.

---

## 2026-05-17  EPhase 01, Step 07: ABS Agricultural Census 2020-21 SA2 ingestion

**Context:** Scope v4 §4.3 identifies ABS Agricultural Census 2020-21 as the SA2-level cross-section for region-importance weighting in Pillars 4 E.

**Decisions:**

1. **Source URL (verified via DevTools):** `https://www.abs.gov.au/statistics/industry/agriculture/agricultural-commodities-australia/2020-21/AGCDCASGS202021.xlsx` (3.87 MB).

2. **Empirical finding  E2020-21 was the FINAL ABS Agricultural Census.** Per ABS publication (26 July 2022): *"The 2020-21 Agricultural Census was the last Agricultural Census to be conducted by the ABS."* Post-2020-21, ABS transitioned to a modernised agricultural statistics pipeline (Levy Payer Register + satellite crop mapping, released annually from 2022-23). Project 5 v1.0 freezes Census-derived weighting at 2020-21 vintage; future extensions requiring SA2 spatial unit and post-2020-21 vintage should incorporate the modernised pipeline (out of v1.0 scope per updated scope v5 §4.3, §13).

3. **Workbook structure (empirically verified):**
   - 2 sheets: `"Contents"` (metadata) and `"Table 1"` (data).
   - `"Table 1"`: rows 1 E = workbook metadata, **row 7 = header, rows 8+ = data**.
   - Columns: `Region code`, `Region label`, `Commodity code`, `Commodity description`, `Estimate`, `Estimate - Relative Standard Error (Percent)`, `Number of agricultural businesses`, `Number of agricultural businesses - Relative Standard Error (Percent)`.
   - **Column names ship with surrounding whitespace** (e.g., `' Estimate '`). Normalised via `raw.columns = [str(c).strip() for c in raw.columns]` at load time.
   - **NA conventions:** `'..'`, `'np'`, `'-'`, `'nil'` handled via `na_values` parameter.

4. **Region hierarchy via digit count of `Region code`:**
   - `0` = Australia (national)
   - 1 digit = State
   - 3 digits = SA4
   - 5 digits = SA3
   - **9 digits = SA2** (primary target for scope §4.3)

5. **Empirical finding  ESA2 commodity counts:**
   - **wheat_sa2.csv:** 394 SA2 rows, 394 non-NA yields, 394 non-NA areas.
   - **barley_sa2.csv:** 367 SA2 rows.
   - **canola_sa2.csv:** 255 SA2 rows.
   Confirms scope §3.2 tier structure (wheat > barley > canola in geographic footprint).

6. **Commodity code discovery  Ecanola under `AGOTHCROP` not `AGOILSEED`.** ABS classifies canola under `Other crops - Oilseeds - Canola` with codes `AGOTHCROP_AHACAN_F` (area), `AGOTHCROP_ATOCAN_F` (production), `CANOLA_YIELD_F` (yield). Yield variables have their own namespace outside the `AGOTHCROP` hierarchy. Initial script attempted `AGOILSEED_*` prefix and failed; corrected via runtime code discovery.

7. **National yield sanity check:**
   - `WHEAT_YIELD_F` national = **2.52 t/ha** (expected 2.5, +0.80% diff  Escreenshot rounding artifact) ✁E   - `BARLEY_YIELD_F` national = **2.67 t/ha** (expected 2.7, ∁E.11% diff) ✁E
8. **Additional deliverables:** Beyond the SA2 tables, also persisted `<commodity>_national_state.csv` (7-8 rows: Australia + states) for downstream triangulation.

9. **`src/ingestion/abs_census.py`** implemented with sheet parsing (skip 6 rows), column-name whitespace normalization, ABS NA-string handling, region-level classification via digit count, and role-pivot for commodity tables.

**New dependency added (scope v5 §9.2):** `openpyxl>=3.1` for XLSX reading.

**Impact:** Provides the SA2-level cross-section for Pillar 4 E region-importance weighting. Documents the discontinuation of ABS Agricultural Census as a structural data constraint on the project's longitudinal analysis future.

**Phase 02 task:** SA2 ↁEAAGIS region mapping for cross-source triangulation (three yield sources: ABARES per-farm, ABS SA2, AGFD simulation).

---

## 2026-05-18  EPhase 01, Step 08 (initial run): OpenWeather One Call 3.0 historical ingestion (partial)

**Context:** Scope v4 §4.5 defines OpenWeather as the validation comparator for a SILO cross-validation study conducted at Phase 02 / Phase 09. Ten AAGIS region centroids ÁE2022-01-01 to 2024-12-31 = 10,960 daily records were the target.

**Decisions:**

1. **Endpoint (verified):** `GET https://api.openweathermap.org/data/3.0/onecall/day_summary?lat={lat}&lon={lon}&date={YYYY-MM-DD}&units=metric&appid={key}`.

2. **Subscription:** OpenWeather One Call API 3.0 Base plan activated. Free quota: 1,000 calls/day. After free: £0.0012/call. Daily hard limit set to **11,000** in dashboard for cost containment.

3. **Ten regions approved (scope v5 §4.5).** Centroids computed via `shapely.geometry.representative_point()` (guaranteed inside polygon, more honest than geometric centroid for irregular AAGIS shapes). WA region 521 flagged an informational warning: `representative_point` and `centroid` differ by 180.2 km due to WA wheatbelt's narrow arc-shaped polygon. This is expected and the representative point (Wongan Hills area) is correctly inside the WA cropping zone.

4. **Region-name reconciliation.** During s08a approval, region 322 was verbally approved as `"QLD Eastern Darling Downs"`. The AAGIS shapefile actually labels code 322 as `"QLD Western Downs and Central Highlands"` (empirical finding at s08 dry-run). Both regions are broadacre-relevant and geographically adjacent; the shapefile name is the canonical name and used going forward (scope v5 §4.5).

5. **API key handling:** Stored in `.env` (gitignored) per scope v5 §11.11. Loaded via `python-dotenv`. Masked in logs (e.g., `061dc7…9e58`).

6. **Configuration:**
   - Sleep 1.05 s between calls (targeting ~57 calls/min under the 60/min ceiling).
   - Daily call soft-quota 10,500 (below 11,000 hard limit with 500 headroom).
   - Persistence format: Parquet, one file per `(region, year)` at `data/raw/openweather/<region_code>_<year>.parquet`.

7. **First run execution (2026-05-18, 01:15 ↁE09:10 AEST):** 10,500 calls consumed, 9,863 new rows persisted, **1 permanent skip (region 222 Wimmera, 2022-11-23)** after 3 retries all returned HTTP 504. Effective rate ~22 calls/min (API-server-side response time limits, not client-side rate-limit).

**Adaptive override  EParquet crash (Project 4 lesson-equivalent):**
- Between 100 and 400 calls into the first execution attempt, `pandas.DataFrame.to_parquet()` raised `ImportError: pyarrow required for Parquet support`. `pyarrow` had not been listed in `requirements.txt` at that point.
- Corrective action: `pip install pyarrow>=15`, updated `requirements.txt` (scope v5 §11.7 first-use rule), re-ran s08. All previously fetched calls (~300-400) were lost from memory and re-fetched on the retry (cost: ~£0.36 = negligible).
- Documented as an explicit scope §11.5 adaptive override: `requirements.txt` first-use-rule violation caught during execution, corrected in-place.

**Cost (first run):** ~£11.40 (10,500 calls total, of which 1,000 free + 9,500 paid at £0.0012/call).

**Impact:** 95.8% of target dataset acquired (10,500 / 10,960). Region 631 (TAS Tasmania) remained partial: year 2023 at 272/365 days, year 2024 at 0/366 days. Daily quota reached; run exited cleanly with resumable state.

---

## 2026-07-09  EPhase 01, Step 08 (resume run): completion

**Context:** After a 52-day pause (May 19  EJuly 8), the s08 main run was resumed to complete the remaining 460 daily records for region 631 (TAS Tasmania) and to attempt recovery of the region 222 (VIC Wimmera) 2022-11-23 permanent skip.

**Decisions:**

1. **Resume run (2026-07-09, 13:05 ↁE13:26 AEST, 21 minutes):**
   - 460 calls consumed.
   - Region 121 E22 (28 (region, year) files): all `already cached`, skipped in ~10 seconds.
   - Region 222 year 2022: **1 date auto-recovered** (2022-11-23)  Ethe previously HTTP-504-skipped date was re-fetched successfully on resume without special intervention. HTTP 504 was confirmed transient.
   - Region 631 year 2023: 93 new dates fetched (272 ↁE365 rows).
   - Region 631 year 2024: 366 new dates fetched (0 ↁE366 rows).

2. **Total coverage (final):** **10,960 / 10,960 daily records (100.0%)** across 30 Parquet files.

3. **Total cost (both sessions):** ~£11.40 (2026-05-18) + £0.00 (2026-07-09, within free daily quota) = **~£11.40 ≁EAUD $22**.

4. **`phase01_s08b_refetch_singleton.py` script  Eretired as redundant.** A dedicated singleton refetch script had been drafted (2026-07-09, pre-resume) to force-retry the 222_2022-11-23 date via 5-outer ÁE3-inner retries. When the main resume run auto-recovered this date on its first attempt, the singleton script became redundant. Deleted from `scripts/` without commit history entry (never persisted to git). Documented here for audit trail per scope §11.5.

5. **Empirical finding  Efile size variation.** Parquet file sizes range 21.8 E0.5 KB across the 30 files. The smaller files (~22 KB: region 123 NSW Riverina, region 521 WA Central WB) correspond to arid regions where daily precip/wind values are frequently absent/near-zero, allowing Parquet dictionary compression to be more effective. This is a healthy signal reflecting climatic reality, not a data-quality issue.

**Total time to complete Phase 01 s08:** initial run 7h 55min + resume 21min = **8h 16min** across two sessions.

**Impact:** Completes Phase 01 data acquisition. All 8 sources acquired to Master 研究老Egrade completeness. Phase 01 complete.

**Phase 02 task:** OpenWeather–SILO comparison study using this 10-region ÁE3-year sample (scope v5 §5.6.4).

---

## 2026-07-09  EPhase 01, Step 09: Phase 01 closure ceremony

**Context:** All eight data acquisition steps (s01–s08) complete. Executing the Phase 01 closure ceremony per `portfolio_finalisation_playbook.md` §3.

**Actions:**

1. **Scope revision:** `docs/project_scope.md` bumped from v4 to **v5**, reflecting 7 empirical findings from Phase 01 data acquisition per `portfolio_finalisation_playbook.md` §11 ("structural revision ↁEnew version" discipline). v4 preserved in Appendix C document history. All 7 findings incorporated into v5's substantive sections (§3.1, §3.3, §4.1, §4.2, §4.3, §4.5, §5.1, §5.3, §5.6.4, §11.6, §12.2, §13).

2. **PROJECT_LOG.md:** Entries for s02–s08 (this batch of 7 entries) appended, plus s09 closure entry. Total PROJECT_LOG line count grows from 304 to ~700+ lines.

3. **`data/raw/manifest.yaml`:** Populated with entries for all 8 sources (previously only s01). Each entry documents: canonical name, vintage, retrieval URL, retrieval date, license, and known quirks per scope v5 §4.8.

4. **`docs/methodology.md`:** New skeleton file created. Structured placeholders for Phase 01 decisions (data source selection rationale, spatial unit choice, per-farm-semantics discipline) with the intent that Phase 02+ decisions will be appended over the project lifecycle.

5. **`docs/phase_summaries/phase01_summary.md`:** New file created summarising Phase 01 deliverables, empirical findings, and Phase 02 handoff tasks (gitignored per playbook convention).

6. **README.md:** Regenerated via `scripts/update_readme.py` to reflect Phase 01 completion.

7. **Git operations:**
   - Final commit on `phase-01-data-acquisition` branch: `[Phase 01 s09] Closure ceremony  Escope v5, manifest, PROJECT_LOG, methodology skeleton, phase01 summary`.
   - Merge to `main` with `--no-ff`: `Merge phase-01-data-acquisition: Phase 01 complete (8 data sources, ~12 GB acquired)`.
   - Annotated tag `v0.1-phase01-complete` on the merge commit.
   - Push `origin main` and `origin --tags`.

**Phase 01 total elapsed calendar time:** 2026-05-14 ↁE2026-07-09 (57 days), of which ~10 effective working days.

**Phase 01 total data volume acquired:** ~12 GB across 8 sources.

**Phase 01 total code:** ~4,500 lines across 8 ingestion modules + 2 processing modules + 8 orchestration scripts + 3 utility modules.

**Total spend:** ~£11.40 (OpenWeather One Call API only; all other sources are free public data).

**Phase 02 tasks summarised (from s02–s08 findings):**
1. AAGIS 3-digit code ↁEFDP text name mapping (`src/processing/region_aggregation.py`).
2. Per-typical-farm ↁEregion-total farm-count weighting (`src/processing/abares_aggregation.py`).
3. Grid-vs-region SILO aggregation consistency check.
4. Cropping-mask threshold sensitivity comparison (t005 vs t010 vs t020).
5. ACORN-SAT 18-station-unavailable coverage impact assessment.
6. OpenWeather–SILO agreement metrics computation.
7. Three-way yield-source triangulation (ABARES per-farm, ABS SA2, AGFD deferred to Phase 09).

**Impact:** Phase 01 complete. All substantive scope §6.2 Phase 01 deliverables satisfied. Phase 02 kickoff enabled from a clean, documented, reproducible state.

## 2026-07-13 — Phase 02, Step 01: AAGIS region code ↔ FDP name mapping (Task A)

**Context:** Phase 02 (Data Quality & Cross-Validation) kickoff. Working branch `phase-02-quality-and-crossvalidation` created from `main` (tag `v0.1-phase01-complete`). Baseline-hygiene fix first: `PROJECT_WORKFLOW.md` (Project 5 edition) was untracked at Phase 01 close and is now committed (`chore:` commit `f5c2dad`). Task A (scope v5 §3.1, §6.2, §11.6; phase01_summary §4.1) builds the canonical bridge between the AAGIS 3-digit region code (shapefile) and the ABARES FDP text region name (CSV), unblocking Pillar 3–5 spatial joins.

**Empirical verification before creation (PROJECT_WORKFLOW §2.4):** Inspected the actual data products before writing any code:
- `data/processed/aagis_regions_repaired.gpkg` feature table `aagis_regions`, attribute fields `[aagis, class, name, zone]` (32 rows).
- `data/raw/abares/fdp-regional-historical.csv` column `ABARES region` (32 unique names).

**Actions:**

1. Created `src/processing/region_aggregation.py`: loads the canonical code↔name↔zone table from the GeoPackage, validates it against the FDP, and persists it atomically (`.part` → rename).
2. Created `scripts/phase02_s01_region_mapping.py`: orchestration; prints the 32-row table + validation report, exits non-zero on failure.
3. Created `tests/test_region_aggregation.py`: 4 tests (2 pure-logic, 2 data-backed; data-backed tests skip if the gitignored data is absent). First `tests/` directory in the project.
4. Added `pytest>=8.0` to `requirements-dev.txt` (first-use dependency rule, PROJECT_WORKFLOW §8.2 — first Phase to import pytest).
5. Ran the pipeline: **32/32 codes → 32 FDP names, zero orphans**; all 7 validation checks PASS; wrote `data/processed/region_mapping.csv` (gitignored, regeneratable). `pytest`: 4 passed.

**Adaptive override (PROJECT_WORKFLOW §4.2):**
- **Original plan** (phase01_summary §4.1): construct the mapping by cross-referencing a shapefile `AAGISname` field against the FDP names, validating via state prefix.
- **Empirical trigger:** the GeoPackage already carries a `name` field whose 32 values match the FDP `ABARES region` names EXACTLY (zero orphans, verified). There is no `AAGISname` field; the real field is `name`.
- **New plan:** Task A reduces from *construction* to *read + validate*. The module reads the canonical table directly and validates name-set equality, code well-formedness/uniqueness, code redundancy (`aagis == class`, all 32), and state-prefix sanity.
- **Downstream consequence:** none negative — the mapping is more robust (single authoritative source) and cheaper to produce. Downstream Pillar 3–5 joins can key on either code or name.

**Latent-bug finding (Phase 01 `src/ingestion/abares.py`):** `cross_check_aagis_region_names()` selects its region field by substring match on "region"/"aagis"; given the actual columns `[aagis, class, name, zone]` it picks the CODE column `aagis`, so it compared codes against names and always reported `n_matching = 0` — it never actually validated name equality. No data was corrupted (finding #1 "explicit mapping required" remains correct). Correct validation now lives in `region_aggregation.validate_region_mapping`. **Remediation deferred** to a dedicated Phase 02 step (out of s01 scope per PROJECT_WORKFLOW §2.3): a minimal fix to the field selection plus a regression test, logged as its own entry. Priority low, non-blocking. Reproducibility motivation: a fresh clone re-running s06 would otherwise see the misleading diagnostic.

**Secondary confirmation:** the `zone` label agrees with the code's 2nd-digit decode (1=Pastoral, 2=Wheat Sheep, 3=High Rainfall) for all 32 rows; zone distribution 12/12/8 matches the s01 record; state distribution NSW 6 / VIC 4 / QLD 8 / SA 4 / WA 5 / TAS 1 / NT 4 = 32.

**Scope:** No revision. This is a code-level finding, not a structural scope change; scope stays v5 (PROJECT_WORKFLOW §4.3). Finding #1 (mapping required) remains valid.

**Impact:** Task A complete — a validated 32/32 region mapping is persisted and Pillar 3–5 spatial joins are unblocked. Next in Phase 02: ABARES per-typical-farm → region-total weighting (Task B) and the deferred `cross_check_aagis_region_names` remediation.

## 2026-07-15 — Phase 02, Step 02: ABARES per-typical-farm → region-total weighting (Task B)

**Context:** Task B (scope v5 §4.3, §5.3, §6.2, §11.6; phase01_summary §4.1, §5). ABARES FDP reports per-typical-farm averages (Phase 01 finding #2), so extensive quantities (sown area, production) require farm-count weighting to become region totals. Builds on the s01 region mapping. Branch `phase-02-quality-and-crossvalidation`.

**Correction (append-only log hygiene):** The preceding s01 entry is mis-dated 2026-07-13; the correct date is 2026-07-15. Both s01 and s02 were executed on 2026-07-15. Recorded here rather than editing the already-committed s01 line, per the append-only PROJECT_LOG convention (scope §7.1).

**Denominator decision (empirically grounded; overrides phase01_summary §5 default):** Use the FDP `Population` variable (the survey's estimate of broadacre farm businesses per region-year) as the weighting denominator, NOT the ABS Census 2020-21 SA2 business counts. Rationale: region-native and per-year (no SA2<->AAGIS spatial join needed); internally exact because `Population` is the survey expansion factor — Σ_region(per-farm × Population) reconstructs the FDP national total to ratio 0.999–1.001 (verified wheat 2020/2021/2022). ABS-SA2 and ABARES national counts are retained as independent Task G cross-checks, not the primary weight.

**Actions:**

1. Created `src/processing/abares_aggregation.py`: loads `Population`; weights `area_ha`->`area_total_ha` and `production_t`->`production_total_t`; carries `yield_t_ha` unchanged (intensive; per finding #2 it needs no weighting); atomic `.part`->rename write of region-total CSVs.
2. Created `scripts/phase02_s02_abares_weighting.py`: runs wheat/barley/canola, validates, prints a per-year report, exits non-zero on failure.
3. Created `tests/test_abares_aggregation.py`: 9 tests (pure-logic weighting + RSE-gate behaviour + data-backed ±5% reconstruction per commodity). All pass.
4. Ran the pipeline: worst graded relative error wheat 0.31%, barley 0.69%, canola 3.35% — all within ±5%. Wrote three `data/processed/abares/<commodity>_region_totals.csv` (gitignored, 1114 rows each). Weighting identity independently verified 1114/1114 exact.

**New data-quality rule — survey-reliability RSE gate (Kota-approved):** A year is graded against the ±5% tolerance only if it has full 32-region coverage AND the FDP national production RSE ≤ 20%. Motivation: the exit criterion's "survey-error tolerance" must not be applied to years whose survey error is itself extreme. Empirical trigger: early canola (1990–1993) has national production RSE 22–88% and is integer-rounded to 1–3 t/farm, so reconstruction error reaches 16–29% from quantization + sampling noise alone; from 1994 on, RSE ≤ 15% and reconstruction error ≤ 3.4%. The gate excludes 1990–1993 for canola (1990–91 are also partial-coverage), leaving 31 graded canola years. Constant `RSE_GATE_THRESHOLD = 20.0` in `abares_aggregation.py`.

**Finding — crop-specific reliable yield window:** wheat and barley reconstruct reliably across 1990+, but canola's reliable window effectively begins 1994. This refines scope §3.3 (currently "FDP earliest = 1990"). Scope treatment (patch v5.1 vs methodology.md note) is deferred to the Phase 02 closure ceremony, where all Phase 02 findings are reconciled together.

**Dependencies:** none new (`pytest` was added at s01).

**Scope:** No revision at this step; scope stays v5. Candidate refinements (crop-specific yield window; `Population` denominator decision; RSE-gate methodology) are logged here for the Phase 02 closure decision.

**Impact:** Task B complete — the per-typical-farm -> region-total weighting pipeline is built, tested, and validated within ±5% for wheat, barley, and canola; region-total CSVs persisted. Unblocks Pillar 3–5 analyses that need region-total production/area (yield_t_ha was already usable). Next in Phase 02: the deferred `cross_check_aagis_region_names` remediation and/or the cross-validation tasks (C grid-vs-region SILO, D OpenWeather–SILO, E ACORN-SAT coverage).

## 2026-07-15 — Phase 02, Step 03: cross_check_aagis_region_names remediation

**Context:** Discharges the deferred Phase 01 latent-bug fix flagged in the s01 entry. `src/ingestion/abares.py::cross_check_aagis_region_names` selected its region field by substring match on "aagis"/"region"; given the actual GeoPackage columns [aagis, class, name, zone] it picked the numeric CODE column `aagis` and compared codes against FDP names, always reporting n_matching = 0 — it never validated name equality. Non-blocking; recorded at s01, remediated here as its own small step per PROJECT_WORKFLOW §2.3. Branch `phase-02-quality-and-crossvalidation`.

**Adaptive override / fix (PROJECT_WORKFLOW §4.2):**
- Original behaviour: substring field selection resolved to the numeric `aagis` code column.
- Fix: prefer a known name field (`name`, `aagisname`, `aagis_name`, `region_name`, `region`); otherwise fall back to the first non-numeric text column; never a numeric code column. The dict return-value contract (keys) is unchanged, so the s06 orchestrator that consumes this helper is unaffected.

**Actions:**

1. Edited `cross_check_aagis_region_names` field-selection logic (src/ingestion/abares.py).
2. Created `tests/test_abares_region_name_check.py`: locks `aagis_field_used == "name"`, 32/32 name matches, zero orphans on the real data (skips if data absent).
3. Ran: new regression test PASS; full suite 14 passed (no existing test broke).

**Dependencies:** none new.

**Scope:** No revision. Code-level correctness fix; scope stays v5.

**Impact:** The Phase 01 name-equality diagnostic now works correctly and agrees with the s01 `region_aggregation.validate_region_mapping` result (32/32, zero orphans). Deferred debt cleared. Remaining Phase 02: cross-validation tasks C (grid-vs-region SILO), D (OpenWeather–SILO), E (ACORN-SAT coverage), then the closure ceremony.

## 2026-07-16 — Phase 02, Step 04a: SILO grid -> AAGIS region means + Phase 01 s04 lat-flip fix (Task C, part 1)

**Context:** Task C part 1 (scope v5 §4.2, §6.2; phase01_summary §4.2): aggregate the cropping-masked SILO climate grid to AAGIS-region climatologies for the grid-vs-region consistency check. Branch `phase-02-quality-and-crossvalidation`.

**Deliverables (s04a):**

1. `src/processing/silo_region_aggregation.py` — cropping-cell -> AAGIS-region assignment (geopandas point-in-polygon, cached parquet); cos(lat) area-weighted region means; single-pass annual + monthly-climatology aggregation.
2. `scripts/phase02_s04a_silo_region_means.py` — orchestrator (coverage report + 1991-2020 reference-period aggregation).
3. `tests/test_silo_region_aggregation.py`, `tests/test_silo_masking.py`.
4. Gitignored outputs: `silo_cell_region_map.parquet` (28,577 cells), `silo_region_means/annual_1991_2020.csv` (5,400 rows), `monthly_climatology_1991_2020.csv` (2,160 rows).

**Cell-region coverage:** 28,721 t005 cropping cells -> 28,577 assigned (99.5%; 144 near-coast cells outside all regions); 30/32 regions covered (the 2 uncovered are Pastoral: WA Kimberley, NT Alice Springs). Every broadacre (Wheat-Sheep / High-Rainfall) region covered; cell counts concentrate in the wheat belt (WA 521: 4,442; NSW 121: 3,368; ...), matching Australian broadacre geography.

**MAJOR finding — Phase 01 s04 latitude-flip masking bug (discovered at s04a, fixed):**
- **Symptom:** under correct coordinate-based sampling only 7.9% of cropping cells carried SILO data; WA/SA/VIC/TAS wheat-belt regions were ~0% valid; Tasmania all-NaN.
- **Root cause:** `src/ingestion/silo.py` applied the mask via `mask.assign_coords(lat=da_raw["lat"].values)` — a POSITIONAL coordinate substitution. The mask is latitude-descending (cropping_mask.py `np.linspace(-10, -44)`) while SILO data is ascending, so the substitution flipped the mask north-south. Cropping cells were masked at their latitude mirror (WA wheat-belt -> Pilbara, Tasmania -> tropical ocean) and the true cropping cells' climate was set to NaN. The flipped values looked plausible (WA sampled arid Pilbara, ~288 mm / 33 degC), which is why it evaded notice until the region-level cross-check.
- **Fix:** replace positional `assign_coords` with coordinate-value `reindex(..., method="nearest", tolerance=0.025)`; add `_assert_masking_sane` guard (latitude-centroid check, fail-fast on any flip); add synthetic regression tests (`tests/test_silo_masking.py`). The s04a aggregation resolves grid indices by coordinate value (`resolve_cell_grid_indices`), robust to axis ordering.
- **Remediation:** deleted the flipped processed SILO; re-ran `phase01_s04` (re-download raw + re-mask, guard active, 375 files, 0 errors, 13.38 GB) on 2026-07-15/16; re-ran s04a.
- **Verification:** post-fix all 6 variables cover all 30 regions (5,400 annual rows), zero NaN, zero spurious rain=0; region climatologies plausible and geographically correct (WA wheat-belt 403 mm / 24.1 degC; TAS 656 mm / 16.9 degC; latitude-consistent temperature gradient). Full suite: 23 passed, including the TAS alignment guard that fails on flipped data.

**Discipline note:** this is exactly the class of data-integrity error Phase 02 (Data Quality & Cross-Validation) exists to catch, found before any Pillar 1-2 analysis was built on it. Post-masking spatial validation should have existed in Phase 01 s04; it now does.

**Adaptive override (PROJECT_WORKFLOW §4.2):** the s04a plan (aggregate existing masked SILO) changed mid-execution upon discovering the upstream masking flip; the plan expanded to include the Phase 01 s04 fix + full SILO regeneration before the aggregation could be trusted.

**Dependencies:** none new.

**Scope:** no revision at this step; scope stays v5. The Phase 01 s04 masking correction and the new masking guard are candidates for a methodology.md note (and possibly scope patch v5.1) at the Phase 02 closure ceremony. The Phase 01 tag `v0.1-phase01-complete` is not re-cut: the corrected artifact is gitignored regenerable data, and the code fix is committed within Phase 02.

**Impact:** s04a complete — validated, area-weighted SILO region climatologies persisted; a Phase 01 latitude-flip data bug corrected across the full SILO archive (13.38 GB). Unblocks s04b (grid-vs-region consistency write-up) and the Pillar 1-2 climate pipeline. Next: s04b consistency documentation; then Task D (OpenWeather-SILO) and Task E (ACORN-SAT coverage).

## 2026-07-17 — Phase 02, Step 04b: grid-vs-region SILO aggregation consistency check (Task C, part 2)

**Context:** completes the grid-vs-region consistency check (scope v5 §4.2, §6.2), building on the s04a region climatologies (and the s04a-fixed SILO data). Per the Phase 02 decision criteria, INTERNAL consistency is the primary/load-bearing check (reproducible from committed code + regenerable data); a BoM station comparison (observed, cited) is a supporting EXTERNAL plausibility check. Branch `phase-02-quality-and-crossvalidation`.

**Deliverables:**

1. `src/processing/climate_consistency.py` — internal-consistency battery + external BoM comparison.
2. `scripts/phase02_s04b_grid_region_consistency.py` — orchestrator (exit 1 on internal failure).
3. `tests/test_climate_consistency.py` (4 synthetic + 1 data-backed).
4. `outputs/tables/s04b_region_climatology_summary.csv`, `outputs/tables/s04b_external_comparison.csv` (committed small public tables).

**Internal consistency (primary) — all pass, 20 broadacre regions:**
- Coverage: every broadacre region present for all 6 variables; zero NaN; zero spurious zero-rain.
- Temperature-latitude: corr(latitude, tmax) = +0.887, corr(latitude, tmin) = +0.938 (further south -> cooler), confirming area-weighting preserves the latitudinal temperature structure.
- Rainfall seasonality regime: SW/southern Mediterranean regions (WA 521/522/531, SA 421) winter-dominant; subtropical/monsoon northern regions (QLD 322/331/332, NSW 121, NT 713/714) summer-dominant — reproduces the continental winter->summer rainfall gradient (WA 521 winter 54% / summer 19%; QLD 322 summer 54% / winter 19%; NT 713/714 summer 71-77%).

**External plausibility (secondary; BoM normals, cited):**
- VIC Mallee (221) vs Mildura: rain 308 vs 278 mm; tmax 23.8 vs 23.8 degC.
- WA Wheat Belt (521) vs Merredin: rain 402 vs 310 mm (region spans wetter south Katanning ~480 to drier east Merredin ~310); tmax 24.1 vs 25.4.
- NSW Riverina (123) vs Wagga Wagga: rain 469 vs 614 mm (region mean between drier west Hay ~365 and wetter east Wagga 614); tmax 23.2 vs 22.5.
- tmax within +-3 degC and rainfall within region-vs-point tolerance for all anchors. Sources: BoM "Climate statistics for Australian locations" (Mildura 076031, Merredin 010092, Wagga 072150).

**Decision-criteria note:** internal (reproducible) primary, external (observed BoM, cited) secondary — per the Phase 02 criteria discussion. `matplotlib` not added (scope earmarks it for Phase 03 EDA); a seasonality figure is deferred to Phase 03. The narrative will be consolidated into the data quality report at Phase 02 closure.

**Dependencies:** none new.

**Scope:** no revision; scope stays v5.

**Impact:** Task C complete — grid-vs-region aggregation consistency confirmed (internal quantitative battery + external BoM plausibility) and documented in `outputs/tables`. The corrected SILO region climatologies are trustworthy inputs for Pillars 1-2. Remaining Phase 02: Task D (OpenWeather-SILO comparison), Task E (ACORN-SAT coverage), then closure.

## 2026-07-17 — Phase 02, Step 05: ACORN-SAT coverage impact assessment (Task E)

**Context:** Task E (scope v5 §4.2, §12.2; phase01_summary §4.2, finding #5). Quantifies the impact of the 18 unavailable ACORN-SAT stations on regional SILO validation. ACORN-SAT is the homogenised station truth used to sanity-check SILO grids; a broadacre region with no available station can only be validated indirectly. Branch `phase-02-quality-and-crossvalidation`.

**Deliverables:**

1. `src/processing/acornsat_coverage.py` — station load + availability, point-in-polygon assignment to AAGIS regions, per-region coverage counts + broadacre under-representation flags.
2. `scripts/phase02_s05_acornsat_coverage.py` — orchestrator.
3. `tests/test_acornsat_coverage.py` (2 synthetic + 1 data-backed).
4. `outputs/tables/s05_acornsat_region_coverage.csv` (committed).

**Method:** 112 ACORN-SAT stations (94 available / 18 unavailable per `bom_acornsat.ACORN_SAT_UNAVAILABLE_STATIONS`) assigned by point-in-polygon to AAGIS regions; per-region available/unavailable counts; broadacre (Wheat-Sheep / High-Rainfall) regions flagged no_station (0 available) or sparse (1 available).

**Findings:**
- 9 stations fall outside all AAGIS regions (remote islands / offshore) and are excluded; 86 available + 17 unavailable land in mainland regions.
- 20 broadacre regions, 51 available stations among them.
- **Broadacre region with NO available station:** QLD Eastern Darling Downs (321) — SILO there is validated only indirectly.
- **Sparse (single available station):** NSW Central West (122), VIC Wimmera (222), VIC Central North (223), WA South West Coastal (531).
- **Broadacre-relevant unavailable stations (lost truth):** 008039 Dalwallinu -> 522 WA Northern & Eastern Wheat Belt; 008051 Geraldton -> 521 WA Central & Southern Wheat Belt; 073054 Wyalong -> 122 NSW Central West. NSW Central West (122) is doubly affected (sparse AND lost Wyalong). Note: the bom_acornsat comment labelled Wyalong "NSW Riverina"; the actual polygon assignment is 122 NSW Central West — the code comment was approximate.

**Assessment:** ACORN-SAT coverage of broadacre regions is generally adequate, but SILO-validation confidence is lower for QLD Eastern Darling Downs (no station) and the four sparse regions; the 18 unavailable stations remove station truth from the WA Wheatbelt (521/522) and NSW Central West (122). Documented, not a blocker — downstream SILO-based indicators in these regions carry a validation caveat.

**Dependencies:** none new.

**Scope:** no revision; scope stays v5. Finding #5's "3 broadacre-relevant" unavailable stations are confirmed; the Wyalong region-label refinement (Central West, not Riverina) is a minor factual note, candidate for a methodology.md note at closure.

**Impact:** Task E complete — ACORN-SAT station coverage per AAGIS region documented, broadacre under-representation flagged. Phase 02 cross-validation tasks C and E done; remaining: Task D (OpenWeather-SILO comparison), then the closure ceremony.

## 2026-07-17 — Phase 02, Step 06: OpenWeather vs SILO comparison study (Task D; scope §5.6.4)

**Context:** Task D — auxiliary methodological side-finding (Pillar 6; scope v5 §5.6.4). Quantifies OpenWeather day-summary API vs gold-standard SILO agreement at the 10 sampled AAGIS centroids over 2022-2024 (1,096 paired days per centroid; 10,960 per variable). Branch `phase-02-quality-and-crossvalidation`.

**Deliverables:**

1. `src/processing/openweather_silo_compare.py` — pair OW daily with SILO at the nearest cropping cell; tmax/tmin/rain direct, humidity via SILO-derived RH (Tetens); RMSE / bias(OW-SILO) / Pearson correlation per centroid x variable + pooled.
2. `scripts/phase02_s06_openweather_silo.py`.
3. `tests/test_openweather_silo_compare.py` (5 synthetic + 1 data-backed).
4. `outputs/tables/s06_openweather_silo_metrics.csv` (40 rows = 4 variables x 10 centroids).

**SILO extraction:** the masked SILO archive keeps only cropping cells, so SILO is sampled at the nearest cropping cell to each centroid. Offset < 5 km for 8 centroids, 17.5 km for 322, and 66.7 km for 631 (Tasmania — sparse Tasmanian cropping; flagged, and its comparison is correspondingly weaker).

**Results (pooled, bias = OpenWeather - SILO):**
- tmax: corr 0.97, RMSE 1.9 degC, bias -0.98 (OW slightly cool).
- tmin: corr 0.92, RMSE 2.6 degC, bias +0.92 (OW slightly warm). Together the API compresses the diurnal range by ~1-2 degC vs SILO.
- rain: corr 0.33, RMSE 4.8 mm, bias -0.10 — LOW DAILY correlation (point API vs 5 km grid placement/timing mismatch) but negligible bias (totals agree).
- humidity (SILO-derived RH, Tetens approximation): corr 0.84, RMSE 10.4 %, bias +1.0 — moderate; carries the derivation caveat (SILO ships vapour pressure; afternoon temperature proxied by the daily maximum).
- Per-centroid temperature correlations 0.90-0.99; the TAS centroid (631) is the weakest (tmin corr 0.81, humidity corr 0.59), consistent with its 67 km SILO offset.

**Finding (scope §5.6.4):** OpenWeather is a usable temperature proxy (high correlation, ~2 degC RMSE, small diurnal-range compression) but NOT a substitute for SILO on daily rainfall (low daily correlation, though unbiased). This supports the project design: SILO is the primary gold-standard climate input; OpenWeather is a validation comparator only, never a training input.

**Dependencies:** none new.

**Scope:** no revision; the §5.6.4 auxiliary result is now populated with concrete metrics (previously a placeholder).

**Impact:** Task D complete. All Phase 02 reconciliation (A, B) and cross-validation (C, D, E) tasks are done. Remaining Phase 02: the closure ceremony — data quality report (`docs/phase_summaries/phase02_summary.md`), manifest/methodology updates, scope-revision decision, and the git merge + tag.

## 2026-07-17 — Phase 02, Step 07: Phase 02 closure ceremony

**Context:** All Phase 02 tasks complete (A, B reconciliation; C, D, E cross-validation; F, G, H deferred to Phase 03/04/09). Executing the closure ceremony (PROJECT_WORKFLOW §9).

**Actions:**

1. **Scope revision v5 → v5.1 (patch):** §3.3 refined — canola reliable yield window begins 1994 (RSE-gate finding); wheat/barley remain 1990+. Appendix C history row added; header version + date bumped. Other Phase 02 methods recorded in methodology.md §7 and phase02_summary.md (not accumulated inline in scope).
2. **methodology.md §7 populated:** region mapping (Task A), Population weighting + RSE gate (Task B), SILO masking latitude-flip fix + guard (Task C), grid-vs-region consistency (Task C), ACORN-SAT coverage (Task E), OpenWeather–SILO (Task D).
3. **data/raw/manifest.yaml:** scope_version -> v5.1; new `phase02_processed_products` section (region_mapping, abares region-totals, silo cell-region map, silo region means) + committed output tables.
4. **docs/phase_summaries/phase02_summary.md** created (data quality report / Phase 03 handoff; gitignored).
5. **PROJECT_LOG.md:** s01–s06 step entries + this closure entry.
6. **Git ceremony (to execute):** closure commit on `phase-02-quality-and-crossvalidation`; `--no-ff` merge to `main`; annotated tag `v0.2-phase02-complete`; push `main` + tags.

**Phase 02 deliverables:** 6 processing modules, 6 orchestrator scripts, 7 test files (37 tests passing), 4 committed output tables, 4 gitignored regenerable data products. 2 code fixes (silo.py masking flip + `_assert_masking_sane` guard; abares.py `cross_check` field selection). 1 dev dependency (pytest). 8 commits on the phase branch before closure.

**Headline finding:** the Phase 01 s04 SILO masking latitude-flip bug was discovered at s04a and fixed; the full 12 GB SILO archive was regenerated correctly — the data-quality process caught it before any Pillar analysis was built on it.

**Appendix A discipline scorecard (Phase 02 close — all ✓):**
- Observed-vs-derived — SILO/BoM observed; OpenWeather comparator only; no model-as-truth. ✓
- Empirical honesty — SILO flip, cross_check bug, canola window reconciled into scope v5.1 / methodology / log, not hidden. ✓
- Adaptive overrides — logged as discrete entries (Population denominator, RSE gate, flip fix). ✓
- Empirical verification before creation — field/structure inspected before every module. ✓
- Reproducibility — fresh clone reproduces via scripts (SILO re-download caveat acknowledged). ✓
- First-use dependency rule — pytest added at s01. ✓
- Idempotent atomic persistence — all writers use `.part` -> rename. ✓
- Manifest as source of truth — phase02_processed_products added. ✓
- Scope discipline — v5 -> v5.1 patch (not accumulated inline). ✓
- Git per-phase branching — `--no-ff` merge preserves structure. ✓
- Annotated tag with substance — `v0.2-phase02-complete`. ✓
- Bilingual discipline — English artefacts, Japanese conversation, no mixing. ✓

**Impact:** Phase 02 COMPLETE. Analysis-ready, cross-validated inputs for Pillars 1–6, with an important Phase 01 data-integrity bug corrected. Phase 03 (Exploratory Analysis) is enabled from a clean, documented, reproducible state at tag `v0.2-phase02-complete`.

## 2026-07-18 — Phase 03, Step 01: data inventory + EDA scaffolding

**Context:** Phase 03 (Exploratory Data Analysis) kickoff. Working branch
`phase-03-eda` created from `main` (tag `v0.2-phase02-complete`). Step 01 goal
(scope §6.2): load the Phase 02 analysis-ready inputs, verify their shapes /
coverage / region-key alignment, and stand up the EDA scaffold — a verified data
baseline before any substantive EDA or the optional-crop decision.

**Empirical verification before creation (PROJECT_WORKFLOW §2.4):** inspected the
real artefacts before writing code. Findings that corrected scope Appendix A:
- `notebooks/` was empty (only `.gitkeep`); `03_exploratory_analysis.ipynb` is the
  project's FIRST notebook and sets the notebook conventions (kernel = `.venv`
  3.12; executes top-to-bottom; every figure carries a one-sentence interpretation).
- `src/viz/` held only an empty `__init__.py` (no `maps.py`, contrary to Appendix A);
  `src/viz/style.py` is therefore new with no conflict.
- The full masked SILO daily archive is on disk (1961–2024 for
  tmax/tmin/rain/vp/radiation, 1970–2024 for evap_pan). A full-record region
  re-aggregation (s02) needs NO re-download.
- The persisted SILO region means cover the 1991–2020 reference period only
  (`silo_region_means/annual_1991_2020.csv`) — the gap handed to s02.

**Deliverables:**
1. `src/processing/input_inventory.py` — loads the 14 Phase 02 products, records
   shapes/columns, checks structural invariants, and (atomically) writes the
   inventory table. Reused by the orchestrator and the notebook (src-promotion
   per §11.6).
2. `scripts/phase03_s01_data_inventory.py` — orchestrator; prints inventory +
   invariants + reliable-window summary, exits non-zero on any failure.
3. `tests/test_input_inventory.py` — 3 pure-logic + 4 data-backed tests
   (data-backed skip if the gitignored processed data is absent).
4. `src/viz/style.py` — project-wide matplotlib/seaborn style. Categorical =
   Okabe-Ito (colourblind-safe, fixed order, non-cycled); sequential = single-hue
   (cividis / YlGnBu / inferno); diverging = RdBu_r (neutral midpoint); stable
   entity→colour maps for zones / commodities / SILO variables; `SEED = 42`.
5. `notebooks/03_exploratory_analysis.ipynb` — EDA scaffold (16 cells): §0 setup +
   verified inventory (executable), §1–§5 stubs for s02–s06, running caveats list.
6. `outputs/tables/s01_input_inventory.csv` — committed inventory table.

**Verification (all green):**
- Inventory: 14 products present; row counts match (region_mapping 32; each of
  wheat/barley/canola raw + region_totals 1,114; SILO annual 5,400; SILO monthly
  2,160; cell-region map 28,577).
- Invariants: 32 mapped regions; 20 broadacre regions jointly present in the yield
  (region name) and climate (aagis_code) products; the 2 SILO-uncovered regions
  are exactly 511 (WA The Kimberley) / 711 (NT Alice Springs), both Pastoral;
  region names/codes subset the mapping.
- Reliable yield windows: non-NA yields wheat 747 / barley 738 / canola 482;
  canola carries 122 pre-1994 rows (28 with a non-NA yield) excluded by the RSE
  gate — carried forward to s03 (yield EDA) and s05 (optional-crop decision).
- `pytest -q`: 44 passed (37 Phase 02 + 7 new). `nbconvert --execute` runs the
  notebook end-to-end on the `.venv` (3.12) kernel with no error.

**First-use dependency rule (§11.7 / §8.2):** `matplotlib>=3.8` and `seaborn>=0.13`
added to `requirements.txt` in the same commit as `src/viz/style.py`.

**Environment note:** stray `cpython-310` `.pyc` files were observed under
`src/__pycache__`; confirmed the active interpreter for tests and the notebook is
the `.venv` (Python 3.12) — `nbconvert --execute` ran under `.venv`.

**Scope:** no revision; scope stays v5.1. Open Phase 03 decisions logged for their
steps: gate ① SILO re-aggregation window (s02); gate ② RSE weighting (s03,
possibly Phase 06); Task H historical-event sanity (s04); optional-crop decision
(s05).

**Impact:** Step 01 complete — a verified, cross-checked data baseline and an
executable EDA scaffold. Phase 03 s02 (regional climate climatology) is enabled.
