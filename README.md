# Agriculture Risk Monitoring System

*A Multi-Method Research Framework for Australian Broadacre Cropping*

_Last updated: 2026-07-19 — Phase 03 complete (`v0.3-phase03-complete`)_

## Overview

This project quantifies how climate extremes translate into agricultural production risk across Australian broadacre regions, comparing six methodologically distinct approaches: climate indicator engineering, extreme value theory, statistical climate–yield models, machine learning, spatio-temporal modeling, and multi-method synthesis.

The framework is research-depth-first; an interactive monitoring layer (dashboard) is an optional final-phase output.

## Research Questions

1. Which literature-grounded climate extreme indicators (drought, heat, frost) most cleanly track yield variation in Australian broadacre regions?
2. What are the regional return periods of key climate extremes, and is there evidence of non-stationarity?
3. What is the statistical relationship between climate indicators and yield outcomes — both at the mean and in the lower tail (= "risk")?
4. Where do statistical, machine learning, and spatial–hierarchical methods agree in their risk characterizations, and where do they diverge?
5. How well does each method recover known historical drought / heatwave events as high-risk?
6. How does a commercial weather API (OpenWeather) compare to the gold-standard scientific dataset (SILO) when used as the climate input layer?

## Data Sources

| Source | Role | Coverage |
|---|---|---|
| **SILO** (Queensland DAF) | Primary climate (gridded daily, ~5km) | 1961–present |
| **BoM ACORN-SAT** | Homogenised long-term temperature reference | 1910–present |
| **ABARES** | Regional crop production statistics | 1990–present |
| **ABS Agricultural Census** | Region structure / weighting (SA2 level) | 5-yearly |
| **OpenWeather API** | Validation comparator (vs SILO) | 2022–2024 sample |

## Tech Stack

- **Python 3.12** (CPU-only stack)
- **Environment:** pip + venv
- **Core:** pandas, numpy, requests, pyyaml
- **Spatial / raster:** xarray, netCDF4, rasterio, geopandas, shapely, pyproj
- **Visualization:** matplotlib, seaborn
- **Statistical / EVT (later phases):** statsmodels, linearmodels, scipy.stats, pyextremes
- **Machine learning (later phases):** scikit-learn, xgboost, lightgbm, shap
- **Code quality:** black, ruff, pre-commit

_Libraries are added Phase-by-Phase; see `requirements.txt` for the current runtime dependency set._

## Project Status

| Phase | Title | Status |
|---|---|---|
| Phase 00 | Scope & Setup | ✅ Complete |
| Phase 01 | Data Acquisition | ✅ Complete |
| Phase 02 | Data Quality & Cross-Validation | ✅ Complete |
| Phase 03 | Exploratory Analysis | ✅ Complete |
| Phase 04 | Climate Indicator Engineering | ⏭️ Next |
| Phase 05 | Extreme Value Analysis | Planned |
| Phase 06 | Climate–Yield Statistical Models | Planned |
| Phase 07 | Machine Learning Models | Planned |
| Phase 08 | Spatio-Temporal Modeling | Planned |
| Phase 09 | Multi-Method Synthesis & Validation | Planned |
| Phase 10 | Communication Layer | Planned |

## Findings to date (through Phase 03, exploratory)

- **Whole-belt warming and drying.** Maximum temperature has risen in all 20 broadacre regions (~+0.2 °C/decade; +0.61 °C median between the 1961–1990 and 1991–2020 baselines) and annual rainfall has fallen in all 20 (~−7% median).
- **Yields are rising but the downside risk is large.** Wheat/barley/canola yields trend up ~+0.2–0.26 t/ha/decade despite the climate, yet a 1-in-10 year is only ~half the regional median — and yield variability concentrates in the drier, more climate-variable regions.
- **Annual climate is a weak year-to-year predictor of yield**, which empirically motivates growing-season / water-balance (SPI, SPEI) and heat (EHF, GDD) indicators (Phase 04). Known droughts (2001–2009, 2018) are recovered as low-yield years; single-year heat labels are not.
- **Optional crops (sorghum, cotton) excluded** on the evidence; coverage is locked to wheat/barley/canola for v1.0.

_These are descriptive EDA findings; formal modelling, extreme-value analysis, and validation follow in Phases 05–09._

## Installation

Reproducing the analysis from scratch:

```bash
git clone https://github.com/kota2003/agriculture-risk-monitoring-system.git
cd agriculture-risk-monitoring-system

# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
# python3.12 -m venv .venv
# source .venv/bin/activate

pip install -r requirements.txt
```

For contributors (additionally):

```bash
pip install -r requirements-dev.txt
pre-commit install
```

## Project Structure

```
agriculture-risk-monitoring-system/
├── data/              # raw (gitignored) and processed datasets
├── docs/              # project_scope.md, methodology.md, findings.md (Phase 10)
├── notebooks/         # phase-aligned narrative notebooks
├── outputs/           # figures, tables, models
├── scripts/           # per-step analytical scripts
├── src/               # reusable Python modules
├── PROJECT_LOG.md     # append-only decision log
└── requirements.txt   # pinned runtime dependencies
```

## Documentation

| Document | Description |
|---|---|
| [`docs/project_scope.md`](docs/project_scope.md) | Full project scope (research questions, data, methods, phase plan) — v5.2 |
| [`docs/methodology.md`](docs/methodology.md) | Methods & conventions reference (populated through Phase 03) |
| [`PROJECT_LOG.md`](PROJECT_LOG.md) | Append-only decision log (audit trail) |

## Limitations and Future Work

The binding data constraint is the fixed set of ~20 broadacre AAGIS regions × ~35 reliable years; the mixed-resolution design (grid-level climate aggregated to region-level yield) is the deliberate response. Known caveats include ABARES survey error (reported per region), sparse ACORN-SAT coverage in a few broadacre regions, and — through Phase 03 — climate captured only at annual resolution (growing-season indicators arrive in Phase 04). See `docs/project_scope.md` §12 and `docs/methodology.md` §8 for detail.

## Author

[Kota](https://github.com/kota2003)
