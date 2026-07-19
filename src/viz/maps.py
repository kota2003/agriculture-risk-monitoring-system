"""
src/viz/maps.py — AAGIS region choropleth maps for the broadacre analysis.

A single, reusable choropleth for "value per AAGIS region" figures: the Phase 03
climate maps (rainfall / temperature climatologies, baseline shifts) and, later,
the Pillar 6 multi-method risk maps (scope §5.6.1). Pastoral (non-broadacre)
regions are drawn in neutral grey for spatial context; the broadacre regions
carry the colour.

Colour discipline (project dataviz): sequential single-hue ramps for magnitude,
the diverging RdBu_r (neutral midpoint) for signed change — see src/viz/style.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src.paths import DATA_PROCESSED

AAGIS_GPKG = DATA_PROCESSED / "aagis_regions_repaired.gpkg"
REGION_MAPPING_CSV = DATA_PROCESSED / "region_mapping.csv"
BROADACRE_ZONES = ("Wheat Sheep", "High Rainfall")

_PASTORAL_FILL = "#EEEEEE"
_PASTORAL_EDGE = "#BBBBBB"
_REGION_EDGE = "#666666"


def load_region_geometries():
    """AAGIS region polygons with the authoritative code/name/zone from the mapping."""
    import geopandas as gpd

    g = gpd.read_file(AAGIS_GPKG)[["class", "geometry"]]
    g["aagis_code"] = g["class"].astype(str).str.strip()
    rm = pd.read_csv(REGION_MAPPING_CSV, dtype={"aagis_code": str})
    return g.merge(
        rm[["aagis_code", "region_name", "zone"]], on="aagis_code", how="left"
    )


def region_choropleth(
    values,
    value_col: str,
    *,
    ax=None,
    cmap: str = "viridis",
    label: str = "",
    title: str | None = None,
    diverging: bool = False,
    vmax_cap: float | None = None,
):
    """
    Draw a value-per-AAGIS-region choropleth; pastoral regions greyed for context.

    Parameters
    ----------
    values : DataFrame | Series
        DataFrame with ``aagis_code`` + ``value_col``, or a Series indexed by
        ``aagis_code``.
    cmap : str
        A sequential ramp for magnitude, or a diverging ramp when ``diverging``.
    diverging : bool
        Centre the scale on 0 with symmetric limits (for signed change maps).
    vmax_cap : float | None
        Cap the upper colour limit (with an ``extend='max'`` bar) so a heavy
        upper tail does not compress the rest of the scale.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 6.0))

    if isinstance(values, pd.Series):
        values = values.rename(value_col).rename_axis("aagis_code").reset_index()
    vals = values[["aagis_code", value_col]].copy()
    vals["aagis_code"] = vals["aagis_code"].astype(str)

    g = load_region_geometries()
    gm = g.merge(vals, on="aagis_code", how="left")
    is_broad = gm["zone"].isin(BROADACRE_ZONES)

    gm[~is_broad].plot(
        ax=ax, color=_PASTORAL_FILL, edgecolor=_PASTORAL_EDGE, linewidth=0.4
    )

    bro = gm[is_broad]
    extend = "neither"
    legend_kwds = {"label": label, "shrink": 0.6}
    plot_kwds = dict(cmap=cmap, edgecolor=_REGION_EDGE, linewidth=0.5, legend=True)
    v = bro[value_col].dropna()
    if diverging:
        m = float(max(abs(v.min()), abs(v.max())))
        plot_kwds.update(vmin=-m, vmax=m)
    elif vmax_cap is not None:
        plot_kwds.update(vmin=float(v.min()), vmax=float(vmax_cap))
        extend = "max"
    legend_kwds["extend"] = extend

    # Broadacre regions with no value (e.g. sparse-coverage regions excluded from
    # a statistic) are drawn as an explicit hatched "no data" fill, not left blank.
    bro.plot(
        ax=ax,
        column=value_col,
        legend_kwds=legend_kwds,
        missing_kwds={
            "color": "#FFFFFF",
            "edgecolor": "#999999",
            "hatch": "////",
            "linewidth": 0.4,
        },
        **plot_kwds,
    )
    ax.axis("off")
    if title:
        ax.set_title(title)
    return ax


__all__ = [
    "AAGIS_GPKG",
    "REGION_MAPPING_CSV",
    "BROADACRE_ZONES",
    "load_region_geometries",
    "region_choropleth",
]
