
---

## 2026-07-21 — Phase 04, Step 03: SPEI grid computation (SPEI-3 and SPEI-12)

**Context:** Phase 04 Step 03. Implements SPEI at scales 3 and 12 months at SILO grid resolution for all years 1970–2024, aggregated to AAGIS regions. Branch `phase-04-climate-indicators`.

**Indicator definition (Vicente-Serrano et al. 2010):**
- Monthly water balance D = P − PET, where P = SILO `daily_rain` accumulated to monthly totals and PET ≈ `evap_pan` monthly totals.
- k-month rolling sums of D fitted to a 3-parameter log-logistic distribution using ascending Probability-Weighted Moments (PWM).
- Baseline period: **1970–1999** (constrained by `evap_pan` effective start = 1970; consistent with WMO 30-year baseline practice).
- Scales k = 3 (seasonal drought) and k = 12 (annual drought persistence).

**Key implementation decisions:**

1. **Ascending PWM for log-logistic fit.** β > 1 required for valid (unimodal) log-logistic; cells where β ≤ 1 or fitting is degenerate produce NaN SPEI.
2. **Continuous monthly series required for k ≥ 3.** Rolling sums must cross year boundaries; `spei_for_year` prepends 11 prior months to allow valid k-month sums from January onward.
3. **evap_pan constraint.** SILO `evap_pan` is absent for 1961–1969; SPEI starts at 1970.

**Deliverables:**
1. `src/indicators/drought.py` — `monthly_pet()`, `monthly_water_balance()`, `_loglogistic_fit()`, `fit_spei_params()`, `spei_for_year()` (in addition to existing SPI/CDD functions).
2. `tests/test_spei_indicators.py` — class-based, 475 lines; **23 passed, 4 skipped**.
3. `scripts/phase04_s03_spei_grid.py` — orchestrator: fit params → annual SPEI → region time-series → validation.

**Outputs:**
- `indicators/spei/params/spei_params_k3.nc`, `spei_params_k12.nc`.
- `indicators/spei/annual/{year}.spei3.nc`, `{year}.spei12.nc` (1970–2024).
- `indicators/spei/spei_region_timeseries.parquet`.

**Validation (all PASS):**
- β > 1 for ≥ 80% of finite cells (all calendar months).
- SPEI mean ∈ (−0.5, 0.5) over 1970–1999 baseline.
- SPEI std ∈ (0.5, 1.5) over 1970–1999 baseline.

**Test classes:** `TestLoglogisticFit`, `TestSPEIConstants`, `TestMonthlyPet`, `TestMonthlyWaterBalance`, `TestFitSpeiParams`, `TestSpeiForYear`, `TestSpeiWithRealData`.

**Dependencies:** none new (`scipy` already present).

**Scope:** no revision; scope stays v5.2.

**Impact:** Step 03 complete. Phase 04 s04a/04b (EHF, frost days) can proceed.

---

## 2026-07-21 — Phase 04, Step 04a: EHF (Excess Heat Factor) grid computation

**Context:** Phase 04 Step 04a. Implements EHF (Nairn & Fawcett 2015) at SILO grid resolution for all years 1961–2024, aggregated to AAGIS regions. Branch `phase-04-climate-indicators`.

**Indicator definition (Nairn & Fawcett 2015):**
- EHF = EHI_sig × max(1, EHI_accl), where EHI_sig measures the current 3-day mean relative to the T90 climatological baseline, and EHI_accl measures it relative to the prior 30-day mean.
- **T90 baseline:** 90th percentile of 32-day rolling T_mean over 1961–1990, per grid cell.
- **Heatwave day:** EHF > 0 AND part of a consecutive run ≥ 3 days.
- **Seasonal aggregation:** heatwave-day count within the growing-season window.

**Key implementation decisions:**

1. **T90 as a spatial field.** T90 is a (lat, lon) DataArray from the 1961–1990 climatological period, respecting spatial heterogeneity.
2. **32-day rolling window requires prior-year data.** `ehf_for_year` loads the final 32 days of year−1; January EHF is NaN for 1961 (expected).
3. **Constants:** `EHF_BASELINE_START=1961`, `EHF_BASELINE_END=1990`, `EHF_T90_PERCENTILE=90.0`.

**Deliverables:**
1. `src/indicators/heat.py` — `compute_t90_baseline()`, `ehf_for_year()`, `ehf_season_summary()` (appended to heat.py alongside GDD functions).
2. `tests/test_ehf_indicators.py` — class-based, 400 lines; **17 passed, 2 skipped**.
3. `scripts/phase04_s04a_ehf_grid.py` — orchestrator: T90 → annual EHF → heatwave-day counts → region time-series → validation.

**Outputs:**
- `indicators/ehf/t90_baseline.nc`.
- `indicators/ehf/annual/{year}.ehf_daily.nc`, `{year}.ehf_hwdays.nc` (1961–2024).
- `indicators/ehf/ehf_region_timeseries.parquet`.

**Validation (all PASS):** T90 ∈ (15, 45) °C; heatwave-day counts ≥ 0; at least one year with mean > 0.

**Test classes:** `TestEhfConstants`, `TestComputeT90Baseline`, `TestEhfForYear`, `TestEhfSeasonSummary`, `TestEhfWithRealData`.

