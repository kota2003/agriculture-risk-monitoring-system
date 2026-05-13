# Project 5 — Project Scope (v4)

**Repo / project codename:** `agriculture-risk-monitoring-system`
**Formal title:** *Agriculture Risk Monitoring System: A Multi-Method Research Framework for Australian Broadacre Cropping*
**Short title:** P5 — Agriculture Risk Monitoring System
**Author:** Kota
**Last updated:** 2026-05-14
**Document status:** Pre-Phase 01 recalibration to Master-research-grade. Replaces `p5_ProjectScope_v3.md` (v3).
**GitHub:** https://github.com/kota2003/agriculture-risk-monitoring-system

---

## 1. Identity and Purpose

### 1.1 One-sentence purpose

Build a research-grade analytical framework for monitoring agricultural risk in Australian broadacre regions, by quantifying how climate extremes translate into production risk using six methodologically distinct approaches (climate indicator engineering, extreme value theory, statistical climate–yield models, machine learning, spatio-temporal modelling, and multi-method synthesis) over an integrated dataset assembled from authoritative public sources.

The framework is the substantive deliverable; an interactive monitoring layer (dashboard) is an optional final-phase output that surfaces results from the framework.

### 1.2 Portfolio positioning

This is a **research-depth-first** portfolio project, scoped and executed to **Master-research-grade quality standards**. The intended evaluator set includes research-lab admissions committees, professors, and academically-literate hiring managers in addition to industry recruiters and engineers. Every methodological choice must be defensible under research peer review; engineering compromises that compromise methodological rigor are not acceptable, even when more convenient.

Its substantive contribution is a defensible, literature-grounded characterization of Australian climate–agriculture risk; its methodological contribution is a side-by-side comparison of how different families of methods quantify that risk, plus an explicit treatment of how spatial-unit choice (MAUP) affects conclusions.

**Framing evolution.** The project was initially scoped (v1) as an operational monitoring system built on a single commercial weather API and rule-based scoring. During Phase 00 scoping, the framing was refined (v2) to a research-depth-first multi-method investigation. v3 reconciled the two by treating the multi-method analytical framework as the core deliverable and positioning any monitoring/dashboard layer as a communication surface for it. v4 (this document) preserves that framing but recalibrates the methodological design to Master-research-grade standards: mixed-resolution spatial design, observed-vs-derived data discipline, and explicit MAUP robustness study. The shift is recorded for honesty (no hidden pivots) and is itself a portfolio signal of scoping discipline.

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
6. **Data validation (auxiliary).** How does a commercial weather API (OpenWeather) compare to the gold-standard scientific dataset (SILO) when used as the climate input layer?

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

---

## 3. Scope Boundaries

### 3.1 Geographic and spatial-unit framing

**Australia** is partitioned for the analysis using a **mixed-resolution spatial design** (see §3.6 for the full strategy):

- **Primary yield unit: AAGIS regions** (~60 regions). The Australian Agricultural and Grazing Industries Survey (AAGIS), operated by ABARES, partitions Australia into a two-level hierarchy of **zones × regions**. Zones (Pastoral, Wheat-sheep, High-rainfall) are coarse climatic/agronomic divisions; regions (~60) are the finest level of geographic aggregation at which ABARES publishes broadacre commodity statistics. AAGIS regions are the canonical unit for matching the ABARES yield data; the project uses them as the primary yield unit. Pastoral-zone regions are excluded from the cropping analysis since they are not broadacre-cropping environments.

- **Primary climate unit: SILO grid cells** (0.05° / ~5 km). Climate indicators are computed at SILO native grid resolution before any region-level aggregation, to avoid the information loss inherent in pre-aggregating temperature and rainfall data.

- **Secondary unit (high-resolution disaggregation): ABS SA2** (~2,300 regions). Used only where ABS Census data is the only available source.

- **Robustness unit: GRDC agro-ecological zones** (~21 zones). The project's primary Pillar 3 / Pillar 4 results will be re-computed at GRDC zone aggregation as a MAUP robustness study (§5.6).

State / territory aggregation will be reported descriptively only, not modeled at.

**Known data-quality caveat for AAGIS shapefiles**: the official AAGIS region mapping files contain geometry errors (self-intersecting polygons, invalid ring orientations). The `read.abares` R package documents these and auto-applies `sf::st_make_valid()` on import; the Python equivalent (`shapely.make_valid()` / `gdf.geometry = gdf.geometry.make_valid()`) will be applied as a standard step in the AAGIS ingestion pipeline (Phase 01) and logged in PROJECT_LOG.

### 3.2 Crop coverage

**Broadacre rainfed crops**, in three layered tiers:

