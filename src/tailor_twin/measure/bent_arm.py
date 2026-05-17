"""Re-pose SMPL-X with the left elbow flexed so bent-arm measurements
(L01 acromion→wrist, L02 acromion→elbow, L04 elbow girth, L03 = L01-L02)
can be computed on a body that actually has a bent arm.

A-pose scans don't capture bent-elbow geometry. Rather than require a
second scan, we re-evaluate the SMPL-X body model with the L_Elbow
joint rotated ~80° from its T-pose / fit-pose orientation and the
L_Shoulder rotated forward by ~30° so the forearm doesn't collide with
the torso. Per-vertex displacement (SMPL-X+D) is reused unchanged.

This module is the single source of truth for the bent-arm pose used
both by `scripts/extract_bent_arm.py` (standalone tool that saves a
bent npz + json) and by `tailor_twin.measure.cli` (the bent-arm
override inside the catalog extractor).

Caveats:
  * SMPL-X pose blend shapes deform skin at the elbow but do NOT
    simulate flexed-muscle bulge — elbow girth may be off by ~1-2 cm
    vs a real bent-arm scan.
  * The fitted displacement was solved in A-pose, so artefacts on the
    arm in the bent pose are possible but small.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


# SMPL-X joint -> body_pose row index mapping. body_pose is (21, 3)
# axis-angle (Rodrigues); joint 0 is pelvis (global_orient, not in
# body_pose), so SMPL-X joint N maps to body_pose row N-1.
L_ELBOW_BODY_POSE_INDEX = 17     # SMPL-X joint 18 (L_Elbow)
L_SHOULDER_BODY_POSE_INDEX = 15  # SMPL-X joint 16 (L_Shoulder)


# Defaults shared by both call sites — Seamly tailoring pose: forearm
# vertical in front of the body, biceps still at the side, elbow
# pointing back.
DEFAULT_ELBOW_FLEX_DEG = 80.0
DEFAULT_ELBOW_AXIS = "0,-1,0"          # local -Y in L_Elbow frame
DEFAULT_SHOULDER_FORWARD_DEG = 30.0    # rotation around world X


@dataclass(frozen=True)
class BentArmPose:
    """Bent-arm pose result: re-posed mesh + the axis-angle vectors that
    produced it, so callers can write the same pose back to disk."""
    verts: np.ndarray         # (V, 3) bent mesh, displacement baked in
    joints: np.ndarray        # (J, 3) bent joints
    elbow_aa: np.ndarray      # (3,) axis-angle applied to L_Elbow
    shoulder_aa: np.ndarray   # (3,) axis-angle applied to L_Shoulder


def _parse_axis(axis_str: str) -> np.ndarray:
    """Parse 'x,y,z' -> unit float32 3-vector. Raises on degenerate axis."""
    axis = np.array([float(c) for c in axis_str.split(",")], dtype=np.float32)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-9:
        raise ValueError(f"degenerate elbow axis {axis_str!r}")
    return axis / norm


def build_bent_pose_axis_angles(
    fit_body_pose: np.ndarray,
    elbow_flex_deg: float = DEFAULT_ELBOW_FLEX_DEG,
    elbow_axis: str = DEFAULT_ELBOW_AXIS,
    shoulder_forward_deg: float = DEFAULT_SHOULDER_FORWARD_DEG,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the L_Elbow and L_Shoulder axis-angle vectors to overlay on
    the fitted body_pose so the left arm is flexed at the elbow with
    the shoulder rotated forward.

    Returns (elbow_aa, shoulder_aa), both float32 shape (3,).
    """
    theta = np.deg2rad(elbow_flex_deg)
    elbow_aa = (_parse_axis(elbow_axis) * theta).astype(np.float32)

    shoulder_aa = fit_body_pose[L_SHOULDER_BODY_POSE_INDEX].copy().astype(
        np.float32)
    shoulder_aa[0] += np.deg2rad(shoulder_forward_deg)
    return elbow_aa, shoulder_aa


def repose_bent_arm(
    fit: dict | np.lib.npyio.NpzFile,
    body_model,
    *,
    elbow_flex_deg: float = DEFAULT_ELBOW_FLEX_DEG,
    elbow_axis: str = DEFAULT_ELBOW_AXIS,
    shoulder_forward_deg: float = DEFAULT_SHOULDER_FORWARD_DEG,
) -> BentArmPose:
    """Re-pose `body_model` with the fitted shape (betas + displacement)
    and a bent left elbow / shoulder, returning the deformed mesh.

    `fit` must expose 'betas', 'body_pose', 'global_orient', 'transl'
    and (optionally) 'displacement'. Accepts an npz handle or a dict.

    The body_model's faces are NOT returned — callers already have them.
    """
    betas_t = torch.tensor(fit["betas"][None], dtype=torch.float32)
    body_pose = np.asarray(fit["body_pose"])
    body_pose_t = torch.tensor(body_pose[None], dtype=torch.float32)
    global_orient_t = torch.tensor(fit["global_orient"][None],
                                   dtype=torch.float32)
    transl_t = torch.tensor(fit["transl"][None], dtype=torch.float32)

    elbow_aa, shoulder_aa = build_bent_pose_axis_angles(
        body_pose,
        elbow_flex_deg=elbow_flex_deg,
        elbow_axis=elbow_axis,
        shoulder_forward_deg=shoulder_forward_deg,
    )
    body_pose_t[0, L_ELBOW_BODY_POSE_INDEX] = torch.tensor(elbow_aa)
    body_pose_t[0, L_SHOULDER_BODY_POSE_INDEX] = torch.tensor(shoulder_aa)

    with torch.no_grad():
        out = body_model(
            betas=betas_t,
            body_pose=body_pose_t.reshape(1, -1),
            global_orient=global_orient_t,
            transl=transl_t,
            return_verts=True,
        )
    verts = out.vertices.detach().numpy()[0]
    joints = out.joints.detach().numpy()[0]

    disp = _maybe_displacement(fit)
    if disp is not None and disp.shape == verts.shape:
        verts = verts + disp

    return BentArmPose(verts=verts, joints=joints,
                       elbow_aa=elbow_aa, shoulder_aa=shoulder_aa)


def _maybe_displacement(fit) -> np.ndarray | None:
    """Return the per-vertex displacement field if the fit has one."""
    # NpzFile exposes `.files`; plain dicts use `in`.
    if hasattr(fit, "files"):
        if "displacement" in fit.files:
            return np.asarray(fit["displacement"])
        return None
    if isinstance(fit, dict) and "displacement" in fit:
        return np.asarray(fit["displacement"])
    return None
