"""
src/indicators — Phase 04 climate extreme indicator library.

Modules
-------
_base   : Shared helpers (growing-season windows, SILO loader, cell map).
heat    : GDD (Growing Degree Days), EHF (Excess Heat Factor).
drought : SPI, SPEI (drought indices), CDD (Consecutive Dry Days).
frost   : Frost days (ETCCDI, Tank et al. 2009).

All indicators are computed at SILO grid resolution before any region
aggregation, per scope §3.6 and §5.1.
"""

from src.indicators._base import (
    GROWING_WINDOWS,
    cos_lat_weights,
    get_cropping_cells,
    get_growing_window,
    load_silo_year,
)
from src.indicators.drought import (
    EVAP_BASELINE_END,
    EVAP_BASELINE_START,
    SPEI_SCALES,
    cdd_growing_season,
    fit_spei_params,
    fit_spi_params,
    monthly_pet,
    monthly_rain,
    monthly_water_balance,
    spei_for_year,
    spi_for_year,
)
from src.indicators.frost import (
    FROST_THRESHOLD_C,
    frost_days_growing_season,
)
from src.indicators.heat import (
    EHF_BASELINE_END,
    EHF_BASELINE_START,
    EHF_T90_PERCENTILE,
    compute_t90_baseline,
    daily_gdd,
    ehf_for_year,
    ehf_season_summary,
    gdd_growing_season,
    gdd_timeseries_cells,
)

__all__ = [
    # _base
    "GROWING_WINDOWS",
    "get_growing_window",
    "get_cropping_cells",
    "cos_lat_weights",
    "load_silo_year",
    # heat — GDD
    "daily_gdd",
    "gdd_growing_season",
    "gdd_timeseries_cells",
    # heat — EHF
    "EHF_BASELINE_START",
    "EHF_BASELINE_END",
    "EHF_T90_PERCENTILE",
    "compute_t90_baseline",
    "ehf_for_year",
    "ehf_season_summary",
    # drought — SPI / CDD
    "monthly_rain",
    "fit_spi_params",
    "spi_for_year",
    "cdd_growing_season",
    # frost
    "FROST_THRESHOLD_C",
    "frost_days_growing_season",
    # drought — SPEI
    "EVAP_BASELINE_START",
    "EVAP_BASELINE_END",
    "SPEI_SCALES",
    "monthly_pet",
    "monthly_water_balance",
    "fit_spei_params",
    "spei_for_year",
]