| Tier | Crops | Treatment |
|---|---|---|
| Primary | Wheat | All six pillars; deepest analysis |
| Secondary | Barley, Canola | Methodology generalization study |
| Optional / deferred | Sorghum (summer crop), Cotton (irrigated) | Decision in Phase 03 EDA based on data availability and homogeneity |

**Out of scope:** horticulture, sugarcane, rice, pastoral livestock, dairy, irrigated systems beyond the optional cotton consideration.

### 3.3 Temporal

**Hybrid temporal design** (different windows for different uses):

| Use | Period | Justification |
|---|---|---|
| Climate climatology baseline | 1961–1990 (and 1991–2020 as alternative) | WMO standard reference periods; required for SPI/SPEI computation |
| EVT analyses (Pillar 2) | 1961–present | Long record needed for stable extreme-tail estimation |
| Climate–yield modeling (Pillars 3–5) | 1980–present | Modern agronomy / variety stability; pre-1980 yield data is non-comparable |
| OpenWeather cross-validation (Pillar 6 auxiliary) | OpenWeather historical API window only | Limited by API capability |

The 1961 start is a hard floor: SILO gridded data is high-quality from 1961 onward but progressively sparser before that.

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

#### 3.6.3 Information loss accounting

Computing climate indicators at grid resolution and then aggregating to region is **not** information-loss-free — the aggregation step still discards within-region variance. But it loses strictly less information than the alternative (computing indicators on already-aggregated regional climate). The project will report, where relevant, the within-region distributional properties of indicators (e.g., region-level standard deviation of GDD across grid cells), not just the within-region means.

---

## 4. Data Sources

### 4.1 Primary climate data

**SILO** (Queensland Department of Agriculture and Fisheries)

- **Type:** Daily gridded (~5 km / 0.05°) interpolated weather data, Australia-wide.
- **Period:** 1889–present; project uses 1961–present.
- **Variables planned:** maximum temperature, minimum temperature, daily rainfall, vapour pressure, evaporation, solar radiation.
- **Access:** SILO Long Paddock data drill; gridded data available via HTTPS direct download (per-year, per-variable NetCDF) or OPeNDAP/THREDDS for subsetting.
- **Status:** widely used in peer-reviewed Australian climate research.

**Ingestion strategy (v4 — grid-based with cropping mask).** Rather than retrieving point queries at AAGIS region centroids (the v3 approach, now retracted), the project retrieves SILO grid data for the full broadacre cropping area only:

1. The ABARES ACLUMP land-use raster (§4.4) is reprojected and resampled to the SILO 0.05° grid.
2. A binary cropping-area mask is constructed: True for grid cells whose ACLUMP class is broadacre cropping (wheat, barley, canola, mixed cereals); False elsewhere.
3. SILO yearly NetCDF files are retrieved for the masked cells only, via either (a) OPeNDAP / THREDDS spatial subsetting if available, or (b) full-extent download with post-hoc masking before persistence.
4. Persisted files in `data/processed/` retain xarray-compatible NetCDF format with the cropping mask applied.

**Volume estimate.** Australia's broadacre cropping zone covers roughly 5–10% of the continent. Masked SILO data at daily resolution × 6 variables × 65 years × ~10,000–50,000 broadacre grid cells is expected to total **~5–20 GB after compression**, vs. the ~100+ GB of the full continental grid. This is tractable for local disk and downstream processing.

### 4.2 Climate quality reference

**BoM ACORN-SAT** (Bureau of Meteorology)

- **Type:** Homogenised station-level long-term temperature record, ~112 stations.
- **Use:** Sanity-check SILO regional aggregates against ACORN-SAT station records to confirm SILO regional means are physically plausible.
- **Access:** BoM data portal.

### 4.3 Observed agricultural production data

This section deliberately uses the term **"observed"** to distinguish these sources from the **derived (model-output)** AGFD dataset described in §4.6. The distinction matters: observed yields are the only acceptable ground truth for yield modelling.

**ABARES** (Australian Bureau of Agricultural and Resource Economics and Sciences)

- Regional commodity statistics: **observed** annual area, production, yield by AAGIS region for major crops.
- AgSurf farm survey indicators (financial / operational, optional secondary use).

**ABS Agricultural Census**

- 5-yearly, SA2-level. Used for region-importance weighting and structural snapshots, not as a time-series.

### 4.4 Land use mask (ACLUMP)

**ACLUMP** (Australian Collaborative Land Use and Management Program, ABARES)

- **Type:** Catchment-scale land use raster of Australia. Most recent published vintage as of 2026 to be recorded in `data/raw/manifest.yaml` at retrieval.
- **Use:** Constructing the broadacre cropping-area mask used to subset SILO grid retrieval (§4.1) and to define the spatial scope of Pillar 1–2 grid-level analyses.
- **Access:** ABARES data portal (direct ZIP / GeoTIFF download).
- **License:** Creative Commons (per ABARES standard data licensing).

