# Project 5 — Project Scope (v5)

**Repo / project codename:** `agriculture-risk-monitoring-system`
**Formal title:** *Agriculture Risk Monitoring System: A Multi-Method Research Framework for Australian Broadacre Cropping*
**Short title:** P5 — Agriculture Risk Monitoring System
**Author:** Kota
**Last updated:** 2026-07-09
**Document status:** Post-Phase 01 empirical reconciliation. Replaces `p5_ProjectScope_v4.md` (v4, 2026-05-14).
**GitHub:** https://github.com/kota2003/agriculture-risk-monitoring-system

---

## 1. Identity and Purpose

### 1.1 One-sentence purpose

Build a research-grade analytical framework for monitoring agricultural risk in Australian broadacre regions, by quantifying how climate extremes translate into production risk using six methodologically distinct approaches (climate indicator engineering, extreme value theory, statistical climate–yield models, machine learning, spatio-temporal modelling, and multi-method synthesis) over an integrated dataset assembled from authoritative public sources.

The framework is the substantive deliverable; an interactive monitoring layer (dashboard) is an optional final-phase output that surfaces results from the framework.

### 1.2 Portfolio positioning

This is a **research-depth-first** portfolio project, scoped and executed to **Master-research-grade quality standards**. The intended evaluator set includes research-lab admissions committees, professors, and academically-literate hiring managers in addition to industry recruiters and engineers. Every methodological choice must be defensible under research peer review; engineering compromises that compromise methodological rigor are not acceptable, even when more convenient.

Its substantive contribution is a defensible, literature-grounded characterization of Australian climate–agriculture risk; its methodological contribution is a side-by-side comparison of how different families of methods quantify that risk, plus an explicit treatment of how spatial-unit choice (MAUP) affects conclusions.

**Framing evolution.** The project was initially scoped (v1) as an operational monitoring system built on a single commercial weather API and rule-based scoring. During Phase 00 scoping, the framing was refined (v2) to a research-depth-first multi-method investigation. v3 reconciled the two by treating the multi-method analytical framework as the core deliverable and positioning any monitoring/dashboard layer as a communication surface for it. v4 preserved that framing but recalibrated the methodological design to Master-research-grade standards: mixed-resolution spatial design, observed-vs-derived data discipline, and explicit MAUP robustness study. v5 (this document) reconciles the v4 design against empirical findings from Phase 01 data acquisition. The shift is recorded for honesty (no hidden pivots) and is itself a portfolio signal of scoping discipline.

It is intentionally complementary to Project 4 (panel econometrics on education and income inequality):

- **Project 4** signal: depth in causal-leaning panel methods within a single methodological family.
- **Project 5** signal: methodological breadth + integration, plus production-grade engineering of an end-to-end research framework that can power a monitoring layer, plus explicit handling of spatial-aggregation issues.

Together, the two projects span "depth in one method" and "breadth across methods," which is a stronger portfolio shape than two single-method projects.

### 1.3 Target audience

In approximate order of priority:

1. **Research-lab admissions committees and professors** evaluating the candidate for Master / research roles.
2. **Hiring managers** in data science / quantitative research roles (industry, agritech, climate analytics, public policy quantitative teams).
3. **Academic / research evaluators** considering the candidate for research-adjacent roles or further study.
4. **Domain readers** in climate impact, agricultural economics, or climate risk.
5. **Engineers** auditing reproducibility, code quality, and pipeline design.

### 1.4 Aspirational outcome

A successful execution of this scope produces a body of work consistent with a **working paper** suitable for a workshop submission or extended methodological note. This is an aspiration, not a success criterion (see §8).

---

## 2. Research Framing

### 2.1 Central research question

> *How do climate extremes translate into agricultural production risk across Australian broadacre regions, and how do different methodological families compare in their characterization of that risk?*

### 2.2 Sub-questions

1. **Indicator design.** Which literature-grounded climate extreme indicators (drought, heat, frost) — computed at SILO grid resolution before any region aggregation — most cleanly track yield variation in Australian broadacre regions?
2. **Extremity.** What are the regional return periods of key climate extremes, and is there evidence of non-stationarity (climate-change signal in distributional parameters)?
3. **Climate–yield linkage.** What is the statistical relationship between climate indicators and yield outcomes — both at the mean and in the lower tail (= "risk")?
4. **Methodological agreement and spatial-unit robustness.** Where do statistical, machine learning, and spatial–hierarchical methods agree in their risk characterizations, and where do they diverge? How robust are the conclusions to choice of spatial aggregation unit (the Modifiable Areal Unit Problem)?
5. **Validation.** How well does each method recover known historical drought / heatwave events as high-risk? How do the project's own modelled outcomes compare to the independent ABARES farmpredict outputs (AGFD)?
6. **Data validation (auxiliary).** How does a commercial weather API (OpenWeather) compare to the gold-standard scientific dataset (SILO) when used as the climate input layer, over the 2022–2024 sample window at the selected AAGIS region centroids?

### 2.3 Substantive contribution

A regional, multi-decadal characterization of climate-induced agricultural risk in Australian broadacre cropping, with explicit uncertainty quantification, honest reporting of where methods disagree, and explicit demonstration of how conclusions depend on the spatial-aggregation choices made.

### 2.4 Methodological contribution

A side-by-side application of six methodological families to a single integrated dataset, allowing direct comparison of how methodological choice shapes risk conclusions. This addresses a gap in the climate-impact literature where methods are typically applied in isolation. The mixed-resolution spatial design and explicit MAUP robustness study together address a second gap: most climate-impact studies select a single spatial unit and do not examine how their conclusions depend on that choice.

### 2.5 Explicit non-claims

This project does **not** claim:

- **Causal identification** in the strong econometric sense. Climate variation is plausibly exogenous to farmer decisions at relevant timescales, but the project will not invoke instrumental variables or natural experiments. Claims will be expressed as "associational with mechanistic plausibility."
- **Predictive operational use.** Any forecasting framing is exploratory and should not be interpreted as a deployable early-warning system.
- **Coverage of irrigated, horticultural, or pastoral systems.** The project is scoped to rainfed broadacre crops (see §3.2).
- **National-level aggregate results.** Findings are regional; aggregating to a single national risk score is explicitly out of scope.
- **Observational status for derived datasets.** ABARES Australian Gridded Farm Data (AGFD) is the output of the ABARES farmpredict simulation model, not observed yield data. AGFD is used in this project only as an *independent validation benchmark* for our own modelled outcomes (Phase 09), never as a training target or yield substitute. Using model outputs as ground truth for other models constitutes a circularity error and is explicitly avoided.
- **Region-total agricultural production from ABARES Farm Data Portal values.** As documented in §4.3, ABARES FDP `Value` columns are survey-weighted per-typical-farm averages, not region totals. Regional yield (t/ha) is dimensionally valid as a per-farm-representative regional average; regional area (ha) and production (t) require farm-count weighting for conversion to region totals (deferred to Phase 02).

---

## 3. Scope Boundaries

### 3.1 Geographic and spatial-unit framing

**Australia** is partitioned for the analysis using a **mixed-resolution spatial design** (see §3.6 for the full strategy):

- **Primary yield unit: AAGIS regions** (32 regions in the current shapefile, of which broadacre-relevant regions are the majority). The Australian Agricultural and Grazing Industries Survey (AAGIS), operated by ABARES, partitions Australia into a two-level hierarchy of **zones × regions**. Zones (Pastoral, Wheat-sheep, High-rainfall) are coarse climatic/agronomic divisions; regions (32) are the finest level of geographic aggregation at which ABARES publishes broadacre commodity statistics. AAGIS regions are the canonical unit for matching the ABARES yield data; the project uses them as the primary yield unit. Pastoral-zone regions are excluded from the cropping analysis since they are not broadacre-cropping environments.

  **Empirical finding from s01 (Phase 01):** the AAGIS shapefile identifies regions by 3-digit integer codes (e.g., `'121'`, `'322'`), while the ABARES Farm Data Portal (FDP) regional CSV identifies the same regions by text names (e.g., `'NSW Riverina'`, `'QLD Western Downs and Central Highlands'`). Both encode 32 regions structurally aligned. An explicit **code-to-name mapping table** is required before spatial joins between the shapefile and FDP CSV can proceed. This mapping is a Phase 02 deliverable (§11.6, `src/processing/region_aggregation.py`).

  The 3-digit code follows a hierarchical structure: 1st digit = state code (1=NSW, 2=VIC, 3=QLD, 4=SA, 5=WA, 6=TAS, 7=NT), 2nd digit = zone (Pastoral/Wheat-sheep/High Rainfall), 3rd digit = region within zone.

- **Primary climate unit: SILO grid cells** (0.05° / ~5 km). Climate indicators are computed at SILO native grid resolution before any region-level aggregation, to avoid the information loss inherent in pre-aggregating temperature and rainfall data.

