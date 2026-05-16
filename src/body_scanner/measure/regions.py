"""SMPL-X vertex -> body region map, derived from skinning weights.

Each SMPL-X vertex has a 55-dim skinning weight vector. The argmax is the
"dominant joint" — the joint whose pose mostly drives that vertex. Grouping
those joints into anatomical regions gives a per-vertex region label.

Used by planar-slice recipes (PlanarGirth, PlanarArc, LateralChord) to keep
only the triangles inside the relevant body part. Without this, a horizontal
slice through e.g. the bicep at A-pose includes the torso ring too.

The mapping depends only on the SMPL-X model file, not on a specific fit,
so it is computed once and cached.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np


# SMPL-X joint indexing (body has 22, plus face=3, plus 30 hand joints).
JOINT = dict(
    pelvis=0, L_Hip=1, R_Hip=2, spine1=3, L_Knee=4, R_Knee=5,
    spine2=6, L_Ankle=7, R_Ankle=8, spine3=9, L_Foot=10, R_Foot=11,
    neck=12, L_Collar=13, R_Collar=14, head=15,
    L_Shoulder=16, R_Shoulder=17, L_Elbow=18, R_Elbow=19,
    L_Wrist=20, R_Wrist=21, jaw=22, L_eye=23, R_eye=24,
)
L_HAND_JOINTS = tuple(range(25, 40))
R_HAND_JOINTS = tuple(range(40, 55))


# Region -> set of joint indices.
REGIONS: dict[str, frozenset[int]] = {
    "torso": frozenset({JOINT[n] for n in (
        "pelvis", "spine1", "spine2", "spine3", "neck", "head",
        "L_Collar", "R_Collar",
        "jaw", "L_eye", "R_eye",
    )}),
    "torso_no_head": frozenset({JOINT[n] for n in (
        "pelvis", "spine1", "spine2", "spine3", "neck",
        "L_Collar", "R_Collar",
    )}),
    # Neck only — used to isolate neck-circumference slices. Excludes
    # collar/spine so the slice can't escape into the chest.
    "neck": frozenset({JOINT[n] for n in ("neck", "head", "jaw",
                                          "L_eye", "R_eye")}),
    "left_arm": frozenset(
        {JOINT[n] for n in ("L_Shoulder", "L_Elbow", "L_Wrist")}
        | set(L_HAND_JOINTS)
    ),
    "right_arm": frozenset(
        {JOINT[n] for n in ("R_Shoulder", "R_Elbow", "R_Wrist")}
        | set(R_HAND_JOINTS)
    ),
    "left_leg": frozenset(
        {JOINT[n] for n in ("L_Hip", "L_Knee", "L_Ankle", "L_Foot")}
    ),
    "right_leg": frozenset(
        {JOINT[n] for n in ("R_Hip", "R_Knee", "R_Ankle", "R_Foot")}
    ),
}


@lru_cache(maxsize=4)
def vertex_dominant_joint(model_folder: str = "data/body_models",
                          gender: str = "female") -> np.ndarray:
    """Return shape (10475,) of dominant-joint-index per vertex."""
    import smplx
    bm = smplx.create(
        model_path=model_folder, model_type="smplx", gender=gender,
        use_pca=False, batch_size=1,
    )
    return bm.lbs_weights.detach().numpy().argmax(axis=1)


def region_vertex_mask(
    region_names: tuple[str, ...],
    model_folder: str = "data/body_models",
    gender: str = "female",
) -> np.ndarray:
    """Bool mask over all 10475 SMPL-X verts: True if the vertex's
    dominant joint belongs to ANY of the named regions. Regions can
    overlap (e.g. neck verts are members of both 'torso' and 'neck')."""
    dom = vertex_dominant_joint(model_folder, gender)
    joints: set[int] = set()
    for r in region_names:
        if r in REGIONS:
            joints |= REGIONS[r]
    return np.isin(dom, list(joints))


# Backwards-compatibility: callers using vertex_to_region get the legacy
# first-match label assignment, but new code should prefer
# region_vertex_mask which handles overlapping regions correctly.
@lru_cache(maxsize=4)
def vertex_to_region(model_folder: str = "data/body_models",
                     gender: str = "female") -> np.ndarray:
    dom = vertex_dominant_joint(model_folder, gender)
    labels = np.full(len(dom), "", dtype=object)
    for region_name, joint_set in REGIONS.items():
        mask = np.isin(dom, list(joint_set))
        unlabelled = labels == ""
        labels[mask & unlabelled] = region_name
    return labels
