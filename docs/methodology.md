# Methodology

*Agriculture Risk Monitoring System — Master research-grade portfolio project*

**Last updated:** 2026-07-10 (Phase 01 s09 closure)
**Status:** Progressive document — Phase 01 sections are populated; Phase 02+ sections are placeholders that will be filled as each phase executes.
**Companion documents:** `docs/project_scope.md` (v5); `PROJECT_LOG.md` (append-only decision log); `data/raw/manifest.yaml` (data provenance).

---

## 0. Purpose of this document

`methodology.md` records the **why** behind each methodological choice made across the project's lifecycle: which data sources were selected and why alternatives were rejected, which spatial and temporal units were chosen, which method families were prioritised, and which trade-offs were consciously accepted. It is the counterpart to `findings.md` (which will report the *what*) and to `PROJECT_LOG.md` (which records *decisions as they happen*, in append-only chronological order).

Where `PROJECT_LOG.md` is transactional (each entry documents one decision at the moment it was made), this document is the **synthesised, reader-facing narrative** of methodology across the whole project. Phase 10 will polish it into a stand-alone deliverable suitable for a working-paper appendix or a portfolio-facing "methods" section.

**Reading order.** New readers should start with `README.md`, then this document (skimming to the phases already executed), then `findings.md` for the results. Reviewers who wish to audit provenance should cross-reference `PROJECT_LOG.md` (for decision timing) and `data/raw/manifest.yaml` (for data-source metadata).

---

## 1. Overall research design

### 1.1 Framing

The project quantifies how climate extremes translate into agricultural production risk in Australian broadacre regions, using multiple methodological families side-by-side (statistical, extreme-value-theoretic, machine-learning, spatial-hierarchical). The framing is deliberately **breadth-across-methods** — complementing Project 4's depth-within-a-single-method (panel econometrics on education inequality).

The framing was refined across four scope revisions:
- **v1** (early draft): operational monitoring system with commercial weather API.
- **v2** (2026-05-09): research-depth-first, multi-method investigation.
- **v3** (2026-05-11): tech stack lockdown (pip + venv, Python 3.12).
- **v4** (2026-05-14): Master research-grade recalibration (mixed-resolution spatial design, observed-vs-derived discipline, MAUP robustness).
- **v5** (2026-07-09): Post-Phase 01 empirical reconciliation of seven findings from data acquisition.

See `docs/project_scope.md` Appendix C for the full revision history.

### 1.2 Multi-method commitment

Six methodological pillars are executed against a single integrated dataset:

1. Climate indicator engineering (grid-level).
2. Extreme value analysis (grid-level fit, region rollup).
3. Climate–yield statistical models (panel + quantile regression).
4. Machine learning models (RF / XGBoost / LightGBM + SHAP).
5. Spatio-temporal / hierarchical modeling.
6. Multi-method synthesis, including MAUP robustness and independent AGFD validation.

Cross-method comparison is the methodological contribution of the project. Places where methods agree strengthen substantive claims; disagreements are reported honestly as methodologically informative, not hidden.

### 1.3 Observed-vs-derived data discipline

A single explicit discipline threads through all data decisions: **derived (simulation-output) datasets are never used as training targets for other models.**

- **ABARES observed yields** (Farm Data Portal, per-typical-farm) are the training target for Pillars 3–5.
- **AGFD simulation outputs** (ABARES farmpredict model) are used only as an **independent Phase 09 validation benchmark**, never as training input or yield substitute.
- **OpenWeather API** is used as a **validation comparator against SILO** (Phase 02 study), never as a climate input for Pillars 3–5.

Using model outputs as ground truth for other models constitutes a circularity error and is explicitly forbidden. See `docs/project_scope.md` §2.5, §4.6.

---

## 2. Data-source selection (Phase 01)

Eight data sources are integrated. Each source's role, selection rationale, and known constraints are recorded in `data/raw/manifest.yaml`; this section summarises the *why* of each choice.

### 2.1 SILO gridded climate data (primary climate input)

- **Chosen because:** SILO is the Australian scientific gold standard for daily gridded climate: peer-reviewed methodology, continental coverage from 1889, native 0.05° (~5 km) resolution, publicly available under Creative Commons.
- **Alternatives considered and rejected:** ERA5-Land (global, but coarser at ~9 km and less locally calibrated); AWAP (older, being deprecated).
- **Grid-first commitment.** SILO is retrieved at native grid resolution and climate indicators are computed at grid resolution before any AAGIS-region aggregation. This preserves within-region heterogeneity that region-mean pre-aggregation would destroy.
- **Constraint discovered.** Pan evaporation (`evap_pan`) is effectively populated only from 1970 onward at continental extent, not 1961 like the other five variables. Downstream consequence: SPEI (which requires evap_pan) is constrained to 1970+.

