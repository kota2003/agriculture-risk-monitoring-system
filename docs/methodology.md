# Methodology

*Agriculture Risk Monitoring System — Master research-grade portfolio project*

**Last updated:** 2026-07-19 (Phase 03 s06 closure)
**Status:** Progressive document — Sections 1–8 (Phases 01–03) are populated; Sections 9–15 (Phases 04–10) are placeholders that will be filled as each phase executes.
**Companion documents:** `docs/project_scope.md` (v5.2); `PROJECT_LOG.md` (append-only decision log); `data/raw/manifest.yaml` (data provenance).

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

Phase 02 reconciled Phase 01's raw data into analysis-ready inputs and cross-validated the sources before any Pillar analysis. Modules live in `src/processing/`; each is driven by a `scripts/phase02_s0X_*.py` orchestrator and covered by tests.

### 7.1 Region-key mapping (Task A)

The AAGIS GeoPackage carries both a 3-digit `class` code and a text `name`; the `name` values match the ABARES FDP `ABARES region` column exactly (32/32, zero orphans). The mapping (`region_aggregation.py`) is therefore read directly from the shapefile and validated (code well-formedness, `aagis == class` redundancy, state-prefix sanity, and name-set equality with the FDP). A latent Phase 01 diagnostic bug — `cross_check_aagis_region_names` selected the numeric code column instead of `name`, so it never validated name equality — was fixed (s03).

### 7.2 Per-typical-farm → region-total weighting (Task B)

