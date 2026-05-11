# Agriculture Risk Monitoring System

*A Multi-Method Research Framework for Australian Broadacre Cropping*

_Last updated: 2026-05-12_

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
| **ABARES** | Regional crop production statistics | 1980–present |
| **ABS Agricultural Census** | Region structure / weighting (SA2 level) | 5-yearly |
| **OpenWeather API** | Validation comparator (vs SILO) | API historical window |

## Tech Stack

- **Python 3.12** (CPU-only stack)
- **Environment:** pip + venv
- **Core:** pandas, numpy, requests, pyyaml
- **Statistical / EVT:** statsmodels, linearmodels, scipy.stats, pyextremes
- **Machine learning:** scikit-learn, xgboost, lightgbm, shap
- **Spatial:** geopandas, libpysal, contextily
- **Visualization:** matplotlib, seaborn, plotly
- **Code quality:** black, ruff, pre-commit

_Libraries are added Phase-by-Phase; see `requirements.txt` for the current runtime dependency set._

## Project Status

| Phase | Title | Status |
|---|---|---|
| Phase 00 | Scope & Setup | Complete |
| Phase 01 | Data Acquisition | Pending |
| Phase 02 | Data Quality & Cross-Validation | Pending |
| Phase 03 | Exploratory Analysis | Pending |
| Phase 04 | Climate Indicator Engineering | Pending |
| Phase 05 | Extreme Value Analysis | Pending |
| Phase 06 | Climate–Yield Statistical Models | Pending |
| Phase 07 | Machine Learning Models | Pending |
| Phase 08 | Spatio-Temporal Modeling | Pending |
| Phase 09 | Multi-Method Synthesis & Validation | Pending |
| Phase 10 | Communication Layer | Pending |

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
├── docs/              # project_scope.md, findings.md, methodology.md
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
| [`docs/project_scope.md`](docs/project_scope.md) | Full project scope (research questions, data, methods, phase plan) |
| [`PROJECT_LOG.md`](PROJECT_LOG.md) | Append-only decision log (audit trail) |

## Limitations and Future Work

_Populated as findings emerge. See `docs/project_scope.md` §12 for anticipated limitations._

## Author

[Kota](https://github.com/kota2003)
