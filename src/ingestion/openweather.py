"""
OpenWeather One Call 3.0 daily-aggregation ingestion (Phase 01 Step 08).

Retrieves daily-aggregated historical weather data for a set of lat/lon
centroids (one per approved AAGIS region) over a configurable date range,
using the One Call 3.0 `day_summary` endpoint.

Purpose (scope v4 §4.5):
    OpenWeather is a *validation comparator*, NOT a primary climate input.
    Phase 09 will compare these point queries against SILO gridded data at
    the same lat/lon for the same date range. The OpenWeather–SILO
    comparison is itself the methodological contribution of this study,
    not a substitute for SILO.

Endpoint (verified 2026-05-15):
    GET https://api.openweathermap.org/data/3.0/onecall/day_summary
        ?lat={lat}&lon={lon}&date={YYYY-MM-DD}&units=metric&appid={API_KEY}

    Returns one JSON object per (lat, lon, date) — 1 call per region-day.

Response fields persisted (metric units):
    temperature.min       -> tmin_c          (°C)
    temperature.max       -> tmax_c          (°C)
    temperature.morning   -> t_morning_c     (°C, 06:00 local)
    temperature.afternoon -> t_afternoon_c   (°C, 12:00 local)
    temperature.evening   -> t_evening_c     (°C, 18:00 local)
    temperature.night     -> t_night_c       (°C, 00:00 local)
    precipitation.total   -> precip_mm       (mm)
    humidity.afternoon    -> humidity_pct
    pressure.afternoon    -> pressure_hpa
    cloud_cover.afternoon -> cloud_cover_pct
    wind.max.speed        -> wind_max_ms     (m/s)
    wind.max.direction    -> wind_max_deg

Rate / cost discipline (scope §4.5, §10):
    - Free quota:    1,000 calls/day
    - Subscription:  Daily hard limit set to 11,000 calls/day in dashboard
    - Per-call price (after free): GBP 0.0012
    - Rate limit:    60 calls/min for the One Call subscription tier
    - This module honours a 1.05-second sleep between calls (default)
      to stay safely below the 60/min ceiling.

Resume / idempotency:
    Each region writes one Parquet file per year:
        data/raw/openweather/<region_code>_<year>.parquet
    On re-run, dates already present in the per-year Parquet are skipped.
    Partial-year files are loaded and appended to, not overwritten.

Error handling:
    HTTP 429 (rate-limit) -> exponential backoff: sleep 60, 120, 240 s
    HTTP 5xx              -> retry up to 3 times with exponential backoff
    HTTP 401 (invalid key) -> raise immediately (no retry)
    HTTP 404 (date out of range) -> warn and skip the date
    Other errors          -> log and continue with next date

API key handling:
    Loaded from environment via `python-dotenv`. The .env file is
    gitignored. .env.example provides a template.

Persistence format:
    Parquet (smaller than CSV, preserves dtypes). One row per
    (region_code, date). All numeric columns are nullable Float64 to
    handle missing values (e.g. wind on calm days).
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.log_utils import log, ok, warn

# ----- Constants ----------------------------------------------------------

ONECALL_DAY_SUMMARY_URL = "https://api.openweathermap.org/data/3.0/onecall/day_summary"

DEFAULT_SLEEP_SECONDS = 1.05  # 60 calls / 63 sec headroom under 60/min limit
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30  # seconds per HTTP request


# ----- API key loading ----------------------------------------------------


def get_api_key() -> str:
    """
    Load the OPENWEATHER_API_KEY from environment. .env is loaded first
    if present. Raises RuntimeError if the key is missing.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # python-dotenv is in requirements.txt but allow plain env
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENWEATHER_API_KEY not found. Set it in .env (gitignored) "
            "or as an environment variable. See .env.example."
        )
    return key


# ----- Single-day fetch ---------------------------------------------------


