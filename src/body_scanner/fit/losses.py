"""Losses for SMPL-X mesh-to-mesh fitting.

Conventions follow SMPLify-X (https://github.com/vchoutas/smplify-x):
  - shape prior:  L2 on betas
  - pose prior:   L2 on body_pose (substitute for VPoser embedding L2 when
                  VPoser ckpt unavailable). SMPLify-X uses
                  `pose_embedding.pow(2).sum() * body_pose_weight**2`.
  - angle prior:  penalises elbow/knee hyperextension. Following
                  SMPLify-X `fitting.py`, applied to body_pose[3:66] of the
                  full pose representation; here we apply directly to the
                  bend axis of the four joints.

The data term replaces SMPLify-X 2D keypoint loss with bidirectional
nearest-neighbour chamfer (vertex-based). This is the standard
adaptation when fitting SMPL-X to a target mesh / point cloud.
"""
from __future__ import annotations

import numpy as np
import torch
from scipy.spatial import cKDTree


# SMPL-X body_pose layout (axis-angle, 21 joints * 3, excludes global_orient):
#   0: L_Hip   1: R_Hip   2: spine1   3: L_Knee   4: R_Knee   5: spine2
#   6: L_Ankle 7: R_Ankle 8: spine3   9: L_Foot  10: R_Foot  11: neck
#  12: L_Collar 13: R_Collar 14: head 15: L_Shoulder 16: R_Shoulder
#  17: L_Elbow 18: R_Elbow 19: L_Wrist 20: R_Wrist
L_KNEE_IDX = 3
R_KNEE_IDX = 4
L_ELBOW_IDX = 17
R_ELBOW_IDX = 18


def crop_scan_for_chamfer(
    scan_verts,
    drop_above_y_frac: float = 0.90,
    drop_below_y_frac: float = 0.02,
):
    """Drop hair/face verts (top fraction of Y) and toe/floor verts (bottom).

    Hair on the scan attracts SMPL-X head verts and warps the fit.
    SMPL-X has no hair. drop_above_y_frac=0.90 means drop everything in the
    top 10% of the body height. drop_below_y_frac=0.02 drops the bottom 2%
    (toes / floor artefacts).

    Returns a boolean mask the same length as scan_verts.
    """
    import numpy as np
    y = scan_verts[:, 1]
    y_min, y_max = float(y.min()), float(y.max())
    height = y_max - y_min
    keep_max = y_min + drop_above_y_frac * height
    keep_min = y_min + drop_below_y_frac * height
    return (y >= keep_min) & (y <= keep_max)


def pose_prior_z_l2(z: "torch.Tensor") -> "torch.Tensor":
    """SMPLify-X's VPoser pose prior: L2 on the 32D latent embedding."""
    return (z ** 2).sum()


def chamfer_bidirectional(
    smplx_verts: torch.Tensor,
    scan_verts: torch.Tensor,
    scan_tree: cKDTree,
) -> torch.Tensor:
    """Bidirectional point-to-point chamfer between SMPL-X mesh and scan.

    smplx_verts:  (V_smplx, 3)  — differentiable
    scan_verts:   (V_scan, 3)   — fixed tensor on same device
    scan_tree:    cKDTree over scan_verts.cpu().numpy() — fixed
    """
    # SMPL-X -> scan: query the (fixed) scan tree with detached SMPL-X verts
    with torch.no_grad():
        _, idx_s2p = scan_tree.query(smplx_verts.detach().cpu().numpy())
    target_for_smplx = scan_verts[idx_s2p]
    loss_a = ((smplx_verts - target_for_smplx) ** 2).sum(-1).mean()

    # scan -> SMPL-X: rebuild a tree on detached SMPL-X each iter
    with torch.no_grad():
        smplx_tree = cKDTree(smplx_verts.detach().cpu().numpy())
        _, idx_p2s = smplx_tree.query(scan_verts.detach().cpu().numpy())
    target_for_scan = smplx_verts[idx_p2s]
    loss_b = ((scan_verts - target_for_scan) ** 2).sum(-1).mean()

    return loss_a + loss_b


def shape_prior(betas: torch.Tensor) -> torch.Tensor:
    """L2 prior on betas — SMPLify-X uses torch.sum(self.shape_prior(betas))
    with a learned MoG; we use plain L2 (Gaussian, sigma=1) which matches the
    well-formed prior for the first few PC components."""
    return (betas ** 2).sum()


def pose_prior_l2(body_pose: torch.Tensor) -> torch.Tensor:
    """L2 prior on body_pose. Substitute for VPoser embedding L2 when VPoser
    weights are unavailable. SMPLify-X uses `pose_embedding.pow(2).sum()` —
    same shape, applied in pose space rather than VPoser latent."""
    return (body_pose ** 2).sum()


def angle_prior_elbow_knee(body_pose: torch.Tensor) -> torch.Tensor:
    """Penalise elbow/knee hyperextension.

    SMPLify-X (`prior.py::SMPLifyAnglePrior`) penalises bending of these four
    joints around the *wrong* axis using a hardcoded sign per joint.
    Here we implement the same idea: the bend axis for these joints is the
    joint-local Z (twist around its rest direction); negative values bend the
    joint "backwards" (hyperextend). Penalise (negative)**2.

    body_pose: (B, 21, 3) or (B, 63)
    """
    if body_pose.dim() == 2:
        bp = body_pose.view(-1, 21, 3)
    else:
        bp = body_pose
    # SMPLify-X uses joints L_Elbow=18 R_Elbow=19 L_Knee=4 R_Knee=5 in the
    # 22-joint indexing including pelvis. body_pose excludes pelvis, so
    # subtract 1: L_Knee=3, R_Knee=4, L_Elbow=17, R_Elbow=18.
    # Bend component (per SMPLify-X) is axis-angle index 2 (z) for elbows
    # and axis-angle index 0 (x) for knees. Signs: elbow_l +, elbow_r -,
    # knee_l +, knee_r -. Penalise clamp(-x * sign, min=0)**2.
    le = bp[:, L_ELBOW_IDX, 2]
    re = bp[:, R_ELBOW_IDX, 2]
    lk = bp[:, L_KNEE_IDX, 0]
    rk = bp[:, R_KNEE_IDX, 0]
    bad = (
        torch.clamp(-le, min=0.0) ** 2
        + torch.clamp(re, min=0.0) ** 2
        + torch.clamp(-lk, min=0.0) ** 2
        + torch.clamp(rk, min=0.0) ** 2
    )
    return bad.sum()
