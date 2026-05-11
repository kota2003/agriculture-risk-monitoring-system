# Project 5 — Project Scope (v3)

**Repo / project codename:** `agriculture-risk-monitoring-system`
**Formal title:** *Agriculture Risk Monitoring System: A Multi-Method Research Framework for Australian Broadacre Cropping*
**Short title:** P5 — Agriculture Risk Monitoring System
**Author:** Kota
**Last updated:** 2026-05-11
**Document status:** Phase 00 deliverable. Replaces `p5_ProjectScope_v2.md` (v2) and `p5_ProjectScope.md` (v1).
**GitHub:** https://github.com/kota2003/agriculture-risk-monitoring-system

---

## 1. Identity and Purpose

### 1.1 One-sentence purpose

Build a research-grade analytical framework for monitoring agricultural risk in Australian broadacre regions, by quantifying how climate extremes translate into production risk using six methodologically distinct approaches (climate indicator engineering, extreme value theory, statistical climate–yield models, machine learning, spatio-temporal modelling, and multi-method synthesis) over an integrated dataset assembled from authoritative public sources.

The framework is the substantive deliverable; an interactive monitoring layer (dashboard) is an optional final-phase output that surfaces results from the framework.

### 1.2 Portfolio positioning

This is a **research-depth-first** portfolio project. Its substantive contribution is a defensible, literature-grounded characterization of Australian climate–agriculture risk; its methodological contribution is a side-by-side comparison of how different families of methods quantify that risk. The "Monitoring System" naming reflects the project's intended use — surfacing risk signals across regions and time — while the analytical core remains a multi-method research framework.

**Framing evolution.** The project was initially scoped (v1) as an operational monitoring system built on a single commercial weather API and rule-based scoring. During Phase 00 scoping, the framing was refined (v2) to a research-depth-first multi-method investigation. v3 reconciles the two by treating the multi-method analytical framework as the core deliverable and positioning any monitoring/dashboard layer as a communication surface for it. The shift is recorded for honesty (no hidden pivots) and is itself a portfolio signal of scoping discipline.

It is intentionally complementary to Project 4 (panel econometrics on education and income inequality):

- **Project 4** signal: depth in causal-leaning panel methods within a single methodological family.
- **Project 5** signal: methodological breadth + integration, plus production-grade engineering of an end-to-end research framework that can power a monitoring layer.

Together, the two projects span "depth in one method" and "breadth across methods," which is a stronger portfolio shape than two single-method projects.

### 1.3 Target audience

In approximate order of priority:

1. **Hiring managers** in data science / quantitative research roles (industry, agritech, climate analytics, public policy quantitative teams).
2. **Academic / research evaluators** considering the candidate for research-adjacent roles or further study.
3. **Domain readers** in climate impact, agricultural economics, or climate risk.
4. **Engineers** auditing reproducibility, code quality, and pipeline design.

### 1.4 Aspirational outcome

A successful execution of this scope produces a body of work consistent with a **working paper** suitable for a workshop submission or extended methodological note. This is an aspiration, not a success criterion (see §8).

---

## 2. Research Framing

### 2.1 Central research question

> *How do climate extremes translate into agricultural production risk across Australian broadacre regions, and how do different methodological families compare in their characterization of that risk?*

### 2.2 Sub-questions

1. **Indicator design.** Which literature-grounded climate extreme indicators (drought, heat, frost) most cleanly track yield variation in Australian broadacre regions?
2. **Extremity.** What are the regional return periods of key climate extremes, and is there evidence of non-stationarity (climate-change signal in distributional parameters)?
3. **Climate–yield linkage.** What is the statistical relationship between climate indicators and yield outcomes — both at the mean and in the lower tail (= "risk")?
4. **Methodological agreement.** Where do statistical, machine learning, and spatial–hierarchical methods agree in their risk characterizations, and where do they diverge?
5. **Validation.** How well does each method recover known historical drought / heatwave events as high-risk?
6. **Data validation (auxiliary).** How does a commercial weather API (OpenWeather) compare to the gold-standard scientific dataset (SILO) when used as the climate input layer?

