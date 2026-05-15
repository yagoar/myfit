"""Landmark resolver: symbolic name -> 3D point on the fitted SMPL-X mesh.

Sources:
  - references/smplx_landmark_review.json  (verified vertex IDs per
    GUARDRAILS section 3; the user signed off on each in Blender)
  - this module's COMPOUND_LANDMARKS dict (midpoints, axes derived from
    base landmarks — no new vertex IDs invented)

The schema in merged.yaml uses dotted names like `landmarks.bust_apex_left`
and `landmarks.bust_apex_midpoint`. Resolution is mechanical: split on the
dot, look up the leaf name in the verified-IDs map or in COMPOUND_LANDMARKS.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEFAULT_REVIEW_JSON = Path("references/smplx_landmark_review.json")


# Compound landmarks: name -> (operation, [base_names])
# Resolved by computing on the base landmarks' 3D coordinates.
COMPOUND_LANDMARKS: dict[str, tuple[str, list[str]]] = {
    "bust_apex_midpoint": ("midpoint", ["bust_apex_left", "bust_apex_right"]),
    "armscye_back_midpoint": (
        "midpoint",
        ["armscye_back_left", "armscye_back_right"],
    ),
    "armscye_front_midpoint": (
        "midpoint",
        ["armscye_front_left", "armscye_front_right"],
    ),
    "shoulder_neck_midpoint": (
        "midpoint",
        ["shoulder_neck_left", "shoulder_neck_right"],
    ),
    "waist_side_midpoint": (
        "midpoint",
        ["waist_side_left", "waist_side_right"],
    ),
    # waist_string: a horizontal ring sitting at the natural waist. As an
    # anchor *point* we use the centre-front waist (Aldrich ties the string
    # there). The plane it defines uses the y-coordinate of this point.
    "waist_string": ("alias", ["waist_cf"]),

    # "Level" landmarks — symbolic horizontal planes referenced in merged.yaml.
    # We represent each as a single 3D point whose y-coordinate defines the
    # horizontal slice; x/z carry no meaning when used as a plane origin.
    "bust_level": ("alias", ["bust_apex_midpoint"]),
    "upper_bust_level": ("alias", ["armscye_front_midpoint"]),
    "crotch_level": ("alias", ["crotch_midpoint"]),
    "mid_knee_level": ("midpoint", ["knee_back_left", "knee_back_right"]),
    "ankle_level": ("midpoint",
                    ["ankle_bone_lateral_left", "ankle_bone_lateral_right"]),
}


@dataclass(frozen=True)
class LandmarkSet:
    """Resolved 3D points for every named landmark on a specific mesh."""

    verts: np.ndarray  # (V, 3) fitted SMPL-X vertices
    vertex_ids: dict[str, int]  # leaf name -> vertex id

    def __getitem__(self, name: str) -> np.ndarray:
        """Resolve `landmarks.<leaf>` or bare `<leaf>` to a 3D point."""
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name

        if leaf in self.vertex_ids:
            return self.verts[self.vertex_ids[leaf]]

        if leaf in COMPOUND_LANDMARKS:
            op, bases = COMPOUND_LANDMARKS[leaf]
            pts = np.stack([self[b] for b in bases])
            if op == "midpoint":
                return pts.mean(axis=0)
            if op == "alias":
                return pts[0]
            raise ValueError(f"unknown compound op {op!r} for {leaf!r}")

        raise KeyError(
            f"landmark {leaf!r} is neither a verified vertex ID nor a "
            "compound landmark. Add it to references/smplx_landmark_review.json "
            "(via Blender review) or to COMPOUND_LANDMARKS in this file."
        )

    def has(self, name: str) -> bool:
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name
        return leaf in self.vertex_ids or leaf in COMPOUND_LANDMARKS


def load_vertex_ids(path: Path | str = DEFAULT_REVIEW_JSON) -> dict[str, int]:
    """Read the verified vertex IDs (with any status — confirmed, corrected,
    mirrored). Skipped entries are dropped."""
    raw = json.loads(Path(path).read_text())
    out: dict[str, int] = {}
    for name, rec in raw.items():
        if rec.get("status") == "skipped":
            continue
        out[name] = int(rec["vertex_id"])
    return out


def build_landmark_set(
    fitted_verts: np.ndarray,
    review_json: Path | str = DEFAULT_REVIEW_JSON,
) -> LandmarkSet:
    """Construct a LandmarkSet from a fitted SMPL-X mesh + verified IDs."""
    return LandmarkSet(verts=fitted_verts, vertex_ids=load_vertex_ids(review_json))