- **Secondary unit (high-resolution disaggregation): ABS SA2** (~2,300 regions total; ~1,124 report agricultural activity in the 2020-21 Census). Used only where ABS Census data is the only available source.

- **Robustness unit: GRDC agro-ecological zones** (~21 zones). The project's primary Pillar 3 / Pillar 4 results will be re-computed at GRDC zone aggregation as a MAUP robustness study (§5.6).

State / territory aggregation will be reported descriptively only, not modeled at.

**Known data-quality caveat for AAGIS shapefiles**: the official AAGIS region mapping files contain geometry errors (self-intersecting polygons, invalid ring orientations). The `read.abares` R package documents these and auto-applies `sf::st_make_valid()` on import; the Python equivalent (`shapely.make_valid()` / `gdf.geometry = gdf.geometry.make_valid()`) is applied as a standard step in the AAGIS ingestion pipeline (Phase 01 s01) and is logged in PROJECT_LOG.

### 3.2 Crop coverage

**Broadacre rainfed crops**, in three layered tiers:

| Tier | Crops | Treatment |
|---|---|---|
| Primary | Wheat | All six pillars; deepest analysis |
| Secondary | Barley, Canola | Methodology generalization study |
| Optional / deferred | Sorghum (summer crop), Cotton (irrigated) | Decision in Phase 03 EDA based on data availability and homogeneity |

**Out of scope:** horticulture, sugarcane, rice, pastoral livestock, dairy, irrigated systems beyond the optional cotton consideration.

**Phase 01 empirical validation of the tier structure (s07):** ABS Census 2020-21 SA2 counts confirm the intended tier separation. Wheat is reported by 394 SA2 regions, barley by 367, and canola by 255 — validating that canola's geographic footprint is narrower and justifying its "secondary" tier assignment. The most concentrated wheat production region as of 2020-21 is the WA Central and Southern Wheat Belt, which anchors the Phase 09 comparison studies (§5.6.3).

### 3.3 Temporal

**Hybrid temporal design** (different windows for different uses):