### 2.3 Substantive contribution

A regional, multi-decadal characterization of climate-induced agricultural risk in Australian broadacre cropping, with explicit uncertainty quantification and honest reporting of where methods disagree.

### 2.4 Methodological contribution

A side-by-side application of six methodological families to a single integrated dataset, allowing direct comparison of how methodological choice shapes risk conclusions. This addresses a gap in the climate-impact literature where methods are typically applied in isolation.

### 2.5 Explicit non-claims

This project does **not** claim:

- **Causal identification** in the strong econometric sense. Climate variation is plausibly exogenous to farmer decisions at relevant timescales, but the project will not invoke instrumental variables or natural experiments. Claims will be expressed as "associational with mechanistic plausibility."
- **Predictive operational use.** Any forecasting framing is exploratory and should not be interpreted as a deployable early-warning system.
- **Coverage of irrigated, horticultural, or pastoral systems.** The project is scoped to rainfed broadacre crops (see §3.2).
- **National-level aggregate results.** Findings are regional; aggregating to a single national risk score is explicitly out of scope.

---

## 3. Scope Boundaries

### 3.1 Geographic

**Australia**, partitioned into **ABARES regions** (~60 regions) as the primary spatial unit. SA2 (~2,300 ABS Statistical Areas Level 2) is the secondary unit, used where ABS Census data is the only available source.

State / territory aggregation will be reported descriptively only, not modeled at.

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
| Climate indicators | Monthly / seasonal aggregations | As required by each indicator's literature definition |
| Yield / agricultural | Annual | ABARES / ABS Census native |
| Risk outputs | Annual, region-level | Match yield layer |

### 3.5 Out-of-scope items (explicit)

- Real-time / near-real-time monitoring (the auxiliary OpenWeather comparison touches this, but operational deployment is not a goal)
- Economic translation (yield risk → farm income / commodity price impact)
- Adaptation / policy recommendation
- Future climate projections (CMIP / regional climate models)
- Crop-model simulation (e.g., APSIM)

These are mentioned in "future work" sections of deliverables but not pursued.

---

## 4. Data Sources

### 4.1 Primary climate data

**SILO** (Queensland Department of Agriculture and Fisheries)

- **Type:** Daily gridded (~5 km / 0.05°) interpolated weather data, Australia-wide.
- **Period:** 1889–present; project uses 1961–present.
- **Variables planned:** maximum temperature, minimum temperature, daily rainfall, vapour pressure, evaporation, solar radiation.
- **Access:** SILO HTTPS API (point queries by lat/lon, or LongPaddock-style data drill).
- **Status:** widely used in peer-reviewed Australian climate research.
- **Computational note:** full-grid retrieval would be ~100+ GB across variables and years; project will use **point-data API queries at ABARES region centroids and selected representative grid points**, then aggregate. Decision in Phase 01.

### 4.2 Climate quality reference

**BoM ACORN-SAT** (Bureau of Meteorology)

- **Type:** Homogenised station-level long-term temperature record, ~112 stations.
- **Use:** Sanity-check SILO regional aggregates against ACORN-SAT station records to confirm SILO regional means are physically plausible.
- **Access:** BoM data portal.

### 4.3 Agricultural production data

**ABARES** (Australian Bureau of Agricultural and Resource Economics and Sciences)

- Regional commodity statistics: annual area, production, yield by ABARES region for major crops.
- AgSurf farm survey indicators (financial / operational, optional secondary use).

**ABS Agricultural Census**

- 5-yearly, SA2-level. Used for region-importance weighting and structural snapshots, not as a time-series.

### 4.4 Validation / auxiliary

**OpenWeather API** (Historical Weather)

- **Type:** Commercial API, historical observation + reanalysis blend.
- **Use:** *Validation target.* Compare OpenWeather output against SILO at a sample of ABARES region centroids over the API's available historical window. The result is a methodological contribution in itself: how does a popular commercial API compare to the scientific gold standard?
- **Access:** API key required; subject to rate limits and historical-window constraints.