ABARES FDP `Value` columns are per-typical-farm averages (Phase 01 finding #2). Extensive quantities (sown area, production) are converted to region totals by multiplying by the FDP **`Population`** variable (the survey's estimate of broadacre farms per region-year); `yield_t_ha` needs no weighting. `Population` was chosen over ABS Census SA2 counts because it is region-native, per-year, and internally exact: Σ_region(per-farm × Population) reconstructs the FDP national total to ratio 0.999–1.001.

**Survey-reliability RSE gate.** The ±5% reconstruction check is applied only to full-coverage years whose FDP national production RSE ≤ 20%. This operationalises the "survey-error tolerance" qualifier: early canola (1990–1993, RSE 22–88%, integer-rounded to 1–3 t/farm) is excluded. Consequently **canola's reliable yield window begins 1994** (wheat/barley 1990+; scope v5.1 §3.3).

### 7.3 SILO grid → region aggregation and the masking-flip fix (Task C)

Region climatologies are cos(latitude)-area-weighted means over each region's cropping cells (`silo_region_aggregation.py`); cell→region assignment is a cached point-in-polygon join, and grid indices are resolved by coordinate value (robust to axis ordering).

**Phase 01 s04 latitude-flip bug (found and fixed here).** `silo.py` had applied the cropping mask via a positional `assign_coords`; because the mask is latitude-descending and SILO data ascending, the mask was flipped north-south (only 7.9% of cropping cells retained data — WA wheat-belt sampled the Pilbara, Tasmania the tropical ocean). The fix aligns the mask by coordinate value (`reindex(method="nearest")`) and adds an `_assert_masking_sane` guard (latitude-centroid check, fail-fast). The full SILO archive (375 files, 13.38 GB) was regenerated from source.

### 7.4 Grid-vs-region consistency check (Task C, s04b)

Primary check is INTERNAL and fully reproducible: coverage/no-NaN, strong temperature–latitude correlation (corr(lat, tmax) = +0.887, tmin = +0.938), and the correct rainfall seasonality regime (Mediterranean-south winter-dominant → subtropical/monsoon-north summer-dominant). A SECONDARY external plausibility check compares region means to representative BoM station normals (Mildura, Merredin, Wagga; cited) — a region mean is expected to fall within the spread of in-region stations, not equal any one.

### 7.5 ACORN-SAT coverage impact (Task E)

The 112 ACORN-SAT stations (94 available / 18 unavailable) are assigned to AAGIS regions; broadacre regions with zero or a single available station are flagged as under-represented for direct SILO validation. QLD Eastern Darling Downs has no available station; four regions are sparse. The three broadacre-relevant unavailable stations degrade WA Wheatbelt (521/522) and NSW Central West (122).

### 7.6 OpenWeather–SILO comparison (Task D; scope §5.6.4)

Daily OpenWeather day-summary records are paired with SILO at the nearest cropping cell to each of the 10 centroids (2022–2024); tmax/tmin/rain compared directly, humidity via SILO-derived RH (Tetens, approximate). Bias = OpenWeather − SILO. OpenWeather tracks SILO temperature well (tmax corr 0.97, RMSE 1.9 °C; tmin corr 0.92, RMSE 2.6 °C; ~1–2 °C diurnal-range compression) but daily rainfall agreement is weak (corr 0.33) though unbiased — supporting SILO as the primary climate input and OpenWeather as a validation comparator only.

---

## 8. Phase 03 — Exploratory Analysis

Phase 03 established the baseline empirical understanding of climate and yield variation across the 20 AAGIS broadacre regions and resolved the optional-crop decision. Products live in `src/processing/` (`input_inventory`, `silo_climatology`, `yield_stats`, `climate_yield`, `optional_crops`) and `src/viz/` (`style`, `maps`), driven by `scripts/phase03_s0X_*.py` and rendered in `notebooks/03_exploratory_analysis.ipynb`. All statistics are descriptive; inference is Phases 05–06 and formal event validation is Phase 09.

### 8.1 Data inventory & EDA scaffolding (s01)

Verified the Phase 02 analysis-ready inputs — shapes, region-key alignment across the yield (region name) and climate (`aagis_code`) products, and joint presence of the 20 broadacre regions. Established the project's first notebook and a single visual system (Okabe-Ito colourblind-safe categorical, assigned in fixed order; single-hue sequential for magnitude; `RdBu_r` diverging with a neutral midpoint for signed change).

### 8.2 Regional climate climatology (s02)

**Decision (gate ①):** re-aggregate SILO region means over the FULL record (1961–2024; evap_pan 1970–2024) rather than align to the yield window — the full daily archive is already on disk, the superset serves both the EDA and later Pillar 2 EVT reuse, and it enables both WMO baselines. The monthly climatology is kept at 1991–2020 (seasonality is baseline-insensitive). Findings: max temperature rises in all 20 broadacre regions (~+0.2 °C/decade; +0.61 °C median between the 1961–1990 and 1991–2020 baselines); annual rainfall falls in all 20 (median −6.6%); interannual rainfall variability is highest in the dry interior/Mallee (CV up to 0.31) and lowest in the Mediterranean south-west (0.14); rainfall is winter-dominant in the south/west and summer-dominant in QLD. The evap_pan 1961–1990 baseline necessarily uses 1970–1990.

### 8.3 Yield trends & dispersion (s03)

**Decision (gate ②):** diagnostic-only — the survey RSE is reported as a data-quality caveat, not used to weight the descriptive statistics; inverse-RSE weighting is deferred to the Phase 06 regression models. Dispersion uses the *detrended* CV so the rising yield trend does not inflate the variability measure; regions with fewer than 10 reliable years (marginal High-Rainfall croppers) are flagged rather than mixed in. Findings: yields rise in ~17/19 adequate regions per crop (~+0.2–0.26 t/ha/decade) despite the warming-and-drying climate; lower-tail risk is large (a 1-in-10 year is ~45–60% of the regional median); detrended yield variability is lowest in the WA/SA wheat-belt (~0.20) and highest on the eastern/coastal margin (~0.84) — the same geography as rainfall variability.

### 8.4 Climate–yield linkage & historical-event sanity (s04)

Both yield and climate are detrended per region before correlating, so the strong yield trend and the climate trend cannot manufacture a spurious linkage. **Key result:** annual, region-aggregated climate is a weak year-to-year predictor of yield — detrended corr(annual rainfall, yield) median ≈ −0.04 (negative in the WA wheat-belt / TAS, where water is not limiting and annual totals mix in non-growing-season rain); corr(tmax, yield) weakly negative, strongest for canola (−0.22, heat sensitivity). This is the phase's principal methodological driver: it **empirically motivates the Pillar 1 growing-season / water-balance (SPI, SPEI) and heat (EHF, GDD) indicators (Phase 04)**, not merely methodological completeness. Across regions, rainfall CV vs yield detrended-CV is positive but modest (+0.31 wheat to +0.44 canola) — climate variability shapes the risk map without determining it. **Event sanity (gate ③ = A+):** droughts recover cleanly as below-trend yield (Millennium Drought 2001–2009, 2018), but the 2013/2017 heat label does not, because a single-year annual-temperature label misses flowering-time heat stress. Formal cross-pillar event validation remains Phase 09.

### 8.5 Optional-crop decision (s05)

**Decision (gate ④):** exclude both. **Cotton** on data grounds — the FDP regional file carries only `Cotton receipts ($)` (no area/production/yield), so a region-level yield-risk analysis is impossible; cotton is also irrigated, outside the rainfed-broadacre framing. **Sorghum** deferred to future work — yield is derivable (production ÷ area) but only 6 broadacre regions clear the 10-year bar (all QLD/N-NSW summer belt), median production RSE ~45 vs 19–32 for the core crops, and as a summer crop it would require its own Pillar 1 growing-season indicators. The binding data constraint is the fixed ~20 broadacre AAGIS regions × ~35 years (crop-independent); sorghum adds neither regions nor years, so crop coverage is locked to wheat/barley/canola for v1.0, with sorghum recorded as a summer-crop companion study for after the Phase 04 indicators exist.

### 8.6 Data quality (as characterised by the EDA)

Climate (SILO) is high and validated — full record, zero NaN after the Phase 02 masking fix, physically coherent signals; the only caveats are localized ACORN-SAT validation gaps (QLD Eastern Darling Downs no station + 4 sparse broadacre regions) and evap_pan starting 1970. Yield (ABARES) is moderate and survey-limited — substantial production RSE (median 19 wheat to 32 canola, p90 ~60) and sparse coverage in marginal High-Rainfall coastal regions; the core Wheat-Sheep regions with full 35-year series are reliable. The mixed-resolution design (grid climate → region yield) is the deliberate response to the region-limited yield data, and is sufficient for the multi-method pillars — Pillar 4 (ML, ~650 wheat samples) being the tightest, mitigated by spatial-blocked cross-validation.

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
| 2026-07-17 | Section 7 (Phase 02) populated at the Phase 02 closure ceremony (region mapping, Population weighting + RSE gate, SILO masking fix, grid-vs-region consistency, ACORN-SAT coverage, OpenWeather–SILO). |
| 2026-07-19 | Section 8 (Phase 03) populated at the s06 closure ceremony; header status and companion scope version (v5.2) updated. |

*End of methodology.md.*
