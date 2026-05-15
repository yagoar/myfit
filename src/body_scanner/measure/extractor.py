"""Measurement extractor — loads merged.yaml and runs recipes on a fitted mesh.

Returns a dict {measurement_name: value_cm}. Skips entries with unimplemented
types (geodesic_path, contoured_path, table_lookup, user_input) until the
corresponding recipes are wired. `derived` entries are computed after all
primary measurements so they can reference them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .landmarks import LandmarkSet, build_landmark_set
from .recipes import RECIPE_DISPATCH, derived


DEFAULT_YAML = Path("src/body_scanner/measure/definitions/merged.yaml")


@dataclass
class ExtractionReport:
    values: dict[str, float]
    skipped: dict[str, str]  # name -> reason


def _list_landmark_refs(params: dict) -> list[str]:
    """Collect every dotted `landmarks.X` reference inside the params tree."""
    refs: list[str] = []

    def walk(node):
        if isinstance(node, str):
            if node.startswith("landmarks."):
                refs.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(params)
    return refs


def extract(
    fitted_verts: np.ndarray,
    smplx_faces: np.ndarray,
    yaml_path: Path | str = DEFAULT_YAML,
    review_json: Path | str | None = None,
    only: set[str] | None = None,
    joints: np.ndarray | None = None,
) -> ExtractionReport:
    """Run the extractor end-to-end.

    fitted_verts:  (V, 3) SMPL-X vertices after fitting (numpy)
    smplx_faces:   (F, 3) SMPL-X mesh faces (numpy)
    yaml_path:     measurement definitions
    review_json:   verified landmark vertex IDs (defaults to repo path)
    only:          if set, only compute measurements whose name is in this set
    """
    spec = yaml.safe_load(Path(yaml_path).read_text())
    rj = review_json if review_json is not None else None
    landmarks = (
        build_landmark_set(fitted_verts, rj, joints=joints) if rj is not None
        else build_landmark_set(fitted_verts, joints=joints)
    )

    values: dict[str, float] = {}
    skipped: dict[str, str] = {}

    # First pass: primary recipes (planar_slice / planar_segment).
    entries = spec.get("measurements", [])
    for entry in entries:
        name = entry["name"]
        if only is not None and name not in only:
            continue
        mtype = entry.get("type")
        if mtype == "derived":
            continue  # deferred to second pass
        recipe = RECIPE_DISPATCH.get(mtype)
        if recipe is None:
            skipped[name] = f"type {mtype!r} not yet implemented"
            continue
        params = entry.get("parameters", {})
        # Check that every referenced landmark exists.
        refs = _list_landmark_refs(params)
        missing = [r for r in refs if not landmarks.has(r)]
        if missing:
            skipped[name] = f"missing landmark(s): {', '.join(missing)}"
            continue
        try:
            v = recipe(fitted_verts, smplx_faces, landmarks, params)
        except Exception as e:
            skipped[name] = f"recipe error: {type(e).__name__}: {e}"
            continue
        if np.isnan(v):
            skipped[name] = "recipe returned NaN"
            continue
        values[name] = v

    # Second pass: derived.
    for entry in entries:
        name = entry["name"]
        if only is not None and name not in only:
            continue
        if entry.get("type") != "derived":
            continue
        try:
            v = derived(
                fitted_verts,
                smplx_faces,
                landmarks,
                entry.get("parameters", {}),
                values,
            )
        except Exception as e:
            skipped[name] = f"derived error: {type(e).__name__}: {e}"
            continue
        values[name] = v

    return ExtractionReport(values=values, skipped=skipped)