### 4.5 Licensing and attribution

All sources are public or accessible via free / inexpensive API tiers. License terms will be:

- Recorded in `data/raw/manifest.yaml` per source.
- Acknowledged in the README and `methodology.md`.
- Respected in distribution: data files themselves are gitignored except for the manifest and small derived summaries; the project distributes scripts to retrieve data, not the data itself (consistent with playbook §5 "reproduce-from-code" default).

### 4.6 Manifest plan

`data/raw/manifest.yaml` will document, for each source:

- Canonical name, version / vintage, retrieval URL, retrieval date
- Field dictionary (variable names, units, encoding)
- License and attribution
- Known quirks (e.g., encoding issues, NA-handling requirements per playbook lesson 9)

---

## 5. Methodological Pillars

Each pillar is implementable as an independent contribution; together they form the multi-method synthesis.

### 5.1 Pillar 1 — Climate Indicator Engineering

Implement literature-grounded climate-extreme indicators rather than bespoke ad-hoc constructions.

| Indicator | Source | What it captures |
|---|---|---|
| **SPI** (Standardised Precipitation Index) | McKee et al. (1993); WMO | Precipitation-only drought |
| **SPEI** (Standardised Precipitation–Evapotranspiration Index) | Vicente-Serrano et al. (2010) | Drought accounting for evaporative demand |
| **EHF** (Excess Heat Factor) | Nairn & Fawcett (2015); BoM operational definition | Heatwave intensity |
| **GDD** (Growing Degree Days) | Standard agronomy | Heat accumulation for crop development |
| **Consecutive dry days** | Standard climate-extreme literature | Drought event duration |
| **Frost days** | Standard | Cold-side risk |

Outputs: indicator time series per ABARES region, validated against SILO/BoM published equivalents where available.

### 5.2 Pillar 2 — Extreme Value Analysis

Apply EVT to characterize the tails of climate-extreme distributions.

- **GEV (Generalized Extreme Value)** distribution fitted to annual block maxima of relevant indicators (e.g., annual maximum heatwave intensity, annual maximum consecutive dry days).
- **GPD (Generalized Pareto Distribution)** fitted to peaks-over-threshold; threshold selection by mean residual life plot and parameter stability.
- **Return level estimates** with confidence intervals (delta method / bootstrap).
- **Non-stationary EVT**: location and / or scale parameters as functions of time, to test for distributional change. Reported with appropriate uncertainty given the difficulty of detecting tail-parameter trends.

This pillar exists because the project frames itself around *extremes*. Failing to apply EVT to a project titled "Climate Extremes" would be a reviewer-visible gap.

### 5.3 Pillar 3 — Climate–Yield Statistical Models

Establish associational links between climate indicators and yields.

- **Panel regression** with region and year fixed effects (continuity with Project 4 methodology).
- **Quantile regression** at multiple quantiles (τ = 0.1, 0.25, 0.5, 0.75, 0.9). The risk-relevant findings live in the lower quantiles of yield, not the mean.
- **Lag and non-linear specifications**: piecewise / GAM where the climate–yield relationship is empirically non-linear (e.g., temperature thresholds).
- **Robustness**: clustered standard errors at the region level; specification curve where appropriate.

### 5.4 Pillar 4 — Machine Learning Models

Provide ML benchmarks and interpretability analyses.

- **Models**: Random Forest, XGBoost, LightGBM at minimum; consideration of quantile gradient boosting to match Pillar 3's quantile focus.
- **Validation**: spatial blocked cross-validation (random K-fold leaks information across nearby regions); time-blocked cross-validation as an alternative.
- **Interpretability**: SHAP value analysis (continuity with Project 4); partial dependence plots.
- **Comparison**: ML vs. Pillar 3 statistical models — does ML find structure the statistical models miss, or does it merely overfit?

### 5.5 Pillar 5 — Spatio-Temporal / Hierarchical Modeling