def _parse_day_summary(resp_json: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten the One Call 3.0 day_summary nested JSON into a flat row dict.
    Missing fields become None (pandas will store as NaN).
    """

    def _g(d: dict, *keys, default=None):
        cur = d
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    return {
        "date": resp_json.get("date"),
        "lat": resp_json.get("lat"),
        "lon": resp_json.get("lon"),
        "tz": resp_json.get("tz"),
        "tmin_c": _g(resp_json, "temperature", "min"),
        "tmax_c": _g(resp_json, "temperature", "max"),
        "t_morning_c": _g(resp_json, "temperature", "morning"),
        "t_afternoon_c": _g(resp_json, "temperature", "afternoon"),
        "t_evening_c": _g(resp_json, "temperature", "evening"),
        "t_night_c": _g(resp_json, "temperature", "night"),
        "precip_mm": _g(resp_json, "precipitation", "total"),
        "humidity_pct": _g(resp_json, "humidity", "afternoon"),
        "pressure_hpa": _g(resp_json, "pressure", "afternoon"),
        "cloud_cover_pct": _g(resp_json, "cloud_cover", "afternoon"),
        "wind_max_ms": _g(resp_json, "wind", "max", "speed"),
        "wind_max_deg": _g(resp_json, "wind", "max", "direction"),
    }


def fetch_day_summary(
    api_key: str,
    lat: float,
    lon: float,
    date_str: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """
    Fetch one day_summary record. Returns a flat row dict or None on
    permanent failure (404 for that date, malformed response).

    Raises RuntimeError on 401 (auth failure — caller should abort run).
    """
    params = {
        "lat": lat,
        "lon": lon,
        "date": date_str,
        "units": "metric",
        "appid": api_key,
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                ONECALL_DAY_SUMMARY_URL,
                params=params,
                timeout=timeout,
            )
        except requests.RequestException as e:
            warn(f"    network error (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(2 ** (attempt + 1))  # 2, 4, 8 s
            continue

        if resp.status_code == 200:
            try:
                return _parse_day_summary(resp.json())
            except ValueError as e:
                warn(f"    malformed JSON for {date_str}: {e}")
                return None
        if resp.status_code == 401:
            raise RuntimeError(
                "OpenWeather API returned 401 Unauthorized. "
                "Check OPENWEATHER_API_KEY validity and One Call 3.0 subscription."
            )
        if resp.status_code == 404:
            warn(f"    {date_str}: HTTP 404 (data not available); skip")
            return None
        if resp.status_code == 429:
            backoff = 60 * (2**attempt)  # 60, 120, 240 s
            warn(
                f"    HTTP 429 rate-limited; sleeping {backoff}s "
                f"(attempt {attempt+1}/{max_retries})"
            )
            time.sleep(backoff)
            continue
        if 500 <= resp.status_code < 600:
            backoff = 5 * (2**attempt)  # 5, 10, 20 s
            warn(
                f"    HTTP {resp.status_code} (attempt {attempt+1}/{max_retries}); "
                f"sleep {backoff}s"
            )
            time.sleep(backoff)
            continue
        # Other 4xx → log and abort the date (likely a bad parameter, no point retrying)
        warn(f"    HTTP {resp.status_code} for {date_str}: {resp.text[:200]}")
        return None
    warn(f"    {date_str}: exhausted {max_retries} retries; skip")
    return None


# ----- Per-region per-year file ingestion --------------------------------


def year_file_path(out_dir: Path, region_code: str, year: int) -> Path:
    return Path(out_dir) / f"{region_code}_{year}.parquet"


def _load_existing(year_path: Path) -> set[str]:
    """Return set of date strings already persisted in the file."""
    if not year_path.exists():
        return set()
    try:
        df = pd.read_parquet(year_path)
        return set(df["date"].astype(str).tolist())
    except Exception as e:
        warn(f"    could not read existing {year_path.name}: {e}; treating as empty")
        return set()


def ingest_region(
    api_key: str,
    region_code: str,
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    out_dir: Path,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    on_call: callable = None,
) -> dict[str, int]:
    """
    Fetch all daily records for one region between start_date and end_date
    (inclusive), persisting one Parquet file per calendar year. Resumable.

    Args:
        api_key: OpenWeather API key.
        region_code: AAGIS code, e.g. '121'.
        lat / lon: WGS84 coordinates of the region centroid.
        start_date / end_date: inclusive range (Python date objects).
        out_dir: directory for the per-year Parquet files.
        sleep_seconds: sleep between calls (default 1.05 s).
        on_call: optional callback(remaining_today: int, region: str, date_str: str)
                 invoked after each successful call. Caller can use this
                 to enforce daily-quota stop.

    Returns:
        {"fetched": int, "skipped_existing": int, "skipped_failed": int}
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group dates by year so we touch each per-year file only once at the end
    dates_by_year: dict[int, list[str]] = {}
    d = start_date
    while d <= end_date:
        dates_by_year.setdefault(d.year, []).append(d.isoformat())
        d += timedelta(days=1)

    fetched = 0
    skipped_existing = 0
    skipped_failed = 0

    for year, date_list in sorted(dates_by_year.items()):
        year_path = year_file_path(out_dir, region_code, year)
        already = _load_existing(year_path)
        new_rows: list[dict[str, Any]] = []
        log(
            f"  region {region_code} year {year}: "
            f"{len(date_list)} target dates, {len(already)} already cached"
        )

        for date_str in date_list:
            if date_str in already:
                skipped_existing += 1
                continue
            row = fetch_day_summary(api_key, lat, lon, date_str)
            if row is None:
                skipped_failed += 1
                # still sleep — preserves call rhythm in case of transient 5xx
                time.sleep(sleep_seconds)
                continue
            row["region_code"] = region_code
            new_rows.append(row)
            fetched += 1
            if on_call is not None:
                try:
                    on_call(region_code, date_str)
                except StopIteration:
                    # caller raised StopIteration to abort the run
                    if new_rows:
                        _append_and_save(year_path, new_rows)
                    raise
            time.sleep(sleep_seconds)

        if new_rows:
            _append_and_save(year_path, new_rows)
            ok(
                f"    region {region_code} year {year}: "
                f"wrote {len(new_rows)} new rows to {year_path.name}"
            )
        else:
            log(f"    region {region_code} year {year}: no new rows")

    return {
        "fetched": fetched,
        "skipped_existing": skipped_existing,
        "skipped_failed": skipped_failed,
    }


def _append_and_save(year_path: Path, new_rows: list[dict[str, Any]]) -> None:
    """Merge new rows with existing Parquet (if any) and atomic-write."""
    new_df = pd.DataFrame(new_rows)
    if year_path.exists():
        try:
            old_df = pd.read_parquet(year_path)
            df = pd.concat([old_df, new_df], ignore_index=True)
        except Exception:
            df = new_df
    else:
        df = new_df
    # De-dup on date (keep latest)
    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.sort_values("date").reset_index(drop=True)
    # Atomic write via tmp + rename
    tmp = year_path.with_suffix(year_path.suffix + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(year_path)


# ----- Sanity / inspection helpers ---------------------------------------


def summary_count_by_region_year(out_dir: Path) -> pd.DataFrame:
    """
    Tally how many days are persisted per (region, year). Used by the
    orchestrator's final reporting step.
    """
    out_dir = Path(out_dir)
    rows = []
    for f in sorted(out_dir.glob("*.parquet")):
        stem = f.stem  # e.g. '121_2022'
        try:
            region_code, year = stem.split("_")
            year = int(year)
        except ValueError:
            continue
        try:
            df = pd.read_parquet(f, columns=["date"])
            rows.append(
                {
                    "region_code": region_code,
                    "year": year,
                    "n_days": len(df),
                    "file": f.name,
                }
            )
        except Exception as e:
            warn(f"  could not summarise {f.name}: {e}")
    return (
        pd.DataFrame(rows).sort_values(["region_code", "year"]).reset_index(drop=True)
    )