| Use | Period | Justification |
|---|---|---|
| Climate climatology baseline | 1961–1990 (and 1991–2020 as alternative) | WMO standard reference periods; required for SPI/SPEI computation |
| EVT analyses (Pillar 2) | 1961–present for tmax/tmin/rainfall; 1970–present for evapotranspiration-derived indices | Long record needed for stable extreme-tail estimation. Evappan effective start = 1970 per SILO (s04 empirical finding). |
| Climate–yield modeling (Pillars 3–5) | **1990–present (35 years, updated from v4's 1980+)** | ABARES Farm Data Portal historical estimates start at financial year 1990. Attempting to use pre-1990 yield data would require an alternative source with structural break considerations; the 5-year adjustment from v4's 1980 baseline is a small concession that preserves data integrity. |
| OpenWeather cross-validation (Pillar 6 auxiliary) | **2022–2024 (3 years)** — 10 AAGIS region sample | Sample window sized for a defensible SILO–OpenWeather comparison study within cost-controlled OpenWeather One Call 3.0 usage (§4.5). |

The 1961 start is a hard floor for the climatological baseline: SILO gridded data is high-quality from 1961 onward but progressively sparser before that. The 1990 start for yield modeling is a Phase 01 empirical concession (see §4.3).

### 3.4 Frequency

| Layer | Frequency | Notes |
|---|---|---|
| Climate raw | Daily | SILO native |
| Climate indicators | Monthly / seasonal aggregations | As required by each indicator's literature definition; computed at grid resolution then aggregated |
| Yield / agricultural | Annual | ABARES / ABS Census native |
| Risk outputs | Annual, region-level | Match yield layer |

### 3.5 Out-of-scope items (explicit)

- Real-time / near-real-time monitoring (the auxiliary OpenWeather comparison touches this, but operational deployment is not a goal)
- Economic translation (yield risk → farm income / commodity price impact)
- Adaptation / policy recommendation
- Future climate projections (CMIP / regional climate models)
- Crop-model simulation (e.g., APSIM)

These are mentioned in "future work" sections of deliverables but not pursued.

### 3.6 Spatial Resolution Strategy

The project adopts a **mixed-resolution spatial design** rather than a single spatial unit. The choice is methodological, not merely convenient: each methodological pillar has a natural spatial scale, and forcing all pillars onto a single unit would either (a) destroy climate information by pre-aggregating to coarse yield units or (b) introduce structural artefacts by attempting to disaggregate yield data to fine climate units.

#### 3.6.1 Pillar-to-unit mapping

| Pillar | Primary spatial unit | Rationale |
|---|---|---|
| P1 — Climate indicator engineering | **SILO grid cell** (~5 km) | Indicators (SPI, SPEI, EHF, GDD, etc.) are functions of point climate; aggregation is a derived product, not a primary computation |
| P2 — Extreme Value Analysis | **SILO grid cell**, with **AAGIS region rollup** | Grid-level fitting yields many observation points per region, stabilising tail-parameter estimation; region-level return periods are derived by aggregating grid-level estimates |
| P3 — Climate–yield statistical models | **AAGIS region** | Yield data is published at AAGIS region; this is the natural unit and there is no methodologically sound way to disaggregate annual yield to grid cells |
| P4 — Machine learning models | **AAGIS region**, with grid-level climate aggregations as features | Yield unit is AAGIS region; grid-level climate enters as engineered features (means, quantiles, extremes within region) |
| P5 — Spatio-temporal / hierarchical modeling | **AAGIS region** primary; grid-derived neighbourhood structure | Hierarchical structure: region intercepts (yield), with grid-derived spatial weights for region adjacency / covariance |
| P6 — Multi-method synthesis | **AAGIS region**, plus **GRDC zone** robustness | Common unit for cross-method comparison; GRDC zone aggregation provides MAUP robustness check |

#### 3.6.2 MAUP awareness and robustness

The Modifiable Areal Unit Problem (MAUP) — the phenomenon that statistical results computed on aggregated spatial data depend on the choice of aggregation boundaries — is a known threat to spatial-econometric and climate-impact studies. The project addresses MAUP in two ways:

1. **Avoid premature aggregation.** Climate quantities are computed at SILO grid resolution before being aggregated to AAGIS region. This preserves all within-region heterogeneity in the indicator construction step.
2. **Explicit robustness check.** The primary Pillar 3 (statistical) and Pillar 4 (ML) results are re-computed using **GRDC agro-ecological zones** (~21 zones) as the aggregation unit, and the magnitude and direction of the difference is reported in Pillar 6 synthesis. Stability of conclusions across the AAGIS-region and GRDC-zone aggregations is itself a reportable finding.

This treatment is explicit precisely because most climate-impact studies pick one spatial unit and proceed without discussing the alternative. A Master-research-grade portfolio should make the unit choice visible and defended.

Additionally, Phase 01 s03 (cropping mask construction) applied three threshold values (0.05, 0.10, 0.20 fraction of grid cell classified as broadacre cropping) to test sensitivity of the mask to threshold choice. This is a related-but-smaller-scale MAUP-adjacent robustness check documented in PROJECT_LOG s03.

#### 3.6.3 Information loss accounting

Computing climate indicators at grid resolution and then aggregating to region is **not** information-loss-free — the aggregation step still discards within-region variance. But it loses strictly less information than the alternative (computing indicators on already-aggregated regional climate). The project will report, where relevant, the within-region distributional properties of indicators (e.g., region-level standard deviation of GDD across grid cells), not just the within-region means.

---

## 4. Data Sources

### 4.1 Primary climate data

**SILO** (Queensland Department of Agriculture and Fisheries)

- **Type:** Daily gridded (~5 km / 0.05°) interpolated weather data, Australia-wide.
- **Period:** 1889–present; project uses 1961–present for tmax/tmin/rainfall/vp/rad; **1970–present for evappan** (Phase 01 s04 empirical finding: SILO evappan variable is populated from 1970 onward, sparse or absent for 1961–1969).
- **Variables retrieved (Phase 01 s04):** maximum temperature, minimum temperature, daily rainfall, vapour pressure, solar radiation, pan evaporation.
- **Access:** SILO Long Paddock data drill; gridded data available via HTTPS direct download (per-year, per-variable NetCDF) from AWS S3 mirror (`s3-ap-southeast-2.amazonaws.com/silo-open-data/Official/annual/`).
- **Status:** widely used in peer-reviewed Australian climate research.
- **Volume acquired (Phase 01 s04):** 375 masked NetCDF files, 11.64 GB total on disk after cropping-mask subsetting.

**Ingestion strategy (grid-based with cropping mask).** SILO grid data is retrieved for the full broadacre cropping area only:

1. The ABARES ACLUMP land-use raster (§4.4) is reprojected and resampled to the SILO 0.05° grid.
2. A binary cropping-area mask is constructed: True for grid cells whose ACLUMP class is broadacre cropping (wheat, barley, canola, mixed cereals); False elsewhere.
3. SILO yearly NetCDF files are retrieved for the full continental extent, with post-hoc masking applied to persist only the cropping-relevant cells.
4. Persisted files in `data/processed/silo/` retain xarray-compatible NetCDF format with the cropping mask applied.

**Volume outcome (empirical).** Post-mask retention is ~11.64 GB across 6 variables × 65 years × masked grid cells, tractable for local disk and downstream processing.

### 4.2 Climate quality reference

**BoM ACORN-SAT** (Bureau of Meteorology)

- **Type:** Homogenised station-level long-term temperature record.
- **Nominal station count:** ~112 stations per ACORN-SAT master list.
- **Effective station count (Phase 01 s05):** **94 stations**, after 18 stations were found unavailable at the BoM hqsites endpoint. The 18 unavailable stations are documented in `src/ingestion/bom_acornsat.py::ACORN_SAT_UNAVAILABLE_STATIONS`; three of them are broadacre-cropping-region relevant (008039 WA Wheatbelt, 008051 WA Wheatbelt margin, 073054 NSW Riverina) and this reduced ACORN-SAT coverage is a Phase 02 quality-check consideration.
- **Files acquired:** 188 CSV files (94 stations × 2 variables: tmax and tmin).
- **Use:** Sanity-check SILO regional aggregates against ACORN-SAT station records to confirm SILO regional means are physically plausible.
- **Access:** BoM hqsites data portal, per-station-per-variable CSV endpoints.

### 4.3 Observed agricultural production data

This section deliberately uses the term **"observed"** to distinguish these sources from the **derived (model-output)** AGFD dataset described in §4.6. The distinction matters: observed yields are the only acceptable ground truth for yield modelling.

**ABARES Farm Data Portal (FDP), Historical Estimates** (Australian Bureau of Agricultural and Resource Economics and Sciences)

- **Type:** Three CSVs (regional, national, state) with different schemas:
  - `fdp-regional-historical.csv` (9.4 MB) — 150,480 rows, 32 AAGIS regions × 35 years × 136 variables
  - `fdp-national-historical.csv` (1.5 MB) — with `Industry` dimension (7 values including `'All Broadacre'`)
  - `fdp-state-historical.csv` (11.4 MB) — with `State` and `Industry` dimensions
- **Period:** **1990 to 2024 (35 financial years)**, revising v4's stated "1980+" downward to the actual FDP start year.
- **Variables:** annual area (ha), production (t), yield (t/ha) by AAGIS region for major crops, plus 130+ additional farm-management, financial, and demographic variables.
- **Critical empirical finding from Phase 01 s06 — per-typical-farm semantics:** ABARES FDP `Value` columns represent survey-weighted per-typical-farm averages, NOT region/national totals. Triangulation from national `'All Broadacre'` wheat = 656 t/farm (2022) × ~55,000 broadacre farms ≈ 36 Mt, matching ABS published national total (~36.6 Mt), confirms per-farm semantics.
  - **Implication for Pillars 3–5:** `yield_t_ha = production_t / area_ha` is dimensionally valid as a per-farm-representative regional yield. `production_t` and `area_ha` are per-typical-farm and require farm-count weighting for conversion to region totals. This is a Phase 02 processing task (§11.6, `src/processing/abares_aggregation.py`).
- **AgSurf farm survey indicators:** available as additional secondary variables within FDP (financial / operational).

**ABS Agricultural Census 2020-21** (Australian Bureau of Statistics)

- **Type:** Single-vintage cross-section, 5-yearly historically.
- **Structural discontinuity (Phase 01 s07 empirical finding):** The 2020-21 Agricultural Census was the **final ABS Agricultural Census**. Post-2020-21, ABS transitioned to a modernised agricultural statistics pipeline (Levy Payer Register + satellite crop mapping, released annually from 2022-23). Project 5 v1.0 freezes Census-derived weighting at the 2020-21 vintage; future extensions requiring SA2 spatial unit and post-2020-21 vintage should incorporate the modernised pipeline (out of scope for v1.0).
- **Spatial units acquired:** National + State + SA4 + SA3 + SA2 (via ASGS Edition 3), across a single `AGCDCASGS202021.xlsx` workbook (3.87 MB, ~3,700 rows in Table 1).
- **SA2 counts by commodity (Phase 01 s07):** 394 SA2 for wheat, 367 for barley, 255 for canola.
- **Use:** SA2-level cross-section snapshot for region-importance weighting (Pillar 4-5). Not used as time-series.

### 4.4 Land use mask (ACLUMP)

**ACLUMP** (Australian Collaborative Land Use and Management Program, ABARES)

- **Type:** Catchment-scale land use raster of Australia.
- **Vintage acquired (Phase 01 s02):** `clum_50m_2023_v2` (December 2023 vintage), 286 MB TIF + 151 MB ZIP + metadata PDF.
- **Native resolution:** 50 m; native CRS: EPSG:3577 (Australian Albers). Reprojected to SILO 0.05° grid at Phase 01 s03.
- **Cropping coverage (Phase 01 s02 empirical):** ALUM 3.3 Cropping class = 5.131% of non-NODATA pixels.
- **Use:** Constructing the broadacre cropping-area mask used to subset SILO grid retrieval (§4.1) and to define the spatial scope of Pillar 1–2 grid-level analyses.
- **Access:** ABARES data portal (direct ZIP / GeoTIFF download).
- **License:** Creative Commons (per ABARES standard data licensing).

### 4.5 Validation comparator (OpenWeather)

**OpenWeather One Call API 3.0** (Historical Weather, `/day_summary` endpoint)

- **Type:** Commercial API, historical observation + reanalysis blend, daily aggregation endpoint.
- **Purpose:** *Validation target.* Compare OpenWeather output against SILO at a sample of AAGIS region centroids over the 2022–2024 sample window (§3.3). The comparison is the methodological contribution: how does a globally-available commercial API compare to the local scientific gold standard?
- **Sample design (Phase 01 s08):** 10 AAGIS region centroids × 1,096 days (2022-01-01 to 2024-12-31) = 10,960 daily records.

  Selected regions and centroids (using `representative_point()` on the AAGIS shapefile geometry, guaranteed inside polygon):

  | AAGIS code | Region name | Zone | Lat | Lon |
  |---|---|---|---|---|
  | 121 | NSW North West Slopes and Plains | Wheat-Sheep | -30.4927 | +149.1082 |
  | 122 | NSW Central West | Wheat-Sheep | -32.4592 | +148.2871 |
  | 123 | NSW Riverina | Wheat-Sheep | -34.4014 | +146.5049 |
  | 221 | VIC Mallee | Wheat-Sheep | -35.1072 | +142.1623 |
  | 222 | VIC Wimmera | Wheat-Sheep | -36.4753 | +141.8499 |
  | 322 | QLD Western Downs and Central Highlands | Wheat-Sheep | -25.2380 | +149.0099 |
  | 421 | SA Eyre Peninsula | Wheat-Sheep | -33.3796 | +136.1039 |
  | 521 | WA Central and Southern Wheat Belt | Wheat-Sheep | -31.6075 | +117.1038 |
  | 522 | WA Northern and Eastern Wheat Belt | Wheat-Sheep | -30.3843 | +118.2580 |
  | 631 | TAS Tasmania | High Rainfall | -42.1424 | +146.6725 |

  Geographic + climate coverage: 6 states (NSW/VIC/QLD/SA/WA/TAS), 5 climate types (semi-arid, Mediterranean, subtropical, temperate, cool-temperate). Pastoral zone and NT excluded per §3.2 broadacre scope.

- **Actual data volume acquired (Phase 01 s08):** 10,960 / 10,960 daily records (100.0% coverage) persisted as 30 Parquet files (one per region-year) in `data/raw/openweather/`.
- **Access + subscription:** One Call API 3.0 pay-per-call. First 1,000 calls/day free; £0.0012 per additional call. Daily hard limit set to 11,000 in dashboard for cost containment.
- **Total cost (Phase 01 s08):** ~£11.40 (≈ AUD $22). API key stored in `.env` (gitignored) and loaded via `python-dotenv`.
- **Endpoint used:** `GET https://api.openweathermap.org/data/3.0/onecall/day_summary?lat={lat}&lon={lon}&date={YYYY-MM-DD}&units=metric&appid={key}`. Returns metric-unit daily aggregations (tmin, tmax, morning/afternoon/evening/night temps, total precip, humidity, pressure, cloud cover, max wind).

### 4.6 Independent validation benchmark (AGFD)

**Australian Gridded Farm Data (AGFD)** (ABARES)

- **Type:** 0.05° (~5 km) NetCDF gridded simulation outputs from ABARES farmpredict model. Includes simulated historical broadacre farm profitability, yields, and inputs for representative typical farms at each grid cell.
- **Critical caveat:** **AGFD is model output, not observed data.** It is the result of the ABARES farmpredict simulation conditioned on climate, prices, and representative farm characteristics — not actual observed farm outcomes.
- **Use in this project:** *Phase 09 only*, as an **independent validation benchmark**. The project's own statistical and ML models (Pillars 3, 4) produce yield predictions at AAGIS region level; AGFD provides an independent (different methodology, different model class) benchmark to compare against. Agreement strengthens both; disagreement is methodologically informative.
- **Explicit non-use:** AGFD is **never** used as a training target, never substituted for ABARES observed yields, and never input as a feature into Pillars 3–4 models. Using model outputs as ground truth for other models constitutes a circularity error.
- **Access:** ABARES Farm Data Portal, NetCDF download.
- **License:** Creative Commons (per ABARES standard data licensing).
- **Ingestion timing:** deferred to Phase 09 (not Phase 01) since usage is confined to the synthesis phase.

### 4.7 Licensing and attribution

All sources are public or accessible via free / inexpensive API tiers. License terms are:

- Recorded in `data/raw/manifest.yaml` per source (populated at Phase 01 s09 closure).
- Acknowledged in the README and `methodology.md`.
- Respected in distribution: data files themselves are gitignored except for the manifest and small derived summaries; the project distributes scripts to retrieve data, not the data itself (consistent with playbook §5 "reproduce-from-code" default).

ABARES-sourced data (AAGIS shapefile, ACLUMP, AGFD, FDP) is available under Creative Commons licensing; project follows the ABARES citation convention at https://www.agriculture.gov.au/abares/products/citations.

OpenWeather data is licensed for research use per OpenWeather's terms; attribution required in any derived publication.

### 4.8 Manifest plan

`data/raw/manifest.yaml` (populated at Phase 01 s09) documents, for each source:

- Canonical name, version / vintage, retrieval URL, retrieval date
- Field dictionary (variable names, units, encoding)
- License and attribution
- Known quirks (encoding issues, NA-handling requirements, geometry-error fixes, observed-vs-derived classification, per-typical-farm semantics for ABARES FDP)

---

## 5. Methodological Pillars

Each pillar is implementable as an independent contribution; together they form the multi-method synthesis.

### 5.1 Pillar 1 — Climate Indicator Engineering

Implement literature-grounded climate-extreme indicators rather than bespoke ad-hoc constructions.

**Resolution discipline:** all indicators are computed at SILO grid resolution before any region aggregation. Region-level indicator series are derived products obtained by aggregating grid-level indicators (typically by area-weighted mean or quantile, depending on indicator), not by computing indicators from already-aggregated regional climate. This preserves within-region heterogeneity in the indicator construction step.

| Indicator | Source | What it captures |
|---|---|---|
| **SPI** (Standardised Precipitation Index) | McKee et al. (1993); WMO | Precipitation-only drought |
| **SPEI** (Standardised Precipitation–Evapotranspiration Index) | Vicente-Serrano et al. (2010) | Drought accounting for evaporative demand (uses SILO evappan from 1970) |
| **EHF** (Excess Heat Factor) | Nairn & Fawcett (2015); BoM operational definition | Heatwave intensity |
| **GDD** (Growing Degree Days) | Standard agronomy | Heat accumulation for crop development |
| **Consecutive dry days** | Standard climate-extreme literature | Drought event duration |
| **Frost days** | Standard | Cold-side risk |

Outputs: grid-level indicator time series; region-level aggregated series persisted alongside (with within-region distributional summaries, not only means), validated against SILO/BoM published equivalents where available.

### 5.2 Pillar 2 — Extreme Value Analysis

Apply EVT to characterize the tails of climate-extreme distributions.

**Resolution discipline:** EVT is performed at SILO grid resolution where possible, with region-level return periods obtained as aggregations of grid-level estimates. Grid-level fitting maximises the per-region sample size for tail estimation (many grid cells × many years of block maxima per region), substantially improving stability of GEV/GPD parameter estimates compared to fitting from region-mean series alone.

- **GEV (Generalized Extreme Value)** distribution fitted to annual block maxima of relevant indicators (e.g., annual maximum heatwave intensity, annual maximum consecutive dry days) at each grid cell.
- **GPD (Generalized Pareto Distribution)** fitted to peaks-over-threshold at each grid cell; threshold selection by mean residual life plot and parameter stability.
- **Return level estimates** with confidence intervals (delta method / bootstrap), aggregated to region.
- **Non-stationary EVT**: location and / or scale parameters as functions of time, to test for distributional change. Reported with appropriate uncertainty given the difficulty of detecting tail-parameter trends.

This pillar exists because the project frames itself around *extremes*. Failing to apply EVT to a project on climate extremes would be a reviewer-visible gap.

### 5.3 Pillar 3 — Climate–Yield Statistical Models

Establish associational links between climate indicators and yields at AAGIS region level (the natural unit of the yield data).

**Per-farm semantics discipline (from s06 empirical finding):** ABARES FDP yield (t/ha) is used directly as the dependent variable, since per-farm yield ≈ regional-average yield under survey-weighted aggregation. Area and production variables, being per-typical-farm, are used only as covariates and never as region totals unless explicitly converted via farm-count weighting.

- **Panel regression** with region and year fixed effects (continuity with Project 4 methodology).
- **Quantile regression** at multiple quantiles (τ = 0.1, 0.25, 0.5, 0.75, 0.9). The risk-relevant findings live in the lower quantiles of yield, not the mean.
- **Lag and non-linear specifications**: piecewise / GAM where the climate–yield relationship is empirically non-linear (e.g., temperature thresholds).
- **Robustness**: clustered standard errors at the region level; specification curve where appropriate.

### 5.4 Pillar 4 — Machine Learning Models

Provide ML benchmarks and interpretability analyses, also at AAGIS region level.

- **Models**: Random Forest, XGBoost, LightGBM at minimum; consideration of quantile gradient boosting to match Pillar 3's quantile focus.
- **Features**: grid-level climate aggregations within each AAGIS region (means, quantiles, extremes — not just regional means) preserve within-region heterogeneity in the feature set.
- **Validation**: spatial blocked cross-validation (random K-fold leaks information across nearby regions); time-blocked cross-validation as an alternative.
- **Interpretability**: SHAP value analysis (continuity with Project 4); partial dependence plots.
- **Comparison**: ML vs. Pillar 3 statistical models — does ML find structure the statistical models miss, or does it merely overfit?

### 5.5 Pillar 5 — Spatio-Temporal / Hierarchical Modeling

Account for spatial and hierarchical structure that standard panel methods ignore.

- **Multilevel models**: region random effects (intercepts, possibly slopes), year random effects.
- **Spatial autocorrelation diagnostics**: Moran's I on residuals from Pillar 3 / 4 models.
- **Spatial smoothing** (if warranted): Gaussian-process regression or CAR/SAR models. Decision based on Phase 03 EDA evidence of spatial autocorrelation. Spatial weights derived from grid-level adjacency / distance where applicable, not from AAGIS region centroids alone.

### 5.6 Pillar 6 — Multi-Method Synthesis

Cross-method comparison, with dedicated robustness and validation sub-studies.

#### 5.6.1 Method-agreement analysis

- **Risk maps** from each method, presented side-by-side for the same region-year cells.
- **Method-agreement analysis**: where do methods agree on high-risk classifications, and where do they diverge? Is divergence systematic (e.g., particular regions, particular years)?
- **Historical event recovery**: do the methods successfully identify historically known high-risk events (e.g., the Millennium Drought 2001–2009, 2018 drought)?

#### 5.6.2 MAUP robustness study

Pillar 3 (statistical) and Pillar 4 (ML) primary results are **re-computed using GRDC agro-ecological zones** (~21 zones) as the aggregation unit. Reported:

- Magnitude of coefficient / feature-importance change between AAGIS-region and GRDC-zone aggregations.
- Direction of change (do the signs of effects flip?).
- Stability of headline findings (e.g., if a heat-stress effect on wheat is reported at AAGIS-region resolution, does it survive GRDC-zone re-aggregation?).
- Discussion: where the result is robust, this strengthens the claim; where it is not robust, this is itself a key finding and the dependence on unit choice is reported honestly.

This is the explicit MAUP-handling commitment promised in §3.6.2.

#### 5.6.3 Independent validation against AGFD

For Phase 09 only, the project's own statistical and ML yield predictions are compared against the **ABARES Australian Gridded Farm Data (AGFD)** simulated yields (§4.6). Side-by-side maps and quantitative agreement metrics. Agreement strengthens both; disagreement is methodologically informative and reported as such.

#### 5.6.4 Auxiliary: OpenWeather vs SILO comparison results

Presented as a methodological side-finding from Phase 02 (data quality study) using the 10-region-centroid × 2022–2024 sample acquired in Phase 01 s08. Reported metrics: RMSE, bias, correlation of daily tmax/tmin/rainfall/humidity at each centroid.

---

## 6. Phase Plan

11 phases, numbered `phase00` through `phase10`. Each phase has a goal, deliverables, and an exit criterion. Phase numbering is fixed; phase ordering is sequential except where noted.

### 6.1 Summary table

| # | Title | Pillar | Goal |
|---|---|---|---|
| 00 | Scope & Setup | — | Lock design and environment |
| 01 | Data Acquisition (8 sources) | — | Reproducible ingestion of climate, agriculture, and mask data |
| 02 | Data Quality & Cross-Validation | (P1, P6 aux.) | Verify integrity; region code-to-name mapping; OpenWeather–SILO comparison; grid-to-region aggregation consistency |
| 03 | Exploratory Analysis | — | Spatial-temporal patterns of climate and yields |
| 04 | Climate Indicator Engineering (grid-level) | P1 | Compute literature-grounded indicators at SILO grid resolution |
| 05 | Extreme Value Analysis (grid-level fit, region rollup) | P2 | EVT on climate indicators; return periods |
| 06 | Climate–Yield Statistical Models | P3 | Panel + quantile regression linkage |
| 07 | Machine Learning Models | P4 | ML benchmarks + SHAP |
| 08 | Spatio-Temporal Modeling | P5 | Hierarchical / spatial structure |
| 09 | Multi-Method Synthesis & Validation | P6 | Cross-method comparison; MAUP robustness; AGFD validation |
| 10 | Communication Layer | — | README polish, findings.md, methodology.md, optional dashboard |

### 6.2 Phase detail

#### Phase 00 — Scope & Setup ✓ (completed 2026-05-12)

- Deliverables: scope v3 → v4 → v5; environment (Python 3.12, pip + venv); `.pre-commit-config.yaml`; initial `src/` utilities; PROJECT_LOG.md initialised.
- Tag: `v0.0-phase00-complete`.

#### Phase 01 — Data Acquisition ✓ (completed 2026-07-09)

- Deliverables:
  - Per-source ingestion modules in `src/ingestion/`: `aagis_regions.py`, `aclump.py`, `silo.py`, `bom_acornsat.py`, `abares.py`, `abs_census.py`, `openweather.py` (7 modules, plus `agfd.py` deferred to Phase 09).
  - `src/processing/cropping_mask.py`, `src/processing/aagis_centroids.py`.
  - Populated `data/raw/` and `data/processed/`; `data/raw/manifest.yaml` fully documented.
  - 8 orchestration scripts in `scripts/phase01_s01_*.py` through `phase01_s08_*.py`.
  - Phase 01 summary in `docs/phase_summaries/phase01_summary.md`.
- Actual volumes acquired: SILO 11.64 GB / 375 files, ACLUMP 437 MB, BoM ACORN-SAT 188 files, ABARES FDP 22 MB / 3 CSVs, ABS Census 3.87 MB XLSX, OpenWeather 800 KB / 30 Parquet files (10,960 records). Total ~12 GB acquired.
- Tag (planned at s09 closure): `v0.1-phase01-complete`.

#### Phase 02 — Data Quality & Cross-Validation

- **Goal:** Quantify and document data integrity issues; construct AAGIS code-to-name mapping; complete OpenWeather vs. SILO comparison study; verify grid-to-region aggregation consistency; address ABARES per-typical-farm semantics.
- **Deliverables:**
  - **`src/processing/region_aggregation.py`** — AAGIS 3-digit code ↔ FDP text name mapping table (from Phase 01 s01/s06 empirical findings §3.1).
  - **`src/processing/abares_aggregation.py`** — Farm-count weighting for converting per-typical-farm values to region totals where required (from Phase 01 s06 empirical finding §4.3).
  - Data quality report.
  - OpenWeather–SILO agreement metrics using the 10-region-centroid × 2022–2024 sample (RMSE, bias, correlation).
  - **Grid-vs-region aggregate consistency check**: confirm that area-weighted means of grid-level SILO match expected regional climatologies.
  - ACORN-SAT coverage assessment: report the impact of the 18 unavailable stations (Phase 01 s05) on regional temperature validation.
  - Cross-validation notebook.
- **Exit criterion:** Region code-name mapping table validated (matches all 32 AAGIS regions to their FDP name); OpenWeather–SILO comparison written up; grid-aggregation consistency confirmed; per-typical-farm ↔ region-total conversion pipeline tested.

#### Phase 03 — Exploratory Analysis

- **Goal:** Establish baseline empirical understanding of climate and yield variation.
- **Deliverables:** EDA notebook; key visualizations (regional climate climatologies, yield trends and dispersions); decision on optional crops (Sorghum / Cotton).
- **Exit criterion:** Clear narrative of where, when, and how much climate and yield variation occurs.

#### Phase 04 — Climate Indicator Engineering

- **Goal:** Implement and validate literature-grounded climate extreme indicators at SILO grid resolution.
- **Deliverables:** `src/indicators/drought.py`, `heat.py`, `frost.py`; grid-level indicator time series in `data/processed/`; region-aggregated series with within-region distributional summaries; indicator notebook with validation against published equivalents where possible.
- **Exit criterion:** SPI, SPEI (using evappan from 1970), EHF, GDD, consecutive dry days, frost days computed at grid resolution, validated, persisted, and aggregated to AAGIS region.

#### Phase 05 — Extreme Value Analysis

- **Goal:** Apply EVT to climate extremes at grid level, aggregate return periods to region, test stationarity.
- **Deliverables:** GEV / POT models per grid cell × indicator; region-aggregated return level maps; non-stationary EVT extension; diagnostic plots.
- **Exit criterion:** Return periods estimated with appropriate diagnostics; grid-level fitting yields stable per-region tail estimates; non-stationary results reported with honest uncertainty.

#### Phase 06 — Climate–Yield Statistical Models

- **Goal:** Establish associational climate–yield links via panel and quantile methods at AAGIS region level. Uses 1990–present yield data per §3.3.
- **Deliverables:** Panel regression results; quantile regression at multiple τ; non-linear / lag specifications; robustness suite.
- **Exit criterion:** Findings reportable with clustered SEs and appropriate caveats.

#### Phase 07 — Machine Learning Models

- **Goal:** ML benchmarks and interpretability analysis at AAGIS region level.
- **Deliverables:** Trained models (or training scripts producing them — track-vs-reproduce decision per playbook §7); SHAP analysis; performance comparison vs. Phase 06.
- **Exit criterion:** ML results validated under spatial / time-blocked CV; interpretability narrative aligns with statistical findings or divergence is explained.

#### Phase 08 — Spatio-Temporal Modeling

- **Goal:** Account for spatial autocorrelation and hierarchical structure.
- **Deliverables:** Multilevel model fits; Moran's I diagnostics; spatial residual analysis; comparison to non-spatial baselines.
- **Exit criterion:** Spatial structure properly accounted for; residuals show no remaining systematic spatial pattern (or remaining pattern explicitly flagged).

#### Phase 09 — Multi-Method Synthesis & Validation

- **Goal:** Compare risk quantifications across pillars 1–5; perform MAUP robustness study; perform AGFD independent validation; validate against historical events.
- **Deliverables:**
  - Synthesis notebook.
  - Multi-method risk maps.
  - Method-agreement analysis.
  - **MAUP robustness section**: Pillar 3 / 4 results re-computed at GRDC agro-ecological zone aggregation; comparison report.
  - **AGFD validation section**: project's yield predictions vs ABARES AGFD farmpredict outputs; side-by-side maps and agreement metrics; methodological discussion of agreement vs disagreement.
  - Historical-event validation report.
  - AGFD ingestion script `src/ingestion/agfd.py` (added in this phase, not Phase 01).
- **Exit criterion:** Cross-method agreement quantified; MAUP robustness reported honestly (whether or not findings change under re-aggregation); AGFD comparison completed; major historical drought / heatwave events recovered as high-risk by majority of methods, or non-recovery explained.

#### Phase 10 — Communication Layer

- **Goal:** Portfolio-facing deliverables.
- **Deliverables:** Polished README; `docs/findings.md`; complete `docs/methodology.md` (skeleton created at Phase 01 s09); PROJECT_LOG closing entry; v1.0 git tag; (optional) React dashboard.
- **Exit criterion:** v1.0 tag pushed to GitHub; repo passes the post-publication checks in `portfolio_finalisation_playbook.md` §14.

### 6.3 Sequencing notes

- Phases 04 and 03 can be run in either order; default is 03 before 04.
- Phases 05, 06, 07, 08 are partially independent and can be interleaved if memory pressure on a single chat necessitates splitting.
- Phase 09 hard-depends on at least Phases 04, 06, and one of {07, 08} being complete.
- Phase 10 is final and runs only after Phase 09.

### 6.4 Rough time estimate

Indicative only. The user has stated time horizon is open; quality-gating (per PROJECT_WORKFLOW §11) takes precedence over schedule.

| Phase block | Indicative weeks | Actual (if completed) |
|---|---|---|
| 00 (foundation) | 1–2 | ~2 days across 2026-05-11 → 2026-05-12 |
| 01 (data acquisition) | 2–4 | ~2 calendar-months elapsed (2026-05-14 → 2026-07-09), ~10 effective working days |
| 02 (quality) | 2–3 | |
| 03 (EDA) | 1–2 | |
| 04 (indicators) | 2–3 | |
| 05 (EVT) | 2–4 | |
| 06 (Statistical) | 3–5 | |
| 07 (ML) | 2–4 | |
| 08 (Spatio-temporal) | 2–4 | |
| 09 (synthesis + MAUP + AGFD) | 3–5 | |
| 10 (closure) | 1–2 | |
| **Total remaining** | **~18–32 weeks** | |

Phase 01 elapsed calendar time is longer than budgeted primarily due to a 52-day pause between s08 initial run and s08 resume (June travel/break). Effective working time within Phase 01 was ~10 days, consistent with the original 2–4 week estimate.

---

## 7. Deliverables

### 7.1 Public (committed and pushed)

- `README.md` — recruiter entry point; structurally similar to Project 4 but stylistically project-specific
- `docs/project_scope.md` — this document (v5 as of 2026-07-09)
- `docs/findings.md` — substantive findings narrative (created at Phase 10)
- `docs/methodology.md` — methods and conventions reference (skeleton at Phase 01 s09, expanded through Phase 10)
- `PROJECT_LOG.md` — append-only decision log
- `requirements.txt`, `requirements-dev.txt` — pinned dependencies (Level 3 per playbook §8, at v1.0)
- `pyproject.toml` — tool configuration (black + ruff)
- `.gitignore`, `.python-version`, `.pre-commit-config.yaml`, `.env.example`, `LICENSE` (MIT)
- `notebooks/0X_*.ipynb` — phase-aligned notebooks, executed end-to-end
- `src/*.py` — reusable modules
- `scripts/phaseXX_sYY_*.py` — analytical step scripts (not log-only orchestrators)
- `outputs/figures/*.png`, `outputs/tables/*.csv` — referenced from notebooks and README
- `data/raw/manifest.yaml` — small, documents data sources

### 7.2 Internal (gitignored)

- `data/raw/*` (except manifest), `data/processed/*` — large, regeneratable
- `outputs/models/*.joblib` and similar — large, regeneratable from training scripts (playbook §7 default)
- `docs/phase_summaries/phaseXX_summary.md` — internal handoff artefacts
- `.env` — API keys and secrets
- `__pycache__/`, `.ipynb_checkpoints/`, `.venv/`, `.vscode/`, `.idea/`, `*.DS_Store`
- Scratch files: `*_dump.*`, `scratch_*`, `temp_*`, `wip_*`

### 7.3 Optional (decide late)

- React dashboard for interactive exploration of risk maps. Decision deferred to Phase 10 based on whether static figures + findings.md adequately communicate findings.

---

## 8. Success Criteria

### 8.1 Substantive

- Clear answers (with appropriate uncertainty) to all sub-questions in §2.2.
- Headline finding statable in 2–3 sentences with specific numerical anchors.
- Honest reporting of where methods disagree and where data limitations bound the conclusions.

### 8.2 Methodological

- All six pillars executed to a level a domain-knowledgeable reviewer would accept (correct method choice, correct diagnostics, correct caveats).
- Multi-method synthesis is a real synthesis, not a simple averaging — i.e., it explicitly handles disagreement.
- **MAUP robustness study completed** (Pillar 3 + Pillar 4 re-computed at GRDC zone aggregation), with honest report of how conclusions change (or don't).
- **AGFD independent validation reported** (Phase 09), with explicit observed-vs-derived discipline maintained throughout.
- **Mixed-resolution discipline maintained**: climate indicators computed at grid resolution before any region aggregation; observed yields never replaced by AGFD model output.
- OpenWeather–SILO comparison study completed and published (Phase 02), using the 10-region-centroid × 2022–2024 sample acquired in Phase 01 s08.

### 8.3 Engineering

- Fresh-clone reproducibility: a recruiter / engineer can clone the repo, install pinned dependencies, and reproduce every figure and table in the deliverables.
- All raw data is retrievable from public APIs / portals via documented scripts (no manual downloads required for the reader — with the caveat that OpenWeather requires a paid One Call 3.0 subscription and API key).
- Clean repo: no scratch files, no backup duplicates, no log-only orchestrators left behind.
- Per-phase commit history preserved via `--no-ff` merges.
- v1.0 annotated tag at project closure (v0.1-phase01-complete anchors Phase 01).

### 8.4 Portfolio

- README satisfies recruiter 5-minute scan and engineer 30-minute audit (playbook §1 finalisation test).
- `findings.md` and `methodology.md` exist and are publication-quality.
- Repo description, topics, and About section configured on GitHub.

---

## 9. Tech Stack

### 9.1 Environment management

**pip + venv** (CPU-only stack). conda is intentionally not used in this project.

- **Python 3.12** (locked at project start to match Project 4's runtime — preserving portfolio-wide Python-version consistency — and to avoid the Project 4 lesson 5 interpreter-mismatch issue). On Windows, the project uses `py -3.12` rather than the bare `python` command to guarantee version selection.
- **venv** placed at repository root as `.venv/`.
- **pip** with manually composed `requirements.txt` (and `requirements-dev.txt` for development-only tools).

**Rationale.** The project does not require GPU compute. Pillars 1–3, 5, 6 are CPU-bound by design. Pillar 4 (XGBoost, LightGBM, RandomForest) runs on CPU within minutes given the AAGIS region × 1990+ sample size. Choosing pip+venv over conda yields a simpler, more transparent, and more recruiter-reproducible environment, at the deliberate cost of foregoing GPU acceleration for Pillar 4 and any Bayesian Pillar 5 extensions.

### 9.2 Runtime dependencies (from Phase 00 + Phase 01 first-use additions)

Grouped by purpose in `requirements.txt`:

- **Core data:** pandas>=2.2, numpy>=1.26
- **Configuration / metadata:** pyyaml>=6.0
- **HTTP / API ingestion:** requests>=2.31
- **Spatial / raster (Phase 01 s01–s04 + reused Phase 04+ Phase 09):** xarray>=2024.1, netCDF4>=1.6, rasterio>=1.3, geopandas>=1.0, shapely>=2.0, pyproj>=3.6
- **Progress / UX:** tqdm>=4.66
- **Excel reading (Phase 01 s07):** openpyxl>=3.1
- **Environment variables (Phase 01 s08):** python-dotenv>=1.0
- **Parquet I/O (Phase 01 s08, reused Phase 04+):** pyarrow>=15
- **Notebook tooling:** jupyter, ipykernel, nbformat, nbconvert

Additional libraries added phase-by-phase per §11.7:

- Phase 03 EDA: matplotlib, seaborn
- Phase 04 indicators: scipy
- Phase 05 EVT: pyextremes
- Phase 06 statistical: statsmodels, linearmodels
- Phase 07 ML: scikit-learn, xgboost, lightgbm, shap
- Phase 08 spatial extra: libpysal, contextily
- Phase 09 synthesis: (no new deps; AGFD via xarray/netCDF4 already installed)

### 9.3 Code quality (dev-only)

Maintained in `requirements-dev.txt`:

- **black** — auto-formatting, line-length 88
- **ruff** — linting
- **pre-commit** — git hook orchestration

`pyproject.toml` configures both:
- `[tool.black]` line-length 88, target-version py312.
- `[tool.ruff]` line-length 88, target-version py312.
- `[tool.ruff.lint.per-file-ignores]` suppresses E402 for `scripts/phase*.py` (deliberate sys.path injection pattern for `from src.*` imports).

### 9.4 Editor integration

- `.vscode/settings.json` committed to the repository, pinning `python.defaultInterpreterPath` to `.venv/`.

### 9.5 Reproducibility level

**Level 3 (pinned)** per playbook §8, at project closure (Phase 10). During Phase 01–09, `>=` constraints are used.

`requirements.txt` is **manually composed** from actual project imports, **not generated by `pip freeze`**, to avoid Project 4 lesson 1.

---

## 10. Reproducibility Strategy

### 10.1 Random seeds

- A project-wide seed (`SEED = 42` by convention) is set in every script involving stochasticity.
- ML training uses `random_state=42`; bootstrap procedures use the same seed; cross-validation splits are deterministic.

### 10.2 Manifests

- `data/raw/manifest.yaml` records every data source with retrieval URL, version, retrieval date, and per-file metadata (fully populated at Phase 01 s09).
- New data sources require a manifest update before Phase 01 considers ingestion complete.

### 10.3 Pinned dependencies

- Per §9.5.

### 10.4 Environment reproduction

- `py -3.12 -m venv .venv` (Windows) or `python3.12 -m venv .venv` (macOS/Linux), followed by `pip install -r requirements.txt`, reproduces the runtime environment.
- `requirements-dev.txt` installs dev-only tools.
- `.python-version` records the exact Python minor version for pyenv-like tools.
- `.env.example` documents required environment variables (currently: `OPENWEATHER_API_KEY`).

### 10.5 Determinism boundaries

The project is CPU-only by design (§9.1), avoiding GPU non-determinism. Remaining concerns:

- Multi-threaded BLAS / OpenMP execution order for some scikit-learn / XGBoost / LightGBM kernels.
- Floating-point summation order in groupby aggregations across pandas versions.
- OpenWeather API returns are deterministic per (lat, lon, date), so re-runs produce identical results modulo API availability.

### 10.6 Encoding and pandas-NA defaults

Per Project 4 lessons:

- All `pd.read_csv` calls use `keep_default_na=False` and explicit `na_values` for country / region / short categorical columns.
- Encoding-fallback CSV reader (`utf-8` → `cp1252` → `latin-1`) implemented in `src/io_utils.py`.
- ABS Census (s07) additionally handles ABS-specific NA strings: `..`, `np`, `-`, `nil`.

### 10.7 Session persistence

- Data is persisted as: NetCDF (SILO, cropping mask), GeoPackage (AAGIS repaired), CSV (BoM, ABARES, ABS), Parquet (OpenWeather).
- All persistence uses atomic write-and-rename (`.part` → final path) to prevent partial-file corruption on interruption.
- Every ingestion module is idempotent: re-running skips already-completed items (per-file, per-record, or per-year depending on source).

---

## 11. Project Conventions

### 11.1 Workflow reference

This project follows `PROJECT_WORKFLOW.md` for process conventions (phase structure, step execution, naming, notebook expectations, documentation maintenance, git workflow, Knowledge management). The Workflow is authoritative for process; this Scope is authoritative for project-specific decisions. Conflicts resolve in favour of the Workflow on process and this Scope on substance.

### 11.2 Naming

- Step scripts: `phaseXX_sYY_<verb_object>.py` (zero-padded)
- Notebooks: `0X_<descriptive_title>.ipynb` (zero-padded)
- Phase summaries: `phaseXX_summary.md`
- Figures: descriptive filenames (`yield_distribution_by_region.png`), never `fig1.png`

### 11.3 Bilingualism

Per PROJECT_WORKFLOW §11.3:

- **Code / file names / comments / commit messages**: English
- **README, findings.md, methodology.md, project_scope.md, PROJECT_LOG.md**: English
- **Conversation between user and Claude**: Japanese by default
- **Bilingual deliverables (portfolio-facing summaries for LinkedIn / resume)**: EN + JP versions where helpful

### 11.4 PROJECT_LOG.md discipline

- Append-only.
- Mid-file edits performed via one-off Python script (PROJECT_WORKFLOW §8.2), never by hand.
- Entry on every material design decision (data source change, method choice, override, empirical finding, etc.).
- Sensitive credentials (API keys) never logged in cleartext; masked format only (e.g., `061dc7…9e58`).

### 11.5 Adaptive override convention

Per Project 4 precedent: when a step plan must change mid-execution, the override is logged as a discrete PROJECT_LOG entry referencing the original plan and the rationale for change. This is an explicit honesty signal in the audit trail, not a deviation to hide.

Examples from Phase 01:
- s04 SILO evappan variable found to be effectively populated only from 1970 (not the 1961 baseline for other variables) — logged as empirical finding in PROJECT_LOG s04 entry.
- s06 ABARES per-typical-farm semantics discovered via triangulation — logged with numeric verification in PROJECT_LOG s06 entry.
- s08 HTTP 504 permanent skip during 2026-05-18 initial run, subsequently auto-recovered during 2026-07-09 resume — logged in PROJECT_LOG s08 entry.

### 11.6 `src/` promotion rule

Per PROJECT_WORKFLOW §6.2: a function moves from `scripts/` to `src/` when it is called more than once or is non-trivial and likely reusable. Reviewed at each phase boundary.

Phase 02 promotion candidates identified in Phase 01:
- **`src/processing/region_aggregation.py`** — AAGIS 3-digit code ↔ FDP text name mapping (from s01/s06 findings).
- **`src/processing/abares_aggregation.py`** — Per-typical-farm ↔ region-total farm-count weighting (from s06 finding).

### 11.7 Code quality tooling

- **black** for auto-formatting (line length 88), enforced on every commit.
- **ruff** for linting; default rule set (E, F).
- **pre-commit** orchestrates both via `.pre-commit-config.yaml`.
- **`pyproject.toml`** centralises tool configuration and per-file-ignore (E402 suppression for `scripts/phase*.py` sys.path injection pattern).
- Dev-only tools in `requirements-dev.txt`.

**First-use rule (§9.2):** new runtime library additions to `requirements.txt` are staged in the same commit as the code that introduces them. Phase 01 additions: `openpyxl` (s07), `python-dotenv` (s08), `pyarrow` (s08).

### 11.8 Editor configuration

- `.vscode/settings.json` committed, pins interpreter to `.venv/`.

### 11.9 Notebook discipline

- Phase notebooks execute top-to-bottom on a fresh kernel without error.
- Every figure has an interpretation sentence beneath it.
- Conclusion section honest about limitations.
- No leftover debug prints or commented-out code.

### 11.10 Knowledge management (Claude side)

At each phase boundary, recommend Knowledge updates to the user. Aim for ~5 files:

1. `PROJECT_WORKFLOW.md`
2. `portfolio_finalisation_playbook.md`
3. `project_scope.md` (this file, v5)
4. The most recent phase summary (rolling)
5. Latest `findings.md` and `methodology.md` skeleton once they exist

### 11.11 Secrets management

- API keys and other credentials live only in `.env` (gitignored).
- `.env.example` provides a template (tracked) documenting required variables.
- `python-dotenv` loads `.env` in scripts that need credentials.
- API keys are never printed in cleartext to logs; only masked format.

---

## 12. Risks and Limitations

### 12.1 Methodological

- **MAUP exposure.** Different spatial aggregation choices can produce different statistical conclusions. *Mitigation:* mixed-resolution design (§3.6); explicit GRDC-zone robustness study in Pillar 6 (§5.6.2).
- **AAGIS region climate-boundary non-alignment.** AAGIS regions are drawn for agricultural-statistics sampling purposes, not by climate criteria. Within-region climate heterogeneity is therefore expected. *Mitigation:* grid-level indicator computation preserves within-region heterogeneity; within-region distributional summaries reported.
- **Quantile regression at extreme quantiles** (τ = 0.05, 0.95) is unstable with small samples. Use τ ∈ [0.1, 0.9] as defaults; report tail estimates as exploratory.
- **Non-stationary EVT** trend detection has notoriously low statistical power. Report effect sizes alongside hypothesis tests.
- **Spatial models** require a defensible spatial weights matrix; multiple weight specifications will be tested.
- **ML overfitting risk** to weather × region interactions. Spatial blocked CV is the primary defense.

### 12.2 Data

- **Observed-vs-derived data discipline.** AGFD is model output, not observation. Using it as a training target is explicitly forbidden (§4.6, §2.5).
- **ABARES FDP per-typical-farm semantics.** Region totals cannot be inferred without farm-count weighting; regional yield (t/ha) remains valid (§4.3, §5.3).
- **ABS Census 2020-21 is the final Census.** Post-2020-21 ABS agricultural statistics use a modernised pipeline (Levy Payer Register + satellite crop mapping) which is not incorporated in v1.0 (§4.3, §13).
- **ACORN-SAT 18 stations unavailable.** Reduces the reference-station network relevant to Phase 02 quality checks; three stations of broadacre-relevance are affected (§4.2).
- **AAGIS region code ↔ name mismatch** between shapefile and FDP CSV. Requires explicit mapping table (Phase 02 §11.6).
- **OpenWeather sample window (2022–2024)** limits statistical power of the SILO comparison to a 3-year seasonal cycle. Sample is nonetheless sufficient for the auxiliary methodological finding claimed in §5.6.4.
- **SILO interpolation quality** degrades in station-sparse regions. The project's restriction to broadacre cropping mitigates this since cropping zones have denser station coverage.
- **SILO evappan variable** effectively populated from 1970 onward. SPEI (which uses evappan) is therefore restricted to 1970+ (§3.3, §5.1).
- **Pre-1990 yield data non-comparability** restricts yield-linkage analysis to 1990+ (§3.3, §4.3).
- **AAGIS shapefile geometry errors** are known and repaired via `shapely.make_valid()` at ingest time (§3.1).

### 12.3 Engineering

- **SILO data volume**. Post-mask ~11.64 GB. Tractable for local disk.
- **Compute limits** for hierarchical Bayesian models. Mitigation: start with frequentist multilevel models; escalate to Bayesian only if needed.
- **Memory / chat handoffs**. Mitigation: PROJECT_WORKFLOW phase summary protocol.
- **OpenWeather API cost containment**. Daily hard limit set to 11,000 in dashboard; script enforces a soft daily quota. Phase 01 actual cost ~£11.40 (well within budget).

### 12.4 Scope

- **Crop coverage scope drift**. Adding sorghum / cotton mid-project is methodologically expensive (irrigation regime differs). Defer to Phase 03 decision (§3.2).
- **Dashboard scope drift**. Decision deferred (§7.3). Resist mid-project React build-out unless directly serves communicating findings.

---

## 13. Flexibility Clause

This Scope reflects current best understanding as of 2026-07-09. It is expected — and welcome — that some elements will need revision as the project encounters reality:

- **Substantive findings may redirect emphasis.** If Phase 03 EDA reveals that a particular crop or region exhibits the cleanest signal, downstream phases may concentrate there.
- **Methodological choices may change.** If Phase 06 finds that quantile regression is unstable at the available sample sizes, alternative tail-modeling approaches will be considered.
- **Phases may split or merge.** If a phase grows too large for one chat, it is split per PROJECT_WORKFLOW §9.3.
- **Optional pillars / crops / deliverables** (Pillar 5 spatial, optional crops, dashboard) are explicitly subject to deferral or omission with logged rationale.
- **Post-Census statistics.** Future extensions requiring post-2020-21 agricultural statistics at SA2 spatial unit should incorporate the ABS modernised pipeline (Levy Payer Register + satellite crop mapping). Not in v1.0 scope.

What is **not** flexible:

- The research framing (multi-method climate–agriculture risk in Australian broadacre).
- The mixed-resolution spatial design philosophy (§3.6) and observed-vs-derived data discipline (§4.6).
- The reproducibility and engineering standards.
- The honesty conventions (no hidden overrides, explicit non-claims, calibrated uncertainty).

Revisions to this Scope are versioned (`p5_ProjectScope_v6.md`, etc.) with a PROJECT_LOG entry summarizing the change.

---

## Appendix A — Repo Structure (post-Phase 01)

```
agriculture-risk-monitoring-system/
│
├── README.md
├── PROJECT_LOG.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .python-version
├── .gitignore
├── .pre-commit-config.yaml
├── .env.example        # template; .env is gitignored
├── LICENSE
│
├── .vscode/
│   └── settings.json
│
├── data/
│   ├── raw/
│   │   ├── manifest.yaml
│   │   ├── aagis_regions/       # gitignored contents; shapefile
│   │   ├── aclump/              # gitignored; land-use raster
│   │   ├── silo/                # gitignored; ~11.64 GB NetCDF
│   │   ├── acorn_sat/           # gitignored; 188 CSVs
│   │   ├── abares/              # gitignored; 3 FDP CSVs
│   │   ├── abs_census/          # gitignored; AGCDCASGS202021.xlsx
│   │   └── openweather/         # gitignored; 30 Parquet
│   └── processed/
│       ├── aagis_regions_repaired.gpkg
│       ├── cropping_mask.nc
│       ├── silo/                # masked NetCDFs
│       ├── bom_acornsat/        # processed station data
│       ├── abares/              # commodity CSVs (wheat/barley/canola)
│       └── abs_census/          # SA2 commodity CSVs
│
├── notebooks/
│   ├── 02_data_quality.ipynb
│   ├── 03_exploratory_analysis.ipynb
│   ├── 04_climate_indicators.ipynb
│   ├── 05_extreme_value_analysis.ipynb
│   ├── 06_climate_yield_statistical.ipynb
│   ├── 07_machine_learning.ipynb
│   ├── 08_spatio_temporal.ipynb
│   └── 09_synthesis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── io_utils.py
│   ├── paths.py
│   ├── log_utils.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── aagis_regions.py
│   │   ├── aclump.py
│   │   ├── silo.py
│   │   ├── bom_acornsat.py
│   │   ├── abares.py
│   │   ├── abs_census.py
│   │   ├── openweather.py
│   │   └── agfd.py              # Phase 09 addition
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── cropping_mask.py
│   │   ├── aagis_centroids.py
│   │   ├── region_aggregation.py   # Phase 02 addition
│   │   └── abares_aggregation.py   # Phase 02 addition
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── drought.py           # Phase 04
│   │   ├── heat.py              # Phase 04
│   │   └── frost.py             # Phase 04
│   ├── models/
│   │   ├── __init__.py
│   │   ├── evt.py               # Phase 05
│   │   ├── statistical.py       # Phase 06
│   │   ├── ml.py                # Phase 07
│   │   └── spatial.py           # Phase 08
│   └── viz/
│       ├── __init__.py
│       └── maps.py
│
├── scripts/
│   ├── phase00_s01_bootstrap_repo.py
│   ├── phase01_s01_init_manifest_and_fetch_aagis.py
│   ├── phase01_s02_init_aclump.py
│   ├── phase01_s03_build_cropping_mask.py
│   ├── phase01_s04_ingest_silo.py
│   ├── phase01_s05_ingest_bom_acornsat.py
│   ├── phase01_s06_ingest_abares.py
│   ├── phase01_s07_ingest_abs_census.py
│   ├── phase01_s08_ingest_openweather.py
│   ├── (phase02+ scripts to be added)
│   └── update_readme.py
│
├── outputs/
│   ├── figures/
│   │   └── .gitkeep
│   ├── tables/
│   │   └── .gitkeep
│   └── models/
│       └── .gitkeep
│
└── docs/
    ├── project_scope.md      # this document (v5)
    ├── findings.md           # Phase 10
    ├── methodology.md        # skeleton at Phase 01 s09, expanded through Phase 10
    └── phase_summaries/      # gitignored
        ├── phase00_summary.md
        ├── phase01_kickoff_prompt.md
        ├── phase01_summary.md
        └── .gitkeep
```

---

## Appendix B — Git and Closure Conventions

Per `portfolio_finalisation_playbook.md`:

- Branch per phase: `phase-XX-<short-topic>`; merge to `main` with `--no-ff`.
- Commit format: `[Phase XX - Step YY] <imperative verb phrase>` or `[Phase XX s01-sNN] <summary>` for consolidated commits.
- Closure: annotated tag `vX.Y-phaseNN-complete` on each phase merge; `v1.0` at final closure.
- Tag messages document phase deliverables.
- Polish commits post-vX.Y use prefix `Portfolio polish:`, `Docs:`, or `Cleanup:`.
- Substantive post-closure revisions bump to next patch version.

Phase 01 tag: `v0.1-phase01-complete` (annotated, on the merge commit into `main`).

---

## Appendix C — Document History

| Version | Date | Change |
|---|---|---|
| v1 | 2026 (pre-finalisation) | Initial draft; operational framing, OpenWeather + FAOSTAT + ABS, 5-phase plan |
| v2 | 2026-05-09 | Research-depth framing; SILO/BoM/ABARES primary with OpenWeather as validation; ABARES regions; broadacre tiered scope; 1961+/1980+ hybrid temporal design; six methodological pillars; 11-phase plan |
| v3 | 2026-05-11 | Formal title and codename aligned with GitHub repo; tech stack switched from conda hybrid to pip + venv, CPU-only; GPU support dropped; code quality tooling added; Python 3.11 → 3.12 to match Project 4 |
| v4 | 2026-05-14 | Pre-Phase 01 recalibration to Master-research-grade. Mixed-resolution spatial strategy (§3.6); grid-based SILO ingestion with ACLUMP cropping mask (§4.1, §4.4); AGFD as Phase 09 independent validation with observed-vs-derived discipline (§4.6, §2.5); MAUP robustness study (§5.6.2); AAGIS region formally named as primary yield unit (§3.1); xarray/netCDF4/rasterio added to stack |
| **v5** | **2026-07-09** | **Post-Phase 01 empirical reconciliation.** 7 findings from Phase 01 data acquisition reflected across the document: (a) §3.1, §11.6 AAGIS 3-digit code ↔ FDP text name mismatch documented; Phase 02 mapping table task defined. (b) §4.3, §5.3, §11.6 ABARES FDP per-typical-farm semantics documented; Phase 02 farm-count-weighting task defined. (c) §3.3, §4.3 yield-modeling period 1980 → 1990 (ABARES FDP earliest year). (d) §4.3, §13 ABS Ag Census 2020-21 = final Census; post-2020-21 requires modernised pipeline (out of v1.0 scope). (e) §4.2, §12.2 ACORN-SAT 18 stations unavailable; effective count = 94. (f) §4.1, §3.3, §5.1 SILO evappan effective from 1970; SPEI restricted to 1970+. (g) §4.5, §5.6.4 OpenWeather 10-region selection concretised with lat/lon centroids; 2022–2024 sample; 100% coverage acquired; total cost £11.40. Additional structural updates: §6.2 Phase 00 and Phase 01 marked complete with actual volumes; §9.2 runtime dependency list updated with openpyxl / python-dotenv / pyarrow; §11.7 first-use rule reiterated; §11.11 secrets management section added; Appendix A repo structure updated to reflect post-Phase 01 state; Appendix B Phase 01 tag documented. |

---

*End of Project Scope v5.*