Account for spatial and hierarchical structure that standard panel methods ignore.

- **Multilevel models**: region random effects (intercepts, possibly slopes), year random effects.
- **Spatial autocorrelation diagnostics**: Moran's I on residuals from Pillar 3 / 4 models.
- **Spatial smoothing** (if warranted): Gaussian-process regression or CAR/SAR models. Decision based on Phase 03 EDA evidence of spatial autocorrelation.

### 5.6 Pillar 6 — Multi-Method Synthesis

Cross-method comparison.

- **Risk maps** from each method, presented side-by-side for the same region-year cells.
- **Method-agreement analysis**: where do methods agree on high-risk classifications, and where do they diverge? Is divergence systematic (e.g., particular regions, particular years)?
- **Out-of-sample validation**: do the methods successfully identify historically known high-risk events (e.g., the Millennium Drought 2001–2009, 2018 drought)?
- **Auxiliary**: OpenWeather vs. SILO comparison results presented as a methodological side-finding.

---

## 6. Phase Plan

11 phases, numbered `phase00` through `phase10`. Each phase has a goal, deliverables, and an exit criterion. Phase numbering is fixed; phase ordering is sequential except where noted.

### 6.1 Summary table

| # | Title | Pillar | Goal |
|---|---|---|---|
| 00 | Scope & Setup | — | Lock design and environment |
| 01 | Data Acquisition | — | Reproducible API ingestion |
| 02 | Data Quality & Cross-Validation | (P1, P6 aux.) | Verify integrity; OpenWeather–SILO comparison |
| 03 | Exploratory Analysis | — | Spatial-temporal patterns of climate and yields |
| 04 | Climate Indicator Engineering | P1 | Compute literature-grounded indicators |
| 05 | Extreme Value Analysis | P2 | EVT on climate indicators; return periods |
| 06 | Climate–Yield Statistical Models | P3 | Panel + quantile regression linkage |
| 07 | Machine Learning Models | P4 | ML benchmarks + SHAP |
| 08 | Spatio-Temporal Modeling | P5 | Hierarchical / spatial structure |
| 09 | Multi-Method Synthesis & Validation | P6 | Cross-method comparison + historical validation |
| 10 | Communication Layer | — | README polish, findings.md, methodology.md, optional dashboard |

### 6.2 Phase detail

#### Phase 00 — Scope & Setup

- **Goal:** Lock down project design and reproducible environment.
- **Deliverables:** This `project_scope.md`; `requirements.txt` + `requirements-dev.txt`; initial repo structure; initial PROJECT_LOG.md entry; PROJECT_WORKFLOW.md instantiation.
- **Exit criterion:** Scope approved; environment reproducible (`py -3.12 -m venv .venv && pip install -r requirements.txt` works on a fresh Windows machine; on macOS/Linux, the equivalent is `python3.12 -m venv .venv && pip install -r requirements.txt`).

#### Phase 01 — Data Acquisition

- **Goal:** Reproducible retrieval of SILO, BoM ACORN-SAT, ABARES, ABS Census, OpenWeather data.
- **Deliverables:** Per-source ingestion scripts in `src/ingestion/`; populated `data/raw/`; `data/raw/manifest.yaml`; basic ingestion sanity-check notebook.
- **Exit criterion:** Every source retrievable from scratch via documented script, reproducing the same files (or files matching a documented hash up to known floating-point variation).

#### Phase 02 — Data Quality & Cross-Validation

- **Goal:** Quantify and document data integrity issues; complete OpenWeather vs. SILO comparison study.
- **Deliverables:** Data quality report; OpenWeather–SILO agreement metrics (by variable, by region); cross-validation notebook.
- **Exit criterion:** Quality issues resolved or explicitly flagged with downstream-handling strategy; OpenWeather–SILO comparison written up as a self-contained mini-study.

#### Phase 03 — Exploratory Analysis

