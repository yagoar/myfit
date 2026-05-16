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


# SMPL-X joint indices, in the order returned by smplx body_model().joints.
# Source: smplx.body_models.SMPLX. Body joints 0..21, then jaw, eyes, hands.
SMPLX_JOINT_INDEX = {
    "pelvis": 0, "L_Hip": 1, "R_Hip": 2, "spine1": 3, "L_Knee": 4,
    "R_Knee": 5, "spine2": 6, "L_Ankle": 7, "R_Ankle": 8, "spine3": 9,
    "L_Foot": 10, "R_Foot": 11, "neck": 12, "L_Collar": 13, "R_Collar": 14,
    "head": 15, "L_Shoulder": 16, "R_Shoulder": 17, "L_Elbow": 18,
    "R_Elbow": 19, "L_Wrist": 20, "R_Wrist": 21,
}


# Landmarks whose verified vertex IDs sit on heavily arm-driven vertices.
# Populating an entry here overrides the vertex with the named SMPL-X joint
# position (pose-invariant rotation centre).
#
# WARNING: joint positions are INTERNAL (rotation centres ~5cm inboard from
# the skin). Overriding e.g. acromion shifts surface-tape measurements like
# B01 width inward by ~9cm. Use only for landmarks where geodesic-endpoint
# stability under pose matters more than surface accuracy.
#
# Empty by default. The `joint.L_Shoulder` syntax remains available for
# explicit opt-in inside recipes.
JOINT_OVERRIDES: dict[str, str] = {}


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

    # "Level" landmarks — symbolic horizontal planes referenced in merged.yaml
    # and the Seamly catalog. We represent each as a single 3D point whose
    # y-coordinate defines the horizontal slice; x/z carry no meaning when
    # used as a plane origin.
    "bust_level": ("alias", ["bust_apex_midpoint"]),
    "upper_bust_level": ("alias", ["armscye_front_midpoint"]),
    "armpit_level": ("alias", ["upper_bust_level"]),  # per extraction_audit.md
    "highbust_level": ("alias", ["armfold_front_left"]),  # armfold height
    "crotch_level": ("alias", ["crotch_midpoint"]),
    "mid_knee_level": ("midpoint", ["knee_back_left", "knee_back_right"]),
    "ankle_level": ("midpoint",
                    ["ankle_bone_lateral_left", "ankle_bone_lateral_right"]),
    "lowbust_level": ("alias", ["lowbust_apex"]),
    "mid_neck_level": ("alias", ["mid_neck_front"]),
    # neck_base_level: front_neck_point sits at the throat hollow, BELOW the
    # actual neck cylinder (no neck-region verts exist at that Y on most
    # bodies). Shift up 2.5cm to land in the neck proper for clean slicing.
    "neck_base_level": ("offset_y", ["front_neck_point", "0.025"]),
    # high_hip_level: rule per dpm pants_1 = 4-5" below waist (~11cm). Use a
    # fixed mid-value here; refine when scan calibration validates.
    # Stored as point with y = waist_cf.y - 0.11; x/z unused as plane origin.
    "high_hip_level": ("offset_y", ["waist_string", "-0.11"]),
    # low_hip_level: dpm "widest girth below waist". For scaffolding we use
    # 20cm below the waist as a placeholder horizontal level; the proper
    # implementation searches for the maximum-girth slice in a Y range.
    "low_hip_level": ("offset_y", ["waist_string", "-0.20"]),
}


@dataclass(frozen=True)
class LandmarkSet:
    """Resolved 3D points for every named landmark on a specific mesh."""

    verts: np.ndarray  # (V, 3) fitted SMPL-X vertices
    vertex_ids: dict[str, int]  # leaf name -> vertex id
    joints: np.ndarray | None = None  # (J, 3) fitted SMPL-X joint positions

    def __getitem__(self, name: str) -> np.ndarray:
        """Resolve `landmarks.<leaf>`, `joint.<NAME>`, or bare `<leaf>` to
        a 3D point."""
        if name.startswith("joint."):
            return self._joint(name.split(".", 1)[1])
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name

        if leaf in JOINT_OVERRIDES and self.joints is not None:
            return self._joint(JOINT_OVERRIDES[leaf])

        if leaf in self.vertex_ids:
            return self.verts[self.vertex_ids[leaf]]

        if leaf in COMPOUND_LANDMARKS:
            op, bases = COMPOUND_LANDMARKS[leaf]
            if op == "offset_y":
                base = self[bases[0]]
                dy = float(bases[1])
                return np.array([base[0], base[1] + dy, base[2]])
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
        if name.startswith("joint."):
            return (self.joints is not None
                    and name.split(".", 1)[1] in SMPLX_JOINT_INDEX)
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name
        if leaf in JOINT_OVERRIDES and self.joints is not None:
            return True
        return leaf in self.vertex_ids or leaf in COMPOUND_LANDMARKS

    def _joint(self, joint_name: str) -> np.ndarray:
        if self.joints is None:
            raise KeyError(
                f"joint.{joint_name} requested but LandmarkSet was built "
                "without joints — pass `joints=fit['smplx_joints']` to "
                "build_landmark_set."
            )
        if joint_name not in SMPLX_JOINT_INDEX:
            raise KeyError(f"unknown SMPL-X joint name {joint_name!r}")
        return self.joints[SMPLX_JOINT_INDEX[joint_name]]


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
    joints: np.ndarray | None = None,
) -> LandmarkSet:
    """Construct a LandmarkSet from a fitted SMPL-X mesh + verified IDs.

    `joints` is the (J, 3) array from a fit (e.g. fit['smplx_joints']);
    when supplied, it enables `joint.X` resolution and the JOINT_OVERRIDES
    fallback (acromion -> L_Shoulder, etc.)."""
    return LandmarkSet(
        verts=fitted_verts,
        vertex_ids=load_vertex_ids(review_json),
        joints=joints,
    )