### 2.2 BoM ACORN-SAT (homogenised station reference)

- **Chosen because:** ACORN-SAT is the BoM-maintained homogenised temperature record, used for cross-validating gridded products against direct station observations.
- **Constraint discovered.** 18 of the 112 nominally listed stations are permanently unavailable at the BoM hqsites endpoint (HTTP 404 across all zero-padding variants). Effective count = 94. Three of the 18 are in broadacre-relevant regions (008039 WA Wheatbelt, 008051 WA Wheatbelt margin, 073054 NSW Riverina); Phase 02 will assess the coverage impact on regional SILO validation.

### 2.3 ABARES Farm Data Portal (primary observed yield)

- **Chosen because:** ABARES FDP is the authoritative source of AAGIS-region-level annual broadacre commodity data (yield, area, production) with continuous coverage from 1990 to present.
- **Alternatives considered and rejected:** ABARES Australian Gridded Farm Data (AGFD) is a simulation output — see §2.6 below.
- **Critical semantic discovery.** FDP `Value` columns are **survey-weighted per-typical-farm averages**, not region or national totals. Verified empirically: national `Industry='All Broadacre'` wheat 2022 = 656 t/farm, which times ~55,000 broadacre farms ≈ 36 Mt ≈ published ABS national total.
  - `yield_t_ha = production_t / area_ha` remains dimensionally valid as per-farm-representative regional yield.
  - `area_ha` and `production_t` are per-typical-farm and require farm-count weighting for conversion to region totals; deferred to Phase 02 (`src/processing/abares_aggregation.py`).
- **Temporal constraint.** Scope v4 §3.3 originally specified 1980+ for yield modelling; FDP earliest year is 1990. Scope v5 §3.3 updated accordingly.
- **Region-key naming mismatch.** FDP identifies regions by text names (e.g., `'NSW Riverina'`) while the AAGIS shapefile uses 3-digit codes (e.g., `'123'`). Both encode 32 aligned regions; explicit mapping table required. Deferred to Phase 02 (`src/processing/region_aggregation.py`).

### 2.4 ABS Agricultural Census 2020-21 (SA2 cross-section)

- **Chosen because:** ABS Census provides the only SA2-granularity agricultural commodity data, needed for Pillar 4–5 region-importance weighting.
- **Structural constraint discovered.** The 2020-21 Agricultural Census was the **final** ABS Agricultural Census. Post-2020-21, ABS transitioned to a modernised pipeline (Levy Payer Register + satellite crop mapping), released annually from 2022-23, out of Project 5 v1.0 scope. Project 5 v1.0 freezes SA2 weighting at 2020-21 vintage.
- **Tier structure validated empirically.** SA2 commodity counts (wheat 394 > barley 367 > canola 255) confirm the intended `docs/project_scope.md` §3.2 crop tier structure.

### 2.5 ACLUMP land-use raster (cropping mask source)

- **Chosen because:** ACLUMP's catchment-scale land use raster is the definitive land-use classification for Australia, needed to construct the broadacre cropping-area mask that constrains SILO grid ingestion.
- **Cropping coverage verified.** ALUM class 3.3 "Cropping" occupies 5.131% of non-NODATA pixels across the continental raster, consistent with published Australian broadacre cropping area estimates.
- **Threshold sensitivity study.** Three mask thresholds (0.05, 0.10, 0.20 fraction of the SILO 0.05° grid cell classified as broadacre cropping) tested at s03. Primary threshold selected: 0.05 (t005), most permissive. Alternate thresholds persisted for Phase 02 sensitivity analysis.

### 2.6 AGFD (ABARES Australian Gridded Farm Data) — deferred to Phase 09

- **Ingestion timing.** AGFD is deferred to Phase 09 because its role is exclusively as an independent validation benchmark for the project's own Pillar 3–5 predictions, not as an ingestion for Pillars 1–8.
- **CRITICAL non-use commitment.** AGFD is model output (ABARES farmpredict simulation), not observation. Using it as a training target or yield substitute would be a circularity error. See `docs/project_scope.md` §4.6 for the explicit non-use commitment.

### 2.7 OpenWeather One Call 3.0 (validation comparator)

