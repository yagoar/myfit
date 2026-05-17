"""Static config for the GUI: choices, paths, Python interpreter selection.

Kept dependency-free so it can be imported from tests without needing
Flask or the body-scanner pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root is two levels above this file: <root>/src/body_scanner/gui/.
REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_SCAN = REPO_ROOT / "scripts" / "run_scan.py"
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "results"
DEFAULT_CAPTURES_DIR = REPO_ROOT / "data" / "captures"

# The GUI may run under any Python that has Flask + Jinja, but the
# pipeline subprocess needs the project's venv (torch, smplx, open3d,
# trimesh, …). Prefer the venv's interpreter when present.
_VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PIPELINE_PY: str = str(_VENV_PY) if _VENV_PY.is_file() else sys.executable

WAIST_COLORS: tuple[str, ...] = (
    "none", "red", "cyan", "green",
    "magenta", "yellow", "blue", "orange",
)

# Label → run_scan --pattern-system value. Order is the dropdown order.
PATTERN_SYSTEMS: tuple[tuple[str, str], ...] = (
    ("aldrich", "Aldrich (5th ed.)"),
    ("dpm", "dpm (dresspatternmaking.com)"),
    ("all", "Both (Aldrich + dpm)"),
    ("seamly_only", "Seamly catalog only"),
)
VALID_PATTERN_SYSTEMS: frozenset[str] = frozenset(v for v, _ in PATTERN_SYSTEMS)