### 4.5 Validation comparator (OpenWeather)

**OpenWeather API** (Historical Weather)

- **Type:** Commercial API, historical observation + reanalysis blend.
- **Use:** *Validation target.* Compare OpenWeather output against SILO at a sample of AAGIS region centroids over the API's available historical window. The result is a methodological contribution in itself: how does a popular commercial API compare to the scientific gold standard?
- **Access:** API key required; subject to rate limits and historical-window constraints.

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

All sources are public or accessible via free / inexpensive API tiers. License terms will be:

- Recorded in `data/raw/manifest.yaml` per source.
- Acknowledged in the README and `methodology.md`.
- Respected in distribution: data files themselves are gitignored except for the manifest and small derived summaries; the project distributes scripts to retrieve data, not the data itself (consistent with playbook §5 "reproduce-from-code" default).

ABARES-sourced data (AAGIS shapefile, ACLUMP, AGFD) is available under Creative Commons licensing; project will follow the ABARES citation convention at https://www.agriculture.gov.au/abares/products/citations.

### 4.8 Manifest plan

`data/raw/manifest.yaml` will document, for each source:

- Canonical name, version / vintage, retrieval URL, retrieval date
- Field dictionary (variable names, units, encoding)
- License and attribution
- Known quirks (e.g., encoding issues, NA-handling requirements per playbook lesson 9, geometry-error fixes per §3.1 for AAGIS, observed-vs-derived classification per §4.6 for AGFD)

---

## 5. Methodological Pillars

Each pillar is implementable as an independent contribution; together they form the multi-method synthesis.

### 5.1 Pillar 1 — Climate Indicator Engineering

Implement literature-grounded climate-extreme indicators rather than bespoke ad-hoc constructions.

**Resolution discipline:** all indicators are computed at SILO grid resolution before any region aggregation. Region-level indicator series are derived products obtained by aggregating grid-level indicators (typically by area-weighted mean or quantile, depending on indicator), not by computing indicators from already-aggregated regional climate. This preserves within-region heterogeneity in the indicator construction step.

| Indicator | Source | What it captures |
|---|---|---|
| **SPI** (Standardised Precipitation Index) | McKee et al. (1993); WMO | Precipitation-only drought |
| **SPEI** (Standardised Precipitation–Evapotranspiration Index) | Vicente-Serrano et al. (2010) | Drought accounting for evaporative demand |
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

Cross-method comparison, with two additional dedicated robustness sub-studies.

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

Presented as a methodological side-finding from Phase 02 (data quality study).

---

## 6. Phase Plan

11 phases, numbered `phase00` through `phase10`. Each phase has a goal, deliverables, and an exit criterion. Phase numbering is fixed; phase ordering is sequential except where noted.

### 6.1 Summary table

| # | Title | Pillar | Goal |
|---|---|---|---|
| 00 | Scope & Setup | — | Lock design and environment |
| 01 | Data Acquisition (+ ACLUMP mask, grid-based SILO) | — | Reproducible ingestion of climate, agriculture, and mask data |
| 02 | Data Quality & Cross-Validation (+ grid-vs-region consistency check) | (P1, P6 aux.) | Verify integrity; OpenWeather–SILO comparison; grid-to-region aggregation consistency |
| 03 | Exploratory Analysis | — | Spatial-temporal patterns of climate and yields |
| 04 | Climate Indicator Engineering (grid-level) | P1 | Compute literature-grounded indicators at SILO grid resolution |
| 05 | Extreme Value Analysis (grid-level fit, region rollup) | P2 | EVT on climate indicators; return periods |
| 06 | Climate–Yield Statistical Models | P3 | Panel + quantile regression linkage |
| 07 | Machine Learning Models | P4 | ML benchmarks + SHAP |
| 08 | Spatio-Temporal Modeling | P5 | Hierarchical / spatial structure |
| 09 | Multi-Method Synthesis & Validation (+ MAUP study, AGFD validation) | P6 | Cross-method comparison; MAUP robustness; AGFD validation |
| 10 | Communication Layer | — | README polish, findings.md, methodology.md, optional dashboard |

### 6.2 Phase detail

#### Phase 00 — Scope & Setup

- **Goal:** Lock down project design and reproducible environment.
- **Deliverables:** `project_scope.md` (v4); `requirements.txt` + `requirements-dev.txt`; initial repo structure; initial PROJECT_LOG.md entries; PROJECT_WORKFLOW.md instantiation.
- **Exit criterion:** Scope approved; environment reproducible.

#### Phase 01 — Data Acquisition

