"""Static config for the GUI: choices, paths, Python interpreter selection.

Kept dependency-free so it can be imported from tests without needing
Flask or the tailor-twin pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root is two levels above this file: <root>/src/tailor_twin/gui/.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "results"
DEFAULT_CAPTURES_DIR = REPO_ROOT / "data" / "captures"

# The GUI may run under any Python that has Flask + Jinja, but the
# pipeline subprocess needs the project's venv (torch, smplx, open3d,
# trimesh, …). Prefer the venv's interpreter when present.
_VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PIPELINE_PY: str = str(_VENV_PY) if _VENV_PY.is_file() else sys.executable

# Pipeline entrypoint = ``python -m tailor_twin.scan``. Kept as a list
# so :func:`build_cmd` can prepend it to argv without re-deriving on
# every request.
RUN_SCAN_ARGS: tuple[str, ...] = ("-m", "tailor_twin.scan")

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

# Gender values match SeamlyMe (Seamly2D/src/libs/vformat/measurements.cpp):
# {"male", "female", "unknown"}. Only "female" is currently usable
# because we ship only SMPLX_FEMALE.npz under data/body_models/smplx/.
# The HTML disables the others; ``VALID_GENDERS`` here mirrors what the
# backend accepts so the SMIS export keeps working if a future scan
# enables them.
GENDERS: tuple[tuple[str, str, bool], ...] = (
    # (value, label, enabled?)
    ("female",  "Female",  True),
    ("male",    "Male — SMPL-X model not present", False),
    ("unknown", "Unknown — SMPL-X model not present", False),
)
VALID_GENDERS: frozenset[str] = frozenset(v for v, _, _ in GENDERS)
ENABLED_GENDERS: frozenset[str] = frozenset(v for v, _, e in GENDERS if e)