- **Role.** OpenWeather is used as a **validation comparator** against SILO for a methodological side-study (Phase 02 §5.6.4). NEVER a training input for Pillars 3–5.
- **Sample design.** 10 AAGIS region centroids (representative points, guaranteed inside polygon) × 1,096 daily records (2022-01-01 to 2024-12-31) = 10,960 daily records target. 100.0% acquired.
- **Cost containment.** Daily hard limit set to 11,000 calls in the OpenWeather dashboard; script soft-quota at 10,500. Total cost across two sessions: ~£11.40 (≈ AUD $22).
- **Regions selected.** 6 states, 5 climate types, all Wheat-Sheep zone except region 631 TAS (High Rainfall). See `data/raw/manifest.yaml` `sources.openweather.sampled_regions` for the full centroid list.

### 2.8 AAGIS regions (primary spatial unit)

- **Chosen because:** AAGIS is the ABARES sampling framework for the Farm Data Portal, making it the natural unit for matching yield data. AAGIS regions are a stable, published spatial partition of Australia.
- **Geometry validity issues.** The raw shapefile ships with self-intersecting rings and invalid ring orientations. Repaired via `shapely.make_valid()` at ingest; validity re-checked before persistence.

---

## 3. Spatial-unit strategy

### 3.1 Mixed-resolution design (scope v5 §3.6)

The project uses a mixed-resolution strategy rather than a single spatial unit. The core commitment:

- **Climate indicators** (Pillar 1) and **EVT** (Pillar 2) are computed at SILO grid resolution (~5 km) before any region-level aggregation. This avoids the information loss inherent in pre-aggregating temperature and rainfall to regional means.
- **Yield-linkage models** (Pillars 3, 4) are fit at AAGIS region level (the natural unit of the yield data). Grid-level climate enters as engineered features (means, quantiles, extremes within region) — preserving within-region heterogeneity in the feature set.
- **Spatio-temporal models** (Pillar 5) use AAGIS region as the primary level, with grid-derived neighbourhood structure.
- **MAUP robustness study** (Pillar 6) re-computes Pillar 3 / 4 results at GRDC agro-ecological zone aggregation (~21 zones) as the alternative unit; stability of headline findings is reported honestly.
- **ABS SA2** is used only for cross-sectional Pillar 4–5 weighting (where SA2 granularity is the only available source).

### 3.2 Why not single-unit? (Explicit design justification)

Most climate-impact studies pick one spatial unit (region, county, grid) and proceed without discussing the alternative. This project makes the unit choice visible and defended because:

- Each pillar has a natural scale; forcing all pillars onto one unit either destroys climate information (grid → region pre-aggregation) or introduces structural artefacts (region-level yield disaggregation).
- MAUP-vulnerability is a Master research-grade concern; committing to a single unit without robustness check is a reviewer-visible gap.

### 3.3 Region-key reconciliation across sources (Phase 02 task)

Three sources use three region-keying conventions:

- **AAGIS shapefile**: 3-digit hierarchical codes (`'121'`, `'322'`).
- **ABARES FDP CSV**: text names (`'NSW Riverina'`, `'QLD Western Downs and Central Highlands'`).
- **ABS Census**: `Region code` integer with different granularities (national / state / SA4 / SA3 / SA2).

Both AAGIS and FDP encode 32 structurally aligned regions but by different keys. Explicit mapping tables required for cross-source joins. Deferred to Phase 02 (`src/processing/region_aggregation.py`).

---

## 4. Temporal strategy

### 4.1 Hybrid temporal design (scope v5 §3.3)

Different phases use different temporal windows, justified per phase:

| Use | Period | Justification |
|---|---|---|
| Climate climatology baseline | 1961–1990 and 1991–2020 | WMO standard reference periods; needed for SPI/SPEI. |
| EVT (Pillar 2) | 1961+ for tmax/tmin/rainfall; 1970+ for evappan-derived indices | Long record for tail-parameter stability. Evappan effective start = 1970 per SILO empirical finding. |
| Climate–yield modelling (Pillars 3-5) | 1990–2024 (35 years) | ABARES FDP earliest year = 1990. Scope v4 originally specified 1980+; v5 §3.3 adjusted. |
| OpenWeather–SILO comparison (Phase 02) | 2022–2024 (3 years) | Cost-containment sample; sufficient for 3-year seasonal-cycle statistical power. |

### 4.2 Temporal alignment across sources (Phase 02 task)

SILO daily (1961–2024) vs ABARES annual (1990–2024, financial year ending) vs ABS 2020-21 cross-section vs OpenWeather daily (2022–2024). Yield modelling window bounded by ABARES (1990+); SPEI bounded by SILO evap_pan (1970+); OpenWeather comparison bounded by the 3-year sample window. Phase 02 §6.2 will implement the alignment.

---

## 5. Reproducibility commitments

### 5.1 Environment