**Dependencies:** none new.

**Scope:** no revision; scope stays v5.2.

**Impact:** Step 04a complete. Phase 04 s04b (frost days) can proceed.

---

## 2026-07-21 — Phase 04, Step 04b: Frost-day grid computation

**Context:** Phase 04 Step 04b. Implements the ETCCDI frost-day indicator at SILO grid resolution for all years 1961–2024, aggregated to AAGIS regions. Branch `phase-04-climate-indicators`.

**Indicator definition (Tank et al. 2009, ETCCDI):**
- **Frost threshold:** tmin < 2°C (strict less-than; agricultural frost definition capturing plant damage before ice formation).
- **Frost-day count:** number of growing-season days where tmin < 2°C.
- **Growing-season windows:** `southern_winter` Apr–Oct; `qld_summer` Sep–Feb cross-year.
- **Constant:** `FROST_THRESHOLD_C = 2.0` (parameterised for future sensitivity analysis).

**Key implementation decisions:**

1. **2°C threshold (not 0°C).** ETCCDI agricultural frost definition; 2°C accounts for cellular damage above 0°C at flowering.
2. **Window consistency.** Same growing-season windows as GDD/SPI/CDD.
3. **Cross-year handling for QLD.** Sep–Feb window requires data from two consecutive SILO annual files.

**Deliverables:**
1. `src/indicators/frost.py` — `frost_days_growing_season()`.
2. `tests/test_frost_indicators.py` — module-level, **20 tests, all passed**.
3. `scripts/phase04_s04b_frost_grid.py` — orchestrator: annual frost-day grid → region time-series → validation.

**Outputs:**
- `indicators/frost/annual/{year}.frost_days.nc` (1961–2024).
- `indicators/frost/frost_region_timeseries.parquet`.

**Validation (all PASS):** Frost-day counts ≥ 0; at least one year with mean > 0 in southern Australia.

**Dependencies:** none new.

**Scope:** no revision; scope stays v5.2.

**Impact:** Step 04b complete. All Phase 04 indicators implemented. Ready for Phase 04 closure ceremony.

---

## 2026-07-29 — Phase 04 closure ceremony

**Context:** All Phase 04 steps complete. Executing closure (PROJECT_WORKFLOW §9). Branch `phase-04-climate-indicators`.

**Full indicator panel:**

| Indicator | Years | Scales/Window | Tests |
|-----------|-------|---------------|-------|
| GDD (Tbase=0°C) | 1961–2024 | Apr–Oct | 22 |
| SPI | 1961–2024 | k=3, k=12 | 23 |
| CDD | 1961–2024 | Apr–Oct | 23 |
| SPEI | 1970–2024 | k=3, k=12 | 23 |
| EHF | 1961–2024 | Apr–Oct | 17 |
| Frost days (tmin < 2°C) | 1961–2024 | Apr–Oct / Sep–Feb | 20 |

**Test suite:** 5 files, **105 passed, 8 skipped** (data-backed; all skips expected and documented).

**Task F (cropping-mask threshold sensitivity, t005 vs t010 vs t020) — formally deferred to Phase 09.** Flagged in `phase03_summary.md` as "actionable in Phase 04" but deferred because (a) t005 mask is stable and validated since Phase 02; (b) Phase 09 multi-method synthesis / robustness study is the appropriate place for a systematic sensitivity analysis alongside the MAUP study.

**Actions:**
1. `methodology.md` §9 (Phase 04) populated.
2. `docs/phase_summaries/phase04_summary.md` created as Phase 05 handoff.
3. Source files delivered to Kota for local commit.

**Git ceremony (executed by Kota):**
```
git add src/indicators/frost.py src/indicators/heat.py src/indicators/drought.py src/indicators/__init__.py
git add tests/test_ehf_indicators.py tests/test_spei_indicators.py tests/test_frost_indicators.py
git add scripts/phase04_s03_spei_grid.py scripts/phase04_s04a_ehf_grid.py scripts/phase04_s04b_frost_grid.py
git add docs/phase_summaries/phase04_summary.md PROJECT_LOG.md
git commit -m "[Phase 04 s03-s04b] SPEI, EHF, frost-day indicators — 105 tests passing"
git checkout main
git merge --no-ff phase-04-climate-indicators -m "Merge phase-04-climate-indicators: Phase 04 complete (6 indicators, 105 tests, 5 scripts)"
git tag -a v0.4-phase04-complete -m "Phase 04 complete: GDD, SPI-3/12, CDD, SPEI-3/12, EHF, frost days at SILO grid resolution"
git push origin main && git push origin --tags
```

**Discipline scorecard (all ✓):** observed-vs-derived ✓; empirical honesty (SPEI 1970+ constraint) ✓; Task F deferral explicit ✓; scripts idempotent ✓; no new dependencies ✓; scope v5.2 unchanged ✓; bilingual discipline ✓.

**Impact:** Phase 04 COMPLETE. Six climate extreme indicators at SILO grid resolution (~5 km), aggregated to 30 AAGIS broadacre regions over 1961–2024 (SPEI 1970–2024). This indicator panel forms the Pillar 1 feature set for Phase 05 (EVT) and Pillars 3–5. Phase 05 is enabled from tag `v0.4-phase04-complete`.
