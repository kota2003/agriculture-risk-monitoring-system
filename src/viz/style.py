"""
src/viz/style.py — Project-wide matplotlib / seaborn styling for Phase 03+ figures.

Establishes a single, reproducible visual language so every figure in the project
reads as one system. Import and call `apply_style()` once at the top of each
notebook or figure script; use the exported colour maps for stable, meaningful
colour assignment.

Design discipline (project dataviz conventions):
  * Categorical colours = the Okabe-Ito colourblind-safe palette (Okabe & Ito,
    2008), assigned in FIXED order and never cycled. Enough distinct, CVD-safe
    hues for the 6 SILO variables / 3 commodities / 3 AAGIS zones used in the EDA.
  * Sequential = single-hue, perceptually uniform (cividis, CVD-safe) by default,
    with semantic ramps for rainfall (YlGnBu) and temperature (inferno).
  * Diverging = two-hue with a neutral grey midpoint (RdBu_r) for anomalies.
  * Colour follows the entity, never its rank (stable ZONE/COMMODITY/VARIABLE maps).
  * Recessive grid / axes, thin marks, restrained typography.

Determinism: exposes SEED (=42) for any sampling done in figure code.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt  # noqa: F401  (re-exported convenience for notebooks)
import seaborn as sns

from src.paths import FIGURES_DIR

SEED = 42

# Okabe-Ito colourblind-safe categorical palette (fixed order; do not reorder).
OKABE_ITO = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # bluish green
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#56B4E9",  # sky blue
    "#F0E442",  # yellow
    "#000000",  # black
]

# Colour-map choices by job (sequential = one hue; diverging = two hues + neutral).
SEQUENTIAL_DEFAULT = "cividis"
CMAP_RAINFALL = "YlGnBu"
CMAP_TEMPERATURE = "inferno"
CMAP_ANOMALY = "RdBu_r"  # diverging, neutral grey midpoint (e.g. temp/rain anomalies)

# Stable entity -> colour maps (colour follows the entity, never its rank/order).
ZONE_COLORS = {
    "Wheat Sheep": OKABE_ITO[0],
    "High Rainfall": OKABE_ITO[2],
    "Pastoral": OKABE_ITO[7],
}
COMMODITY_COLORS = {
    "wheat": OKABE_ITO[1],
    "barley": OKABE_ITO[0],
    "canola": OKABE_ITO[2],
}
VARIABLE_COLORS = {
    "max_temp": OKABE_ITO[3],
    "min_temp": OKABE_ITO[0],
    "daily_rain": OKABE_ITO[2],
    "evap_pan": OKABE_ITO[1],
    "radiation": OKABE_ITO[4],
    "vp": OKABE_ITO[5],
}


def apply_style() -> None:
    """Apply the project-wide matplotlib / seaborn rcParams. Idempotent."""
    sns.set_theme(context="notebook", style="whitegrid")
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "figure.figsize": (8.0, 5.0),
            "axes.prop_cycle": mpl.cycler(color=OKABE_ITO),
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": "#666666",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": "#DDDDDD",
            "grid.linewidth": 0.6,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "legend.frameon": False,
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
            "font.size": 10,
        }
    )


def savefig(fig: mpl.figure.Figure, name: str, subdir: str | None = None) -> Path:
    """Save `fig` as PNG under outputs/figures/ with a descriptive stem.

    Use descriptive names (scope §11.2), never `fig1.png`. Returns the path.
    """
    out_dir = FIGURES_DIR if subdir is None else FIGURES_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    if not name.endswith(".png"):
        name = f"{name}.png"
    path = out_dir / name
    fig.savefig(path)
    return path


__all__ = [
    "SEED",
    "OKABE_ITO",
    "SEQUENTIAL_DEFAULT",
    "CMAP_RAINFALL",
    "CMAP_TEMPERATURE",
    "CMAP_ANOMALY",
    "ZONE_COLORS",
    "COMMODITY_COLORS",
    "VARIABLE_COLORS",
    "apply_style",
    "savefig",
]