- **Goal:** Reproducible retrieval of SILO, BoM ACORN-SAT, ABARES (yields + AAGIS shapefile), ACLUMP (cropping-area raster), ABS Census, and OpenWeather data.
- **Deliverables:**
  - Per-source ingestion scripts in `src/ingestion/`: `silo.py`, `bom_acornsat.py`, `abares.py` (yields), `aagis_regions.py` (shapefile + geometry repair), `aclump.py` (land-use raster), `abs_census.py`, `openweather.py`.
  - `src/processing/cropping_mask.py` — construct broadacre cropping mask at SILO resolution from ACLUMP.
  - Populated `data/raw/`; `data/raw/manifest.yaml` with all sources entered.
  - Phase 01 sanity-check notebook (Phase 01 ingestion summary: file counts, date ranges, mask coverage).
- **Exit criterion:** Every source retrievable from scratch via documented script, reproducing the same files (or files matching a documented hash up to known floating-point variation). Cropping mask covers expected broadacre area.

#### Phase 02 — Data Quality & Cross-Validation

- **Goal:** Quantify and document data integrity issues; complete OpenWeather vs. SILO comparison study; verify grid-to-region aggregation consistency.
- **Deliverables:**
  - Data quality report.
  - OpenWeather–SILO agreement metrics (by variable, by region).
  - **Grid-vs-region aggregate consistency check**: confirm that area-weighted means of grid-level SILO match expected regional climatologies and behave sensibly under aggregation (no obvious mask boundary artefacts, no implausible discontinuities at AAGIS region edges).
  - Cross-validation notebook.
- **Exit criterion:** Quality issues resolved or explicitly flagged with downstream-handling strategy; OpenWeather–SILO comparison written up as a self-contained mini-study; grid-aggregation consistency confirmed.

#### Phase 03 — Exploratory Analysis

- **Goal:** Establish baseline empirical understanding of climate and yield variation.
- **Deliverables:** EDA notebook; key visualizations (regional climate climatologies, yield trends and dispersions); decision on optional crops (Sorghum / Cotton).
- **Exit criterion:** Clear narrative of where, when, and how much climate and yield variation occurs.

#### Phase 04 — Climate Indicator Engineering

- **Goal:** Implement and validate literature-grounded climate extreme indicators at SILO grid resolution.
- **Deliverables:** `src/indicators/drought.py`, `heat.py`, `frost.py`; grid-level indicator time series in `data/processed/`; region-aggregated series with within-region distributional summaries; indicator notebook with validation against published equivalents where possible.
- **Exit criterion:** SPI, SPEI, EHF, GDD, consecutive dry days, frost days computed at grid resolution, validated, persisted, and aggregated to AAGIS region with distributional summaries.

#### Phase 05 — Extreme Value Analysis

- **Goal:** Apply EVT to climate extremes at grid level, aggregate return periods to region, test stationarity.
- **Deliverables:** GEV / POT models per grid cell × indicator; region-aggregated return level maps; non-stationary EVT extension; diagnostic plots.
- **Exit criterion:** Return periods estimated with appropriate diagnostics; grid-level fitting yields stable per-region tail estimates; non-stationary results reported with honest uncertainty.

#### Phase 06 — Climate–Yield Statistical Models

- **Goal:** Establish associational climate–yield links via panel and quantile methods at AAGIS region level.
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
- **Deliverables:** Polished README; `docs/findings.md`; `docs/methodology.md`; PROJECT_LOG closing entry; v1.0 git tag; (optional) React dashboard.
- **Exit criterion:** v1.0 tag pushed to GitHub; repo passes the post-publication checks in `portfolio_finalisation_playbook.md` §14.

### 6.3 Sequencing notes

- Phases 04 and 03 can be run in either order; default is 03 before 04.
- Phases 05, 06, 07, 08 are partially independent and can be interleaved if memory pressure on a single chat necessitates splitting.
- Phase 09 hard-depends on at least Phases 04, 06, and one of {07, 08} being complete.
- Phase 10 is final and runs only after Phase 09.

### 6.4 Rough time estimate

Indicative only. The user has stated time horizon is open; quality-gating (per PROJECT_WORKFLOW §11) takes precedence over schedule.

| Phase block | Indicative weeks |
|---|---|
| 00–02 (foundation, expanded scope) | 3–5 |
| 03–04 (EDA + indicators) | 3–5 |
| 05 (EVT) | 2–4 |
| 06 (Statistical) | 3–5 |
| 07 (ML) | 2–4 |
| 08 (Spatio-temporal) | 2–4 |
| 09 (synthesis + MAUP + AGFD) | 3–5 |
| 10 (closure) | 1–2 |
| **Total** | **19–34 weeks** (≈ 5–8.5 months) |

This is a working-paper-scale project. The user has explicitly accepted this scope.

---

## 7. Deliverables

### 7.1 Public (committed and pushed)