- Python 3.12 (matching Project 4 for portfolio-wide runtime consistency).
- pip + venv (not conda). CPU-only stack. See `docs/project_scope.md` §9 for rationale.
- Environment reproduction: `py -3.12 -m venv .venv && pip install -r requirements.txt`.

### 5.2 Reproducibility level

- **Level 2** (`>=` constraints) during Phases 01–09.
- **Level 3** (pinned metadata) at v1.0 closure per `portfolio_finalisation_playbook.md` §8.

### 5.3 Determinism

- Project-wide seed `SEED = 42` in every script involving stochasticity.
- Multi-threaded BLAS / OpenMP ordering, floating-point summation across pandas versions are the known determinism boundaries.

### 5.4 Data reproducibility

- Data files are gitignored; the manifest is committed. A fresh clone can regenerate every raw and processed dataset by running the ingestion scripts, with the caveat that OpenWeather requires a paid One Call 3.0 subscription and API key.
- API keys stored in `.env` (gitignored), loaded via `python-dotenv`. `.env.example` provides a template.

### 5.5 Determinism boundaries acknowledged

- OpenWeather API responses are deterministic per (lat, lon, date), so re-runs produce identical results modulo API availability.
- SILO retrieval is a one-shot snapshot of the 2026-05-15 vintage.
- ABARES / ABS may refresh their public files; each refresh would invalidate exact reproducibility but leave the qualitative research design intact.

---

## 6. Engineering discipline

### 6.1 First-use dependency rule (scope v5 §11.7)

New runtime library additions to `requirements.txt` are staged in the same commit as the code that introduces them. Phase 01 additions:

- `openpyxl>=3.1` (s07, XLSX reading).
- `python-dotenv>=1.0` (s08, API key loading).
- `pyarrow>=15` (s08, Parquet persistence). Discovered mid-execution when the first Parquet write crashed with ImportError; corrective action documented in `PROJECT_LOG.md` s08 entry as an explicit scope §11.5 adaptive override.

### 6.2 Code-quality tooling

- `black` for auto-formatting (line length 88).
- `ruff` for linting (default rule set E, F).
- `pre-commit` orchestrates both via `.pre-commit-config.yaml`.
- `pyproject.toml` configures both and per-file-ignores E402 for `scripts/phase*.py` (deliberate `sys.path` injection pattern for `from src.*` imports).

### 6.3 Idempotency and atomic persistence

- All ingestion modules are idempotent: re-running skips already-completed items (per-file, per-record, or per-year depending on source).
- All persistence uses atomic write-and-rename (`.part` → final path) to prevent partial-file corruption on interruption.

### 6.4 Notebook discipline

Phase notebooks execute top-to-bottom on a fresh kernel without error. Every figure has an interpretation sentence beneath it. No leftover debug prints or commented-out code.

---

## 7. Phase 02 — Data Quality & Cross-Validation

*Placeholder — this section will be populated at Phase 02 completion. Planned content:*

- Grid-vs-region SILO aggregation consistency check methodology.
- OpenWeather–SILO agreement metrics (RMSE, bias, correlation) at the 10 sampled centroids.
- AAGIS 3-digit code ↔ FDP text name mapping table construction.
- ABARES per-typical-farm ↔ region-total farm-count weighting implementation.
- Cropping-mask threshold sensitivity comparison (t005 vs t010 vs t020).
- ACORN-SAT 18-station-unavailable coverage impact assessment on broadacre-region SILO validation.

---

## 8. Phase 03 — Exploratory Analysis

*Placeholder — this section will be populated at Phase 03 completion. Planned content:*

- Baseline regional climate climatologies (temperature, rainfall, extremes) 1961–present.
- Yield trend and dispersion by AAGIS region.
- Empirical evidence for the optional-crop decision (Sorghum / Cotton).

---

## 9. Phase 04 — Climate Indicator Engineering

*Placeholder — this section will be populated at Phase 04 completion. Planned content:*

- Choice and definition of each indicator: SPI (McKee et al. 1993), SPEI (Vicente-Serrano et al. 2010), EHF (Nairn & Fawcett 2015), GDD (standard agronomy), consecutive dry days, frost days.
- Grid-resolution computation vs region rollup: aggregation formulae and within-region distributional summaries preserved.
- Validation against SILO / BoM published equivalents where available.

---

## 10. Phase 05 — Extreme Value Analysis

*Placeholder — this section will be populated at Phase 05 completion. Planned content:*

- GEV vs POT modelling choice per indicator.
- Threshold selection method for POT (mean residual life plot, parameter stability).
- Return-level estimation with confidence intervals (delta method / bootstrap).
- Grid-level fitting → region rollup aggregation formula.
- Non-stationary EVT: parameter-as-function-of-time specifications; effect-size reporting.

