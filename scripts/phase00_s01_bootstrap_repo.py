"""
Phase 00 - Step 01: Bootstrap repository structure.

Purpose:
    Idempotently create the initial directory structure defined in
    project_scope.md (v3) Appendix A. Places .gitkeep in empty
    directories so they can be tracked by git. Creates empty
    __init__.py files in src/ subpackages.

    This script does NOT create:
      - .gitignore, LICENSE, .python-version, .pre-commit-config.yaml
        (handled by Step 02)
      - requirements.txt, requirements-dev.txt, .venv
        (handled by Step 03)
      - src/ module contents (paths.py, io_utils.py, log_utils.py)
        (handled by Step 04)
      - documentation files
        (handled by Steps 05-07)

Inputs:
    None. Reads only its own resolved path to determine the
    repository root (assumes this script lives in <repo>/scripts/
    or is run from <repo>/).

Outputs:
    Directory tree under <repo>/, with .gitkeep and __init__.py
    placeholder files. Stdout: a per-path status line for each
    operation (CREATED / EXISTS).

Idempotent:
    Re-running this script after any successful run is safe.
    Existing files are never overwritten.

Usage (from repository root):
    python scripts/phase00_s01_bootstrap_repo.py

    Or, if the script is at the repo root before scripts/ exists:
    python phase00_s01_bootstrap_repo.py

Author: Kota (Phase 00, Project 5)
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

# Reproducibility (no stochasticity in this step, but convention applies)
SEED = 42
random.seed(SEED)
np.random.seed(SEED)


# ---------------------------------------------------------------------------
# Configuration: directory tree to create
# ---------------------------------------------------------------------------

# Directories that should exist with a .gitkeep so git tracks them
# even when otherwise empty.
DIRS_WITH_GITKEEP: list[str] = [
    "data/raw",
    "data/processed",
    "notebooks",
    "scripts",
    "outputs/figures",
    "outputs/tables",
    "outputs/models",
    "docs/phase_summaries",
    ".vscode",
]

# src/ subpackages: each gets an empty __init__.py (no .gitkeep needed
# because __init__.py itself makes the directory tracked).
SRC_PACKAGES: list[str] = [
    "src",
    "src/ingestion",
    "src/processing",
    "src/indicators",
    "src/models",
    "src/viz",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve_repo_root() -> Path:
    """
    Determine repository root.

    Strategy:
        If this script lives in <repo>/scripts/, repo root is parent of
        scripts. Otherwise assume the script's parent is repo root.
    """
    script_path = Path(__file__).resolve()
    if script_path.parent.name == "scripts":
        return script_path.parent.parent
    return script_path.parent


def ensure_dir(path: Path) -> str:
    """Create a directory. Returns 'CREATED' or 'EXISTS'."""
    if path.exists():
        return "EXISTS"
    path.mkdir(parents=True, exist_ok=False)
    return "CREATED"


def ensure_empty_file(path: Path) -> str:
    """
    Create an empty file if it doesn't exist.
    Returns 'CREATED' or 'EXISTS'.
    """
    if path.exists():
        return "EXISTS"
    path.touch(exist_ok=False)
    return "CREATED"


def log(label: str, status: str, path: Path, repo_root: Path) -> None:
    """Print a uniformly formatted status line."""
    rel = path.relative_to(repo_root).as_posix()
    print(f"  [{status:<7}] {label:<12} {rel}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    repo_root = resolve_repo_root()

    print("=" * 72)
    print("Phase 00 - Step 01: Bootstrap repository structure")
    print("=" * 72)
    print(f"Repository root: {repo_root}")
    print()

    # Sanity check: are we at the right place? We expect to find .git/.
    git_dir = repo_root / ".git"
    if not git_dir.is_dir():
        print(
            f"WARNING: No .git/ directory found at {repo_root}.\n"
            "         This script expects to run inside an initialised\n"
            "         git repository. Continuing anyway, but please verify\n"
            "         the repo_root above is correct."
        )
        print()

    # --- 1. Create directories with .gitkeep ---
    print("[1/2] Directories with .gitkeep")
    print("-" * 72)
    for rel in DIRS_WITH_GITKEEP:
        d = repo_root / rel
        dir_status = ensure_dir(d)
        log("dir", dir_status, d, repo_root)
        gk = d / ".gitkeep"
        gk_status = ensure_empty_file(gk)
        log("gitkeep", gk_status, gk, repo_root)
    print()

    # --- 2. src/ subpackages: empty __init__.py ---
    print("[2/2] src/ subpackages with __init__.py")
    print("-" * 72)
    for rel in SRC_PACKAGES:
        d = repo_root / rel
        dir_status = ensure_dir(d)
        log("dir", dir_status, d, repo_root)
        init = d / "__init__.py"
        init_status = ensure_empty_file(init)
        log("__init__", init_status, init, repo_root)
    print()

    # --- Summary ---
    print("=" * 72)
    print("Done.")
    print("Next: Step 02 (generate .gitignore, LICENSE, .python-version,")
    print("              .pre-commit-config.yaml)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
