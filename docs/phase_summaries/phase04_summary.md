# Phase 04 Summary — Climate Indicator Engineering

**Phase:** 04
**Status:** COMPLETE
**Completed:** 2026-07-29
**Branch:** `phase-04-climate-indicators`
**Tag:** `v0.4-phase04-complete`
**Handoff to:** Phase 05 (Extreme Value Analysis)

---

## What Phase 04 built

Six growing-season climate extreme indicators computed at SILO grid resolution (~5 km, 28,577-cell cropping mask, t005 threshold) for all years 1961–2024 (SPEI from 1970), then aggregated to 30 AAGIS broadacre regions via cos(latitude) area-weighted means.

| Indicator | Reference | Years | Scales / Window | Module |
|-----------|-----------|-------|-----------------|--------|
| GDD (Tbase=0°C) | McMaster & Wilhelm 1997 | 1961–2024 | Apr–Oct (southern_winter) | `src/indicators/heat.py` |
| SPI | McKee et al. 1993 | 1961–2024 | k=3, k=12 | `src/indicators/drought.py` |
| CDD | ETCCDI | 1961–2024 | Apr–Oct | `src/indicators/drought.py` |
| SPEI | Vicente-Serrano et al. 2010 | 1970–2024 | k=3, k=12 | `src/indicators/drought.py` |
| EHF (heatwave days) | Nairn & Fawcett 2015 | 1961–2024 | Apr–Oct | `src/indicators/heat.py` |
| Frost days (tmin < 2°C) | Tank et al. 2009, ETCCDI | 1961–2024 | Apr–Oct / Sep–Feb (QLD) | `src/indicators/frost.py` |

---

## Key implementation decisions (for Phase 05 context)

**GDD:** Tbase=0°C (Australian broadacre cereal standard). Region summary includes mean, p10, p25, p75, p90, std of cell values — within-region distributional information preserved.

**SPI:** Zero-adjusted Gamma distribution (Thom 1958 analytical MLE); WMO baseline 1961–1990. Continuous monthly series required: SPI-12 for 1961 is NaN (expected; 11 prior months unavailable).

**CDD:** Max consecutive days with rain < 1mm within growing-season window. Pure ETCCDI definition; no baseline required.

**SPEI:** 3-parameter log-logistic distribution, ascending PWM (Hosking & Wallis 1997); baseline 1970–1999 (evap_pan constraint). β > 1 required for valid fit; cells where β ≤ 1 produce NaN SPEI. PET ≈ SILO `evap_pan` monthly totals.

**EHF:** T90 baseline (90th percentile of 32-day rolling T_mean, 1961–1990) is a spatial field (lat, lon) — threshold adapts to local climate. Heatwave day = EHF > 0 AND part of ≥3-day consecutive run. Seasonal aggregate = count of heatwave days within growing-season window. January 1961 EHF is NaN (32-day window straddles prior year).

**Frost days:** tmin < 2°C (ETCCDI agricultural frost threshold; 2°C captures plant-cell damage before ice formation). Cross-year handling for QLD Sep–Feb window.

**Growing windows:** `southern_winter` = April–October; `qld_summer` = September–February (cross-year). Used consistently across all six indicators.

**Grid-first aggregation:** Each indicator computed at cell level, then cos(lat)-weighted mean to region. This preserves within-region heterogeneity and avoids Jensen's-inequality artefacts from pre-averaging climate inputs.

---

## Test suite

| File | Pattern | Passed | Skipped |
|------|---------|--------|---------|
| `tests/test_heat_indicators.py` | module-level | 22 | 2 |
| `tests/test_drought_indicators.py` | module-level | 23 | 2 |
| `tests/test_spei_indicators.py` | class-based | 23 | 4 |
| `tests/test_ehf_indicators.py` | class-based | 17 | 0 |
| `tests/test_frost_indicators.py` | module-level | 20 | 0 |
| **Total** | | **105** | **8** |

All skips are data-backed (SILO files not present in CI environment) and documented.

