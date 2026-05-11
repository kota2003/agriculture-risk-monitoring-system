"""
src/io_utils.py — Robust I/O utilities for data ingestion.

This module exists because raw data files in this project come from
heterogeneous sources (Australian government, international agencies,
commercial APIs) with inconsistent encoding and NA conventions. Two
Project 4 lessons motivate the helpers here:

  - Lesson 8: UNDP HDR CSV ships as cp1252; default UTF-8 decoding crashed
              Phase 01. Wrap every `pd.read_csv` in encoding fallback.
  - Lesson 9: Pandas default NA detection silently converts the string
              "NA" (e.g., Namibia's country code) into NaN. Always use
              `keep_default_na=False` and explicit `na_values` for any
              column containing short categorical strings.

Usage:
    from src.io_utils import read_csv_safe

    df = read_csv_safe(path_to_csv)
    df = read_csv_safe(path_to_csv, na_values=["", "N/A", "-"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


# Encoding fallback order. UTF-8 first (the modern default); cp1252 covers
# many Australian / European government CSVs; latin-1 is a last-resort that
# never raises a decode error (it maps every byte to a character).
ENCODING_FALLBACK_ORDER: tuple[str, ...] = ("utf-8", "cp1252", "latin-1")


def read_csv_safe(
    path: str | Path,
    na_values: Iterable[str] | None = None,
    **read_csv_kwargs,
) -> pd.DataFrame:
    """
    Read a CSV with encoding fallback and conservative NA handling.

    Tries encodings in order: utf-8 -> cp1252 -> latin-1. The first one
    that decodes successfully is used. By default, pandas' aggressive NA
    auto-detection is disabled to prevent silent string-to-NaN conversion
    of values like "NA", "N/A", "null" in categorical columns. Provide
    explicit `na_values` to opt in to NA handling for specific tokens.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.
    na_values : iterable of str, optional
        Strings to interpret as NA. Default: empty string only.
        Pass an explicit list (e.g., ["", "N/A", "-"]) to widen.
    **read_csv_kwargs
        Forwarded to `pandas.read_csv`. Note that `encoding`,
        `keep_default_na`, and `na_values` are managed by this function;
        passing them in `read_csv_kwargs` will raise.

    Returns
    -------
    pandas.DataFrame
        The parsed CSV.

    Raises
    ------
    UnicodeDecodeError
        Only if all encodings in the fallback chain fail (very unlikely
        given latin-1's permissive byte mapping).
    ValueError
        If `read_csv_kwargs` contains a managed keyword.
    """
    managed = {"encoding", "keep_default_na", "na_values"}
    clash = managed & set(read_csv_kwargs)
    if clash:
        raise ValueError(
            f"read_csv_safe manages these kwargs; do not pass them: {sorted(clash)}"
        )

    path = Path(path)
    effective_na_values = list(na_values) if na_values is not None else [""]

    last_error: UnicodeDecodeError | None = None
    for encoding in ENCODING_FALLBACK_ORDER:
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                keep_default_na=False,
                na_values=effective_na_values,
                **read_csv_kwargs,
            )
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    # Should be unreachable because latin-1 cannot raise UnicodeDecodeError.
    raise last_error  # type: ignore[misc]


__all__ = ["read_csv_safe", "ENCODING_FALLBACK_ORDER"]
