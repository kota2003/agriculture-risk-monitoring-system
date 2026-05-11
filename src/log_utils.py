"""
src/log_utils.py — Lightweight, uniform console logging for scripts.

Provides a consistent print-style logging interface used across phase
step scripts and notebooks. Intentionally avoids Python's `logging`
module: phase scripts are short, single-use, and benefit from
unconditional stdout output that always reaches the user — no handler
configuration, no log level gymnastics.

Each log line follows a fixed shape:

    HH:MM:SS [LEVEL] message

Levels:
    INFO  — neutral progress information (default)
    OK    — successful step completion
    WARN  — non-fatal issue worth noticing
    ERROR — fatal problem; script likely exits next

Section helpers (`section`, `subsection`) emit visually distinct
separators to group related log lines.

Usage:
    from src.log_utils import log, ok, warn, error, section, subsection

    section("Phase 01 - Step 01: SILO ingestion")
    log("Fetching 1961-present daily climate data")
    rows = 12_345
    ok(f"Retrieved {rows:,} daily records")
    warn("3 region centroids returned partial coverage")
    error("ABARES region 42 returned no data; aborting")
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TextIO


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SEPARATOR_WIDTH: int = 72
_SECTION_CHAR: str = "="
_SUBSECTION_CHAR: str = "-"


def _now() -> str:
    """Return current time as HH:MM:SS string."""
    return datetime.now().strftime("%H:%M:%S")


def _emit(level: str, message: str, stream: TextIO) -> None:
    """Write a single formatted log line to the given stream."""
    print(f"{_now()} [{level:<5}] {message}", file=stream)


# ---------------------------------------------------------------------------
# Public API: level-based logging
# ---------------------------------------------------------------------------


def log(message: str) -> None:
    """Emit an INFO-level message to stdout."""
    _emit("INFO", message, sys.stdout)


def ok(message: str) -> None:
    """Emit an OK-level message to stdout (successful completion)."""
    _emit("OK", message, sys.stdout)


def warn(message: str) -> None:
    """Emit a WARN-level message to stderr (non-fatal issue)."""
    _emit("WARN", message, sys.stderr)


def error(message: str) -> None:
    """Emit an ERROR-level message to stderr (fatal problem)."""
    _emit("ERROR", message, sys.stderr)


# ---------------------------------------------------------------------------
# Public API: section separators
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    """Print a visually distinct section header to stdout."""
    bar = _SECTION_CHAR * _SEPARATOR_WIDTH
    print(bar)
    print(title)
    print(bar)


def subsection(title: str) -> None:
    """Print a visually distinct subsection header to stdout."""
    bar = _SUBSECTION_CHAR * _SEPARATOR_WIDTH
    print(bar)
    print(title)
    print(bar)


__all__ = ["log", "ok", "warn", "error", "section", "subsection"]