- **Goal:** Establish baseline empirical understanding of climate and yield variation.
- **Deliverables:** EDA notebook; key visualizations (regional climate climatologies, yield trends and dispersions); decision on optional crops (Sorghum / Cotton).
- **Exit criterion:** Clear narrative of where, when, and how much climate and yield variation occurs; reader can describe Australian broadacre regions in 2 paragraphs based on this notebook.

#### Phase 04 — Climate Indicator Engineering

- **Goal:** Implement and validate literature-grounded climate extreme indicators.
- **Deliverables:** `src/climate_indicators.py`; indicator notebook with validation against published equivalents where possible; per-region indicator time series in `data/processed/`.
- **Exit criterion:** SPI, SPEI, EHF, GDD, consecutive dry days, frost days computed, validated, and persisted.

#### Phase 05 — Extreme Value Analysis

- **Goal:** Apply EVT to climate extremes, estimate return periods, test stationarity.
- **Deliverables:** GEV / POT models per region × indicator; return level maps; non-stationary EVT extension; diagnostic plots.
- **Exit criterion:** Return periods estimated with appropriate diagnostics; non-stationary results reported with honest uncertainty.

#### Phase 06 — Climate–Yield Statistical Models

- **Goal:** Establish associational climate–yield links via panel and quantile methods.
- **Deliverables:** Panel regression results; quantile regression at multiple τ; non-linear / lag specifications; robustness suite.
- **Exit criterion:** Findings reportable with clustered SEs and appropriate caveats.

#### Phase 07 — Machine Learning Models

- **Goal:** ML benchmarks and interpretability analysis.
- **Deliverables:** Trained models (or training scripts producing them — track-vs-reproduce decision per playbook §7); SHAP analysis; performance comparison vs. Phase 06.
- **Exit criterion:** ML results validated under spatial / time-blocked CV; interpretability narrative aligns with statistical findings or divergence is explained.

#### Phase 08 — Spatio-Temporal Modeling

- **Goal:** Account for spatial autocorrelation and hierarchical structure.
- **Deliverables:** Multilevel model fits; Moran's I diagnostics; spatial residual analysis; comparison to non-spatial baselines.
- **Exit criterion:** Spatial structure properly accounted for; residuals show no remaining systematic spatial pattern (or remaining pattern explicitly flagged).

#### Phase 09 — Multi-Method Synthesis & Validation

- **Goal:** Compare risk quantifications across pillars 1–5; validate against historical events.
- **Deliverables:** Synthesis notebook; multi-method risk maps; method-agreement analysis; historical-event validation report.
- **Exit criterion:** Cross-method agreement quantified; major historical drought / heatwave events recovered as high-risk by majority of methods, or non-recovery explained.

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
| 00–02 (foundation) | 2–4 |
| 03–04 (EDA + indicators) | 3–5 |
| 05 (EVT) | 2–4 |
| 06 (Statistical) | 3–5 |
| 07 (ML) | 2–4 |
| 08 (Spatio-temporal) | 2–4 |
| 09–10 (synthesis + close) | 3–5 |
| **Total** | **17–31 weeks** (≈ 4–8 months) |

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
- `src/*.py` — reusable modules
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

**Rationale.** The project does not require GPU compute. Pillars 1–3, 5, 6 are CPU-bound by design (statistical / EVT / spatial / synthesis). Pillar 4 (XGBoost, LightGBM, RandomForest) runs on CPU within minutes given the ABARES region × 1980+ sample size. Choosing pip+venv over conda yields a simpler, more transparent, and more recruiter-reproducible environment, at the deliberate cost of foregoing GPU acceleration for Pillar 4 and any Bayesian Pillar 5 extensions.

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

### 9.6 Spatial

