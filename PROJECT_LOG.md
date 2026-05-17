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

**Decision:** No generator script (avoiding accumulation of ephemeral scripts). Claude provides file content directly; Kota places via editor.

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
Claude's preliminary Phase 01 recommendations (point-centroid SILO sampling at AAGIS
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
raise the quality bar, not by discovery of new technical information. Claude's initial
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

**Honesty note on prior turn:** Claude's previous-turn hypothesis that
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