---

## Outputs available for Phase 05

### NetCDF grids (per-year, gitignored — regenerable)

```
indicators/gdd/gdd_growing_season_{year}.nc          (64 files)
indicators/spi/annual/{year}.spi3.nc                 (64 files)
indicators/spi/annual/{year}.spi12.nc                (64 files)
indicators/spei/annual/{year}.spei3.nc               (55 files, 1970–2024)
indicators/spei/annual/{year}.spei12.nc              (55 files, 1970–2024)
indicators/ehf/annual/{year}.ehf_daily.nc            (64 files)
indicators/ehf/annual/{year}.ehf_hwdays.nc           (64 files)
indicators/frost/annual/{year}.frost_days.nc         (64 files)
```

### Region time-series (primary Phase 05+ inputs, committed)

```
indicators/region_summaries/gdd_region_summary.csv    (~1,920 rows; includes p10/p25/p75/p90/std)
indicators/spi/spi_region_timeseries.parquet          (~3,840 rows; SPI-3 and SPI-12)
indicators/spei/spei_region_timeseries.parquet        (~3,300 rows; SPEI-3 and SPEI-12)
indicators/ehf/ehf_region_timeseries.parquet          (~1,920 rows; seasonal heatwave days)
indicators/frost/frost_region_timeseries.parquet      (~1,920 rows; seasonal frost days)
```

### Fitted parameters (committed)

```
indicators/spei/params/spei_params_k3.nc
indicators/spei/params/spei_params_k12.nc
indicators/ehf/t90_baseline.nc
```

---

## Scripts

| Script | Function |
|--------|----------|
| `scripts/phase04_s01_gdd_grid.py` | GDD grid computation + region aggregation |
| `scripts/phase04_s02_spi_cdd_grid.py` | SPI-3/12, CDD grid computation + region aggregation |
| `scripts/phase04_s03_spei_grid.py` | SPEI-3/12 grid computation + region aggregation |
| `scripts/phase04_s04a_ehf_grid.py` | EHF + T90 baseline + region aggregation |
| `scripts/phase04_s04b_frost_grid.py` | Frost-day grid computation + region aggregation |

All scripts are idempotent (skip already-computed years) and include quantitative validation gates (exit code 1 on failure).

---

## What was deferred

**Task F — cropping-mask threshold sensitivity (t005 vs t010 vs t020).** Flagged as "actionable in Phase 04" in the Phase 03 handoff but formally deferred to Phase 09. Rationale: (a) the t005 mask is stable and validated since Phase 02; (b) Phase 09 is the appropriate place for systematic robustness analysis alongside the MAUP study and AGFD validation. See `methodology.md` §9.8 and §14.

---

## Phase 05 entry conditions

Phase 05 (Extreme Value Analysis) is enabled from tag `v0.4-phase04-complete`. Inputs are:

1. **Region time-series parquet files** listed above — the primary EVT fitting input.
2. **Per-year NetCDF grids** — available if grid-level EVT fitting is needed (Pillar 2 scope).
3. **Cropping-cell map** (`data/processed/silo/cropping_cells.parquet`) — 28,577 cells with `aagis_code` labels for region rollup.

Phase 05 decisions to make at entry:
- GEV vs POT (peaks-over-threshold) per indicator.
- Stationarity assumption: fit as stationary first, then non-stationary (parameter as function of time) as a robustness extension.
- Return-level targets: 1-in-10, 1-in-20, 1-in-50 year events.
- Grid-level vs region-level EVT fitting strategy.

---

## Discipline scorecard

| Check | Status |
|-------|--------|
| Observed-vs-derived discipline (AGFD never used) | ✓ |
| Empirical honesty (SPEI 1970+ constraint documented) | ✓ |
| Task F deferral explicit and logged | ✓ |
| All scripts idempotent | ✓ |
| No new Python dependencies | ✓ |
| Scope v5.2 unchanged | ✓ |
| Bilingual discipline (English code/docs, Japanese conversation) | ✓ |