---

## 11. Phase 06 — Climate–Yield Statistical Models

*Placeholder — this section will be populated at Phase 06 completion. Planned content:*

- Panel regression specification: region + year fixed effects, clustered SEs at region level.
- Quantile regression at τ ∈ {0.1, 0.25, 0.5, 0.75, 0.9}.
- Lag structure and non-linear specification choices (piecewise / GAM).
- Robustness suite.

---

## 12. Phase 07 — Machine Learning Models

*Placeholder — this section will be populated at Phase 07 completion. Planned content:*

- Model choice: Random Forest, XGBoost, LightGBM; consideration of quantile gradient boosting.
- Feature engineering from grid-level climate: means, quantiles, extremes preserved.
- Spatial blocked cross-validation vs time-blocked CV.
- SHAP interpretability analysis and comparison to Pillar 3 statistical findings.

---

## 13. Phase 08 — Spatio-Temporal Modeling

*Placeholder — this section will be populated at Phase 08 completion. Planned content:*

- Multilevel model specification (region random effects, year random effects).
- Moran's I diagnostics for spatial autocorrelation.
- Spatial weight matrix construction from grid-level adjacency vs region centroids.
- Comparison to non-spatial baselines.

---

## 14. Phase 09 — Multi-Method Synthesis & Validation

*Placeholder — this section will be populated at Phase 09 completion. Planned content:*

- Method-agreement analysis: side-by-side risk maps, agreement metrics.
- MAUP robustness study: Pillar 3 / 4 re-computed at GRDC zone aggregation.
- Historical-event recovery: Millennium Drought (2001–2009), 2018 drought, notable heatwaves.
- AGFD independent validation: side-by-side maps vs project modelled outputs, agreement metrics, methodological discussion.

---

## 15. Phase 10 — Communication Layer

*Placeholder — this section will be populated at Phase 10 completion. Planned content:*

- README polish targeting recruiter 5-minute scan + engineer 30-minute audit.
- `findings.md` narrative structure and substantive-conclusion framing.
- This `methodology.md` document polished into a stand-alone appendix.
- Optional React dashboard decision (per `docs/project_scope.md` §7.3).

---

## Appendix A — Notation and abbreviations

- **AAGIS**: Australian Agricultural and Grazing Industries Survey (ABARES).
- **AGFD**: Australian Gridded Farm Data (ABARES farmpredict model outputs).
- **AWAP**: Australian Water Availability Project (older gridded product; deprecated).
- **ABARES**: Australian Bureau of Agricultural and Resource Economics and Sciences.
- **ABS**: Australian Bureau of Statistics.
- **ACLUMP**: Australian Collaborative Land Use and Management Program (ABARES).
- **ACORN-SAT**: Australian Climate Observations Reference Network — Surface Air Temperature (BoM).
- **ALUM**: Australian Land Use and Management (classification).
- **ASGS**: Australian Statistical Geography Standard (ABS).
- **BoM**: Bureau of Meteorology.
- **CAR / SAR**: Conditional / Simultaneous Autoregressive (spatial models).
- **CRS**: Coordinate Reference System.
- **CV**: Cross-Validation.
- **EHF**: Excess Heat Factor (heatwave indicator, Nairn & Fawcett).
- **EVT**: Extreme Value Theory.
- **FDP**: Farm Data Portal (ABARES).
- **GDD**: Growing Degree Days.
- **GEV**: Generalised Extreme Value distribution.
- **GPD**: Generalised Pareto Distribution.
- **GRDC**: Grains Research and Development Corporation (agro-ecological zones as MAUP alternative).
- **MAUP**: Modifiable Areal Unit Problem.
- **POT**: Peaks Over Threshold (EVT).
- **RSE**: Relative Standard Error.
- **SA2 / SA3 / SA4**: Statistical Area levels 2 / 3 / 4 (ABS ASGS).
- **SHAP**: SHapley Additive exPlanations (interpretability method).
- **SILO**: Long Paddock daily gridded climate data (Queensland Government).
- **SPI**: Standardised Precipitation Index (McKee et al.).
- **SPEI**: Standardised Precipitation–Evapotranspiration Index (Vicente-Serrano et al.).
- **WMO**: World Meteorological Organization.

---

## Appendix B — Document history

| Date | Change |
|---|---|
| 2026-07-10 | Skeleton created at Phase 01 s09 closure. Sections 1–6 populated with Phase 01 decisions; sections 7–15 are placeholders for Phase 02–10 expansion. |

*End of methodology.md.*