- `README.md` — recruiter entry point; structurally similar to Project 4 but stylistically project-specific
- `docs/project_scope.md` — this document
- `docs/findings.md` — substantive findings narrative
- `docs/methodology.md` — methods and conventions reference
- `PROJECT_LOG.md` — append-only decision log
- `requirements.txt`, `requirements-dev.txt` — pinned dependencies (Level 3 per playbook §8)
- `.gitignore`, `.python-version`, `LICENSE` (MIT)
- `notebooks/0X_*.ipynb` — phase-aligned notebooks, executed end-to-end
- `src/*.py` — reusable modules including:
  - `src/ingestion/silo.py`, `bom_acornsat.py`, `abares.py`, `aagis_regions.py`, `aclump.py`, `abs_census.py`, `openweather.py`, `agfd.py` (Phase 09)
  - `src/processing/cropping_mask.py`, `quality_checks.py`, `region_aggregation.py`
  - `src/indicators/`, `src/models/`, `src/viz/`
- `scripts/phaseXX_sYY_*.py` — analytical step scripts (not log-only orchestrators)
- `outputs/figures/*.png`, `outputs/tables/*.csv` — referenced from notebooks and README
- `data/raw/manifest.yaml` — small, documents data sources

### 7.2 Internal (gitignored)

- `data/raw/*` (except manifest), `data/processed/*` — large, regeneratable
- `outputs/models/*.joblib` and similar — large, regeneratable from training scripts (playbook §7 default)
- `docs/phase_summaries/phaseXX_summary.md` — internal handoff artefacts (PROJECT_WORKFLOW §10)
- `__pycache__/`, `.ipynb_checkpoints/`, `.venv/`, `.env`, `.vscode/`, `.idea/`, `*.DS_Store`
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
- OpenWeather–SILO comparison study completed and published (Phase 02), independently of whether downstream pillars need it.

### 8.3 Engineering

- Fresh-clone reproducibility: a recruiter / engineer can clone the repo, install pinned dependencies, and reproduce every figure and table in the deliverables.
- All raw data is retrievable from public APIs / portals via documented scripts (no manual downloads required for the reader).
- Clean repo: no scratch files, no backup duplicates, no log-only orchestrators left behind.
- Per-phase commit history preserved via `--no-ff` merges.
- v1.0 annotated tag at project closure.

### 8.4 Portfolio

- README satisfies recruiter 5-minute scan and engineer 30-minute audit (playbook §1 finalisation test).
- `findings.md` and `methodology.md` exist and are publication-quality.
- Repo description, topics, and About section configured on GitHub.

---

## 9. Tech Stack

### 9.1 Environment management

**pip + venv** (CPU-only stack). conda is intentionally not used in this project.

