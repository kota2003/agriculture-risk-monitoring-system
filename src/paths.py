"""
src/paths.py — Project path resolution and directory constants.

Provides a single source of truth for filesystem paths used across all
phases. Downstream modules and notebooks should `from src.paths import ...`
rather than hard-coding absolute paths (Project 4 lesson: never hardcode
absolute paths; always use relative paths anchored at the repo root).

Usage:
    from src.paths import REPO_ROOT, DATA_RAW, DATA_PROCESSED, FIGURES_DIR

    raw_silo = DATA_RAW / "silo"
    fig_path = FIGURES_DIR / "yield_distribution.png"

Convention:
    - All paths are `pathlib.Path` objects, never strings.
    - Paths are resolved at import time from this file's location.
    - Constants are UPPER_SNAKE_CASE.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------------
# This file lives at <repo>/src/paths.py.
# Going up two levels (-> src -> repo root) gives the repository root.

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Top-level directories
# ---------------------------------------------------------------------------

DATA_DIR: Path = REPO_ROOT / "data"
NOTEBOOKS_DIR: Path = REPO_ROOT / "notebooks"
OUTPUTS_DIR: Path = REPO_ROOT / "outputs"
DOCS_DIR: Path = REPO_ROOT / "docs"
SCRIPTS_DIR: Path = REPO_ROOT / "scripts"
SRC_DIR: Path = REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# Data subdirectories
# ---------------------------------------------------------------------------

DATA_RAW: Path = DATA_DIR / "raw"
DATA_PROCESSED: Path = DATA_DIR / "processed"
DATA_MANIFEST: Path = DATA_RAW / "manifest.yaml"


# ---------------------------------------------------------------------------
# Output subdirectories
# ---------------------------------------------------------------------------

FIGURES_DIR: Path = OUTPUTS_DIR / "figures"
TABLES_DIR: Path = OUTPUTS_DIR / "tables"
MODELS_DIR: Path = OUTPUTS_DIR / "models"


# ---------------------------------------------------------------------------
# Documentation subdirectories
# ---------------------------------------------------------------------------

PHASE_SUMMARIES_DIR: Path = DOCS_DIR / "phase_summaries"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "REPO_ROOT",
    "DATA_DIR",
    "NOTEBOOKS_DIR",
    "OUTPUTS_DIR",
    "DOCS_DIR",
    "SCRIPTS_DIR",
    "SRC_DIR",
    "DATA_RAW",
    "DATA_PROCESSED",
    "DATA_MANIFEST",
    "FIGURES_DIR",
    "TABLES_DIR",
    "MODELS_DIR",
    "PHASE_SUMMARIES_DIR",
]