- geopandas, shapely, pyproj
- libpysal (Moran's I and spatial weights)
- optionally: pymc or numpyro for Bayesian hierarchical models (CPU sampling; performance considerations apply)

### 9.7 Visualization

- matplotlib, seaborn for static figures
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

- **Quantile regression at extreme quantiles** (τ = 0.05, 0.95) is unstable with small samples. Use τ ∈ [0.1, 0.9] as defaults; report tail estimates as exploratory.
- **Non-stationary EVT** trend detection has notoriously low statistical power. Report effect sizes alongside hypothesis tests; do not over-interpret marginal significance.
- **Spatial models** require a defensible spatial weights matrix; arbitrary choices can drive results. Multiple weight specifications will be tested.
- **ML overfitting risk** to weather × region interactions. Spatial blocked CV is the primary defense; performance gap between spatial CV and naive CV is itself a reportable diagnostic.

### 12.2 Data

- **OpenWeather historical window** may be too short for some validation goals; the OpenWeather–SILO comparison may be confined to recent years only.
- **ABARES regional yield data** has known structural breaks (region boundary changes). Document and either harmonize or restrict analysis to stable-boundary periods.
- **SILO interpolation quality** degrades in remote / station-sparse regions (e.g., far-western pastoral zones). Project's restriction to broadacre cropping mitigates this since cropping zones have denser station coverage, but the issue is acknowledged.
- **Pre-1980 yield data** is non-comparable; restricting yield-linkage analysis to 1980+ is a deliberate concession.

### 12.3 Engineering

- **SILO data volume**. Mitigation: point-data API queries at region centroids, not full-grid downloads (§4.1).
- **Compute limits** for hierarchical Bayesian models. Mitigation: start with frequentist multilevel models (statsmodels / pymer4); escalate to Bayesian only if needed.
- **Memory / chat handoffs**. Mitigation: PROJECT_WORKFLOW §10 phase summary protocol; expect 2–3 chat handoffs within larger phases.

### 12.4 Scope

- **Crop coverage scope drift**. Adding sorghum / cotton mid-project is tempting but methodologically expensive (irrigation regime differs). Defer to Phase 03 decision (§3.2).
- **Dashboard scope drift**. Decision is deferred (§7.3). Resist mid-project React build-out unless it directly serves communicating findings.

---

## 13. Flexibility Clause

This Scope reflects current best understanding as of 2026-05-09. It is expected — and welcome — that some elements will need revision as the project encounters reality:

- **Substantive findings may redirect emphasis.** If Phase 03 EDA reveals that a particular crop or region exhibits the cleanest signal, downstream phases may concentrate there.
- **Methodological choices may change.** If Phase 06 finds that quantile regression is unstable at the available sample sizes, alternative tail-modeling approaches will be considered.
- **Phases may split or merge.** If a phase grows too large for one chat, it is split per PROJECT_WORKFLOW §9.3. If two phases naturally converge, they may be merged with a PROJECT_LOG entry recording the change.
- **Optional pillars / crops / deliverables** (Pillar 5 spatial, optional crops, dashboard) are explicitly subject to deferral or omission with logged rationale.

What is **not** flexible:

- The research framing (multi-method climate–agriculture risk in Australian broadacre).
- The reproducibility and engineering standards.
- The honesty conventions (no hidden overrides, explicit non-claims, calibrated uncertainty).

Revisions to this Scope are versioned (`p5_ProjectScope_v3.md`, etc.) with a PROJECT_LOG entry summarizing the change.

---

## Appendix A — Initial Repo Structure

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
│   │   ├── abares.py
│   │   ├── abs_census.py
│   │   └── openweather.py
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── quality_checks.py
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
│   ├── phase01_s01_silo_ingest.py
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
| v3 | 2026-05-11 | This document. (a) Formal title and codename aligned with GitHub repo `agriculture-risk-monitoring-system`; framing reconciled as research framework that can power a monitoring layer. (b) Tech stack switched from conda hybrid to pip + venv, CPU-only; GPU support intentionally dropped. (c) Code quality tooling (black + ruff + pre-commit) and committed `.vscode/settings.json` added to conventions. (d) Repo structure, document history, and tag-message convention updated to match. (e) Python version corrected from 3.11 → **3.12** to match Project 4's runtime and preserve portfolio-wide consistency (in-conversation amendment, same date). |

---

*End of Project Scope v3.*