- **Python 3.12** (locked at project start to match Project 4's runtime — preserving portfolio-wide Python-version consistency — and to avoid the Project 4 lesson 5 interpreter-mismatch issue). On Windows, the project uses `py -3.12` rather than the bare `python` command to guarantee version selection even when 3.13 is the default launcher target.
- **venv** placed at repository root as `.venv/` (relative-path-friendly for editor and pre-commit hooks)
- **pip** with manually composed `requirements.txt` (and `requirements-dev.txt` for development-only tools)

**Rationale.** The project does not require GPU compute. Pillars 1–3, 5, 6 are CPU-bound by design (statistical / EVT / spatial / synthesis). Pillar 4 (XGBoost, LightGBM, RandomForest) runs on CPU within minutes given the AAGIS region × 1980+ sample size. Choosing pip+venv over conda yields a simpler, more transparent, and more recruiter-reproducible environment, at the deliberate cost of foregoing GPU acceleration for Pillar 4 and any Bayesian Pillar 5 extensions.

### 9.2 Core

- pandas, numpy, pyyaml, requests, pycountry (for region-coding utilities)

### 9.3 Statistical / econometric

- statsmodels (panel regression, GAM via statsmodels.gam)
- linearmodels (clustered SEs, panel methods)
- pingouin or scipy.stats (auxiliary statistical tests)

### 9.4 Extreme value

- scipy.stats (GEV, GPD via genextreme, genpareto)
- pyextremes (POT and stationarity workflows)
- alternatively: SDFC or custom non-stationary GEV implementation

### 9.5 Machine learning (CPU)

- scikit-learn, xgboost (CPU), lightgbm (CPU)
- shap

### 9.6 Spatial / raster

- **xarray, netCDF4, rasterio** for grid and NetCDF handling (SILO grid, ACLUMP raster, AGFD NetCDF)
- **geopandas, shapely, pyproj** for vector handling (AAGIS region shapefile, GRDC zones)
- **tqdm** for download progress (SILO grid downloads can be long)
- libpysal (Moran's I and spatial weights) — added Phase 08
- optionally: pymc or numpyro for Bayesian hierarchical models (CPU sampling; performance considerations apply)

### 9.7 Visualization

- matplotlib, seaborn for static figures
- xarray plotting for grid-level / map visualisations
- plotly for any interactive figures
- contextily for map basemaps (cartopy intentionally avoided due to non-pip system dependencies)

### 9.8 Notebook tooling

- jupyter, ipykernel, nbformat, nbconvert

### 9.9 Code quality (dev-only)

Maintained in `requirements-dev.txt`, not in main `requirements.txt`:

- **black** — auto-formatting
- **ruff** — linting
- **pre-commit** — git hook orchestration; `.pre-commit-config.yaml` runs black + ruff on every commit

### 9.10 Editor integration

- `.vscode/settings.json` committed to the repository, pinning `python.defaultInterpreterPath` to `.venv/bin/python` (or `.venv\\Scripts\\python.exe` on Windows). This prevents the Project 4 lesson 5 interpreter-mismatch issue at the repository level.

### 9.11 Optional

- streamlit (only if dashboard is built and React is rejected)
- React + Recharts / Mapbox / D3 (only if dashboard is built and React is selected)

### 9.12 Reproducibility level

**Level 3 (pinned)** per playbook §8. Pinning is performed at project closure (Phase 10). During development, `>=` constraints are acceptable.

`requirements.txt` will be **manually composed** from actual project imports, **not generated by `pip freeze`**, to avoid Project 4 lesson 1.

---

## 10. Reproducibility Strategy

### 10.1 Random seeds

- A project-wide seed (`SEED = 42` by convention) is set in every script that involves stochasticity.
- ML training uses `random_state=42`; bootstrap procedures use the same seed; cross-validation splits are deterministic.

### 10.2 Manifests

- `data/raw/manifest.yaml` records every data source with retrieval URL, version, retrieval date, and per-file metadata.
- New data sources require a manifest update before Phase 01 considers ingestion complete.

### 10.3 Pinned dependencies

- Per §9.12.

### 10.4 Environment reproduction

- `py -3.12 -m venv .venv` (Windows) or `python3.12 -m venv .venv` (macOS / Linux), followed by `pip install -r requirements.txt`, reproduces the runtime environment on any platform with Python 3.12 available.
- `requirements-dev.txt` installs dev-only tools (black, ruff, pre-commit).
- `.python-version` records the exact Python minor version for tools like pyenv.

### 10.5 Determinism boundaries

The project is CPU-only by design (§9.1), avoiding GPU non-determinism. Remaining determinism concerns:

- Multi-threaded BLAS / OpenMP execution order for some scikit-learn / XGBoost / LightGBM kernels. Where this matters for a reported result, the relevant section documents the expected variation magnitude.
- Floating-point summation order in groupby aggregations across pandas versions. Mitigated by pinning pandas in `requirements.txt` at closure.

### 10.6 Encoding and pandas-NA defaults

Per Project 4 lessons:

- All `pd.read_csv` calls use `keep_default_na=False` and explicit `na_values` for any column containing country codes, region codes, or short categorical strings (lesson 9).
- An encoding-fallback CSV reader (`utf-8` → `cp1252` → `latin-1`) is implemented in `src/io_utils.py` from Phase 01 (lesson 8).

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
- Entry on every material design decision (data source change, method choice, override, etc.).

### 11.5 Adaptive override convention

Per Project 4 precedent: when a step plan must change mid-execution, the override is logged as a discrete PROJECT_LOG entry referencing the original plan and the rationale for change. This is an explicit honesty signal in the audit trail, not a deviation to hide.

### 11.6 `src/` promotion rule

Per PROJECT_WORKFLOW §6.2: a function moves from `scripts/` to `src/` when it is called more than once or is non-trivial and likely reusable. Reviewed at each phase boundary.

### 11.7 Code quality tooling

- **black** for auto-formatting (line length default 88), enforced on every commit.
- **ruff** for linting; minimum rule set is the ruff default plus pandas-vet and numpy plugins; rule additions logged in PROJECT_LOG.
- **pre-commit** orchestrates both via `.pre-commit-config.yaml`; installed locally via `pre-commit install` after env setup.
- Dev-only tools live in `requirements-dev.txt`, not `requirements.txt`, so the runtime dependency surface stays minimal.

### 11.8 Editor configuration

- `.vscode/settings.json` is committed to the repository.
- `python.defaultInterpreterPath` is set to a relative path inside `.venv/` so the correct Python is auto-selected when the repo is opened.
- This is a structural fix for Project 4 lesson 5 (interpreter mismatch). Personal user preferences (themes, keybindings) do **not** belong in this file; only project-correctness settings.

### 11.9 Notebook discipline

- Phase notebooks execute top-to-bottom on a fresh kernel without error.
- Every figure has an interpretation sentence beneath it.
- Conclusion section honest about limitations.
- No leftover debug prints or commented-out code.

### 11.10 Knowledge management (Claude side)

At each phase boundary, recommend Knowledge updates to the user (PROJECT_WORKFLOW §9.2). Aim for ~5 files in Knowledge:

1. `PROJECT_WORKFLOW.md`
2. `portfolio_finalisation_playbook.md`
3. `project_scope.md` (this file)
4. The most recent phase summary (rolling)
5. Latest `findings.md` and `methodology.md` once they exist

---

## 12. Risks and Limitations

### 12.1 Methodological

- **MAUP exposure.** Different spatial aggregation choices can produce different statistical conclusions. *Mitigation:* mixed-resolution design (§3.6); explicit GRDC-zone robustness study in Pillar 6 (§5.6.2).
- **AAGIS region climate-boundary non-alignment.** AAGIS regions are drawn for agricultural-statistics sampling purposes, not by climate criteria. Within-region climate heterogeneity is therefore expected. *Mitigation:* grid-level indicator computation preserves within-region heterogeneity; within-region distributional summaries (not just means) are reported.
- **Quantile regression at extreme quantiles** (τ = 0.05, 0.95) is unstable with small samples. Use τ ∈ [0.1, 0.9] as defaults; report tail estimates as exploratory.
- **Non-stationary EVT** trend detection has notoriously low statistical power. Report effect sizes alongside hypothesis tests; do not over-interpret marginal significance.
- **Spatial models** require a defensible spatial weights matrix; arbitrary choices can drive results. Multiple weight specifications will be tested.
- **ML overfitting risk** to weather × region interactions. Spatial blocked CV is the primary defense; performance gap between spatial CV and naive CV is itself a reportable diagnostic.

### 12.2 Data

- **Observed-vs-derived data discipline.** AGFD is model output, not observation. Using it as a training target or yield substitute is a circularity error and is explicitly forbidden in this project (§4.6, §2.5).
- **OpenWeather historical window** may be too short for some validation goals; the OpenWeather–SILO comparison may be confined to recent years only.
- **ABARES regional yield data** has known structural breaks (region boundary changes). Document and either harmonize or restrict analysis to stable-boundary periods.
- **SILO interpolation quality** degrades in remote / station-sparse regions (e.g., far-western pastoral zones). Project's restriction to broadacre cropping mitigates this since cropping zones have denser station coverage, but the issue is acknowledged.
- **Pre-1980 yield data** is non-comparable; restricting yield-linkage analysis to 1980+ is a deliberate concession.
- **AAGIS shapefile geometry errors** are known and repaired via `shapely.make_valid()` (§3.1). Repair step is logged in PROJECT_LOG.

### 12.3 Engineering

- **SILO data volume**. With cropping-mask subsetting, expected to be ~5–20 GB compressed (vs. ~100+ GB full continental grid). Tractable for local disk.
- **Compute limits** for hierarchical Bayesian models. Mitigation: start with frequentist multilevel models (statsmodels / pymer4); escalate to Bayesian only if needed.
- **Memory / chat handoffs**. Mitigation: PROJECT_WORKFLOW §10 phase summary protocol; expect 2–3 chat handoffs within larger phases.

### 12.4 Scope

- **Crop coverage scope drift**. Adding sorghum / cotton mid-project is tempting but methodologically expensive (irrigation regime differs). Defer to Phase 03 decision (§3.2).
- **Dashboard scope drift**. Decision is deferred (§7.3). Resist mid-project React build-out unless it directly serves communicating findings.

---

## 13. Flexibility Clause

This Scope reflects current best understanding as of 2026-05-14. It is expected — and welcome — that some elements will need revision as the project encounters reality:

- **Substantive findings may redirect emphasis.** If Phase 03 EDA reveals that a particular crop or region exhibits the cleanest signal, downstream phases may concentrate there.
- **Methodological choices may change.** If Phase 06 finds that quantile regression is unstable at the available sample sizes, alternative tail-modeling approaches will be considered.
- **Phases may split or merge.** If a phase grows too large for one chat, it is split per PROJECT_WORKFLOW §9.3. If two phases naturally converge, they may be merged with a PROJECT_LOG entry recording the change.
- **Optional pillars / crops / deliverables** (Pillar 5 spatial, optional crops, dashboard) are explicitly subject to deferral or omission with logged rationale.

What is **not** flexible:

- The research framing (multi-method climate–agriculture risk in Australian broadacre).
- The mixed-resolution spatial design philosophy (§3.6) and observed-vs-derived data discipline (§4.6).
- The reproducibility and engineering standards.
- The honesty conventions (no hidden overrides, explicit non-claims, calibrated uncertainty).

Revisions to this Scope are versioned (`p5_ProjectScope_v5.md`, etc.) with a PROJECT_LOG entry summarizing the change.

---

## Appendix A — Initial Repo Structure (updated for v4)

```
agriculture-risk-monitoring-system/
│
├── README.md
├── PROJECT_LOG.md
├── requirements.txt
├── requirements-dev.txt
├── .python-version
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
│
├── .vscode/
│   └── settings.json        # committed; pins interpreter to .venv
│
├── data/
│   ├── raw/
│   │   ├── .gitkeep
│   │   └── manifest.yaml
│   └── processed/
│       └── .gitkeep
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
│   │   ├── silo.py
│   │   ├── bom_acornsat.py
│   │   ├── abares.py            # yields
│   │   ├── aagis_regions.py     # shapefile + geometry repair
│   │   ├── aclump.py            # land-use raster (cropping mask source)
│   │   ├── abs_census.py
│   │   ├── openweather.py
│   │   └── agfd.py              # Phase 09 validation benchmark
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── quality_checks.py
│   │   ├── cropping_mask.py     # constructs broadacre mask at SILO resolution
│   │   └── region_aggregation.py
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── drought.py
│   │   ├── heat.py
│   │   └── frost.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── evt.py
│   │   ├── statistical.py
│   │   ├── ml.py
│   │   └── spatial.py
│   └── viz/
│       ├── __init__.py
│       └── maps.py
│
├── scripts/
│   ├── phase00_s01_bootstrap_repo.py
│   ├── phase01_s01_*.py
│   ├── (...)
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
    ├── project_scope.md
    ├── findings.md          # populated in Phase 10
    ├── methodology.md       # populated in Phase 10
    └── phase_summaries/     # gitignored
        └── .gitkeep
```

---

## Appendix B — Git and Closure Conventions

Per `portfolio_finalisation_playbook.md`:

- Branch per phase: `phase-XX-<short-topic>`; merge to `main` with `--no-ff`.
- Commit format: `[Phase XX - Step YY] <imperative verb phrase>`.
- Closure: annotated tag `v1.0` on the final-phase merge commit.
- Tag message: `"Project 5 closed YYYY-MM-DD - Agriculture Risk Monitoring System: A Multi-Method Research Framework for Australian Broadacre Cropping"`.
- Polish commits post-v1.0 use prefix `Portfolio polish:` or `Docs:` or `Cleanup:`.
- Substantive post-closure revisions bump to `v1.1` with PROJECT_LOG entry.

---

## Appendix C — Document History

| Version | Date | Change |
|---|---|---|
| v1 | 2026 (pre-finalisation) | Initial draft (`p5_ProjectScope.md`); operational framing, OpenWeather + FAOSTAT + ABS, 5-phase plan |
| v2 | 2026-05-09 | Research-depth framing; SILO/BoM/ABARES primary with OpenWeather as validation; ABARES regions; broadacre tiered scope; 1961+/1980+ hybrid temporal design; six methodological pillars; 11-phase plan; full reproducibility / engineering conventions |
| v3 | 2026-05-11 | (a) Formal title and codename aligned with GitHub repo; framing reconciled as research framework that can power a monitoring layer. (b) Tech stack switched from conda hybrid to pip + venv, CPU-only; GPU support intentionally dropped. (c) Code quality tooling (black + ruff + pre-commit) and committed `.vscode/settings.json` added to conventions. (d) Repo structure, document history, and tag-message convention updated to match. (e) Python version corrected from 3.11 → **3.12** to match Project 4's runtime and preserve portfolio-wide consistency |
| v4 | 2026-05-14 | This document. Pre-Phase 01 recalibration to Master-research-grade. Key substantive changes: (a) New §3.6 Spatial Resolution Strategy with mixed-resolution pillar-to-unit mapping and explicit MAUP commitment. (b) §4.1 SILO ingestion rewritten — grid-based subsetting with ACLUMP cropping mask, replacing v3 point-centroid strategy. (c) New §4.4 ACLUMP land-use mask as primary data source. (d) New §4.6 AGFD as Phase 09 independent validation benchmark, with explicit observed-vs-derived discipline. (e) §5.1, §5.2 clarified — climate indicators and EVT at grid resolution with region rollup. (f) §5.6 expanded — MAUP robustness study (GRDC zone re-aggregation) + AGFD validation added to Pillar 6. (g) §3.1 — AAGIS region formally named, zone×region hierarchy documented, geometry-error caveat. (h) §6 phase plan — Phase 01 acquires ACLUMP mask; Phase 02 adds grid-vs-region consistency check; Phase 09 ingests AGFD and runs MAUP study. (i) §9 tech stack — xarray, netCDF4, rasterio, tqdm added. (j) §12 risks — AAGIS climate-boundary non-alignment and observed-vs-derived discipline explicitly acknowledged. |

---

*End of Project Scope v4.*
