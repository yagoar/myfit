"""Run the Seamly catalog extractor over a fitted SMPL-X mesh.

Two-pass: primary recipes first, then formula-only entries that may reference
primary outputs. Returns a dict {seamly_code: value_cm} plus a skipped map.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .landmarks import build_landmark_set
from .seamly_catalog import FORMULAS, JUDGMENT_OR_STANDARD, RECIPES


@dataclass
class CatalogReport:
    values: dict[str, float]
    skipped: dict[str, str]


def extract_catalog(
    fitted_verts: np.ndarray,
    smplx_faces: np.ndarray,
    review_json: str | Path | None = None,
    joints: np.ndarray | None = None,
    waist_y_override: float | None = None,
) -> CatalogReport:
    if review_json is not None:
        landmarks = build_landmark_set(
            fitted_verts, review_json, joints=joints, faces=smplx_faces,
            waist_y_override=waist_y_override,
        )
    else:
        landmarks = build_landmark_set(
            fitted_verts, joints=joints, faces=smplx_faces,
            waist_y_override=waist_y_override,
        )
    values: dict[str, float] = {}
    skipped: dict[str, str] = {}

    # Pass 1 — primary recipes (Height / PlanarGirth / etc.).
    for code, recipe in RECIPES.items():
        try:
            v = recipe.compute(fitted_verts, smplx_faces, landmarks)
        except KeyError as e:
            skipped[code] = f"missing landmark {e!s}"
            continue
        except Exception as e:
            skipped[code] = f"{type(e).__name__}: {e}"
            continue
        if not np.isfinite(v):
            skipped[code] = "non-finite result"
            continue
        values[code] = v

    # Pass 2 — formulas.
    for code, recipe in FORMULAS.items():
        try:
            v = recipe.compute_from(values)
        except Exception as e:
            skipped[code] = f"formula error: {type(e).__name__}: {e}"
            continue
        if not np.isfinite(v):
            skipped[code] = "non-finite result"
            continue
        values[code] = v

    # Pass 3 — record judgment/standard codes as skipped with reason.
    for code, reason in JUDGMENT_OR_STANDARD.items():
        if code not in values and code not in skipped:
            skipped[code] = reason

    return CatalogReport(values=values, skipped=skipped)
