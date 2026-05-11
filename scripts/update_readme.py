"""
scripts/update_readme.py — Regenerate README.md from project state.

This is a maintenance script: re-run it whenever the project state
changes in a way the README should reflect (new phase completed,
new finding, new figure to embed, etc.).

Run from repo root:
    python scripts/update_readme.py

Design philosophy:
    - README content is composed from Python string sections, not
      from an external template file. This keeps everything in one
      place during development.
    - The script writes README.md atomically (write to .tmp, rename)
      so a half-finished write cannot corrupt the file.
    - Phase 00 generates a minimal "v0" README: title, tagline,
      overview, project status table (only Phase 00 marked complete),
      tech stack, installation, author. Subsequent phases extend the
      section list (findings, methods, etc.).

Convention:
    - Never hand-edit README.md. Always regenerate via this script.
    - Section functions return strings. main() assembles and writes.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# Locate repo root (this script lives at <repo>/scripts/update_readme.py)
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent
README_PATH = REPO_ROOT / "README.md"


# ---------------------------------------------------------------------------
# Project state (single source of truth — update here as phases progress)
# ---------------------------------------------------------------------------

PROJECT_TITLE = "Agriculture Risk Monitoring System"
PROJECT_SUBTITLE = "A Multi-Method Research Framework for Australian Broadacre Cropping"
GITHUB_URL = "https://github.com/kota2003/agriculture-risk-monitoring-system"
AUTHOR_NAME = "Kota"
AUTHOR_GITHUB = "https://github.com/kota2003"

# Phase progression. Status values: "Complete", "In progress", "Pending".
PHASES: list[tuple[str, str, str]] = [
    ("00", "Scope & Setup", "Complete"),
    ("01", "Data Acquisition", "Pending"),
    ("02", "Data Quality & Cross-Validation", "Pending"),
    ("03", "Exploratory Analysis", "Pending"),
    ("04", "Climate Indicator Engineering", "Pending"),
    ("05", "Extreme Value Analysis", "Pending"),
    ("06", "Climate–Yield Statistical Models", "Pending"),
    ("07", "Machine Learning Models", "Pending"),
    ("08", "Spatio-Temporal Modeling", "Pending"),
    ("09", "Multi-Method Synthesis & Validation", "Pending"),
    ("10", "Communication Layer", "Pending"),
]


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def section_title() -> str:
    return f"# {PROJECT_TITLE}\n\n*{PROJECT_SUBTITLE}*\n"


def section_last_updated() -> str:
    today = date.today().isoformat()
    return f"_Last updated: {today}_\n"


def section_overview() -> str:
    return (
        "## Overview\n\n"
        "This project quantifies how climate extremes translate into agricultural "
        "production risk across Australian broadacre regions, comparing six "
        "methodologically distinct approaches: climate indicator engineering, "
        "extreme value theory, statistical climate–yield models, machine learning, "
        "spatio-temporal modeling, and multi-method synthesis.\n\n"
        "The framework is research-depth-first; an interactive monitoring layer "
        "(dashboard) is an optional final-phase output.\n"
    )


def section_research_questions() -> str:
    return (
        "## Research Questions\n\n"
        "1. Which literature-grounded climate extreme indicators (drought, heat, frost) "
        "most cleanly track yield variation in Australian broadacre regions?\n"
        "2. What are the regional return periods of key climate extremes, and is there "
        "evidence of non-stationarity?\n"
        "3. What is the statistical relationship between climate indicators and yield "
        'outcomes — both at the mean and in the lower tail (= "risk")?\n'
        "4. Where do statistical, machine learning, and spatial–hierarchical methods "
        "agree in their risk characterizations, and where do they diverge?\n"
        "5. How well does each method recover known historical drought / heatwave "
        "events as high-risk?\n"
        "6. How does a commercial weather API (OpenWeather) compare to the gold-standard "
        "scientific dataset (SILO) when used as the climate input layer?\n"
    )


def section_data_sources() -> str:
    return (
        "## Data Sources\n\n"
        "| Source | Role | Coverage |\n"
        "|---|---|---|\n"
        "| **SILO** (Queensland DAF) | Primary climate (gridded daily, ~5km) | 1961–present |\n"
        "| **BoM ACORN-SAT** | Homogenised long-term temperature reference | 1910–present |\n"
        "| **ABARES** | Regional crop production statistics | 1980–present |\n"
        "| **ABS Agricultural Census** | Region structure / weighting (SA2 level) | 5-yearly |\n"
        "| **OpenWeather API** | Validation comparator (vs SILO) | API historical window |\n"
    )


def section_tech_stack() -> str:
    return (
        "## Tech Stack\n\n"
        "- **Python 3.12** (CPU-only stack)\n"
        "- **Environment:** pip + venv\n"
        "- **Core:** pandas, numpy, requests, pyyaml\n"
        "- **Statistical / EVT:** statsmodels, linearmodels, scipy.stats, pyextremes\n"
        "- **Machine learning:** scikit-learn, xgboost, lightgbm, shap\n"
        "- **Spatial:** geopandas, libpysal, contextily\n"
        "- **Visualization:** matplotlib, seaborn, plotly\n"
        "- **Code quality:** black, ruff, pre-commit\n"
        "\n"
        "_Libraries are added Phase-by-Phase; see `requirements.txt` for the "
        "current runtime dependency set._\n"
    )


def section_project_status() -> str:
    rows = "\n".join(
        f"| Phase {num} | {title} | {status} |" for num, title, status in PHASES
    )
    return (
        "## Project Status\n\n"
        "| Phase | Title | Status |\n"
        "|---|---|---|\n"
        f"{rows}\n"
    )


def section_installation() -> str:
    return (
        "## Installation\n\n"
        "Reproducing the analysis from scratch:\n\n"
        "```bash\n"
        f"git clone {GITHUB_URL}.git\n"
        "cd agriculture-risk-monitoring-system\n"
        "\n"
        "# Windows\n"
        "py -3.12 -m venv .venv\n"
        ".venv\\Scripts\\activate\n"
        "\n"
        "# macOS / Linux\n"
        "# python3.12 -m venv .venv\n"
        "# source .venv/bin/activate\n"
        "\n"
        "pip install -r requirements.txt\n"
        "```\n\n"
        "For contributors (additionally):\n\n"
        "```bash\n"
        "pip install -r requirements-dev.txt\n"
        "pre-commit install\n"
        "```\n"
    )


def section_project_structure() -> str:
    return (
        "## Project Structure\n\n"
        "```\n"
        "agriculture-risk-monitoring-system/\n"
        "├── data/              # raw (gitignored) and processed datasets\n"
        "├── docs/              # project_scope.md, findings.md, methodology.md\n"
        "├── notebooks/         # phase-aligned narrative notebooks\n"
        "├── outputs/           # figures, tables, models\n"
        "├── scripts/           # per-step analytical scripts\n"
        "├── src/               # reusable Python modules\n"
        "├── PROJECT_LOG.md     # append-only decision log\n"
        "└── requirements.txt   # pinned runtime dependencies\n"
        "```\n"
    )


def section_documentation() -> str:
    return (
        "## Documentation\n\n"
        "| Document | Description |\n"
        "|---|---|\n"
        "| [`docs/project_scope.md`](docs/project_scope.md) | "
        "Full project scope (research questions, data, methods, phase plan) |\n"
        "| [`PROJECT_LOG.md`](PROJECT_LOG.md) | "
        "Append-only decision log (audit trail) |\n"
    )


def section_limitations() -> str:
    return (
        "## Limitations and Future Work\n\n"
        "_Populated as findings emerge. See `docs/project_scope.md` §12 for "
        "anticipated limitations._\n"
    )


def section_author() -> str:
    return "## Author\n\n" f"[{AUTHOR_NAME}]({AUTHOR_GITHUB})\n"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_readme() -> str:
    parts = [
        section_title(),
        section_last_updated(),
        section_overview(),
        section_research_questions(),
        section_data_sources(),
        section_tech_stack(),
        section_project_status(),
        section_installation(),
        section_project_structure(),
        section_documentation(),
        section_limitations(),
        section_author(),
    ]
    return "\n".join(parts)


def write_readme_atomic(content: str) -> None:
    """Write README.md via a temp file + rename, for atomicity."""
    tmp = README_PATH.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    tmp.replace(README_PATH)


def main() -> int:
    content = build_readme()
    write_readme_atomic(content)
    print(f"README.md regenerated at: {README_PATH}")
    print(f"  Lines: {len(content.splitlines())}")
    print(f"  Bytes: {len(content.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
