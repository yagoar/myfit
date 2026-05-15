"""SMPL-X mesh-to-mesh fitting.

Adapted from SMPLify-X (https://github.com/vchoutas/smplify-x) for the case
where the input is a target mesh (e.g. a LiDAR scan reconstruction) rather
than an image plus 2D keypoints. The 2D keypoint loss is replaced with
bidirectional chamfer; everything else follows SMPLify-X conventions:

  - LBFGS with strong-Wolfe line search
  - staged unfreezing (rigid -> +shape -> +pose-via-VPoser -> relaxed)
  - L2 shape prior, L2 on VPoser latent z (SMPLify-X: pose_embedding.pow(2).sum())
  - elbow/knee angle prior (SMPLify-X angle_prior)

See GUARDRAILS.md sections 1.2 and 4 for the rules governing this code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import smplx
import torch
from scipy.spatial import cKDTree

from . import align
from .losses import (
    angle_prior_elbow_knee,
    chamfer_bidirectional,
    crop_scan_for_chamfer,
    pose_prior_l2,
    pose_prior_z_l2,
    shape_prior,
)
from .vposer import VPoserWrapper


@dataclass
class FitConfig:
    model_folder: str = "data/body_models"
    gender: str = "female"
    num_betas: int = 200
    device: str = "cpu"
    vposer_ckpt: str | None = "data/vposer/vposer_v1_0/snapshots/TR00_E096.pt"
    # Crop hair/floor from the chamfer target — see losses.crop_scan_for_chamfer.
    crop_above_y_frac: float = 0.97
    crop_below_y_frac: float = 0.02
    # Stage weights. Chamfer always 1; priors scaled relative to it.
    stage_weights: list[dict] = field(default_factory=lambda: [
        # Stage 1 — rigid: global_orient + transl
        dict(chamfer=1.0, shape=0.0, pose=0.0, angle=0.0, iters=20,
             unfreeze=("global_orient", "transl"), use_vposer=False),
        # Stage 2 — +shape: pelvis-anchored shape adjustment
        dict(chamfer=1.0, shape=0.01, pose=0.0, angle=0.0, iters=30,
             unfreeze=("global_orient", "transl", "betas"), use_vposer=False),
        # Stage 3 — +pose via VPoser z (32D latent), strong z prior
        dict(chamfer=1.0, shape=0.005, pose=0.01, angle=10.0, iters=60,
             unfreeze=("global_orient", "transl", "betas", "z"), use_vposer=True),
        # Stage 4 — relax z prior
        dict(chamfer=1.0, shape=0.002, pose=0.001, angle=10.0, iters=60,
             unfreeze=("global_orient", "transl", "betas", "z"), use_vposer=True),
        # Stage 5 — release into raw body_pose with very loose prior
        dict(chamfer=1.0, shape=0.0001, pose=0.0002, angle=10.0, iters=80,
             unfreeze=("global_orient", "transl", "betas", "body_pose"),
             use_vposer=False),
        # Stage 6 — final tighten, almost free shape, mainly to chase
        # the last few mm on a naked scan
        dict(chamfer=1.0, shape=0.00002, pose=0.00005, angle=10.0, iters=120,
             unfreeze=("global_orient", "transl", "betas", "body_pose"),
             use_vposer=False),
    ])


@dataclass
class FitResult:
    betas: np.ndarray
    body_pose: np.ndarray  # axis-angle (21, 3)
    global_orient: np.ndarray  # axis-angle (3,)
    transl: np.ndarray
    z: np.ndarray | None  # VPoser latent if used in final stage
    smplx_vertices: np.ndarray
    smplx_joints: np.ndarray
    final_chamfer: float


def _set_requires_grad(body_model, transl, z, names: tuple[str, ...]):
    for p in body_model.parameters():
        p.requires_grad_(False)
    if z is not None:
        z.requires_grad_(False)
    for n in names:
        if n == "transl":
            transl.requires_grad_(True)
        elif n == "z":
            z.requires_grad_(True)
        else:
            getattr(body_model, n).requires_grad_(True)


def fit_scan(
    scan_verts: np.ndarray,
    cfg: FitConfig | None = None,
    verbose: bool = True,
) -> FitResult:
    cfg = cfg or FitConfig()
    device = torch.device(cfg.device)

    body_model = smplx.create(
        model_path=cfg.model_folder,
        model_type="smplx",
        gender=cfg.gender,
        num_betas=cfg.num_betas,
        use_pca=False,
        flat_hand_mean=True,
        batch_size=1,
    ).to(device)

    vposer = None
    if cfg.vposer_ckpt is not None and Path(cfg.vposer_ckpt).exists():
        vposer = VPoserWrapper(cfg.vposer_ckpt, device=cfg.device)
        if verbose:
            print(f"loaded VPoser from {cfg.vposer_ckpt}")
    elif verbose:
        print("VPoser checkpoint not found — falling back to L2 pose prior")

    z = (
        torch.zeros(1, vposer.latent_dim, device=device, requires_grad=False)
        if vposer is not None
        else None
    )
    if z is not None:
        z = torch.nn.Parameter(z)

    # Crop chamfer target: drop hair/floor.
    keep_mask = crop_scan_for_chamfer(
        scan_verts, cfg.crop_above_y_frac, cfg.crop_below_y_frac
    )
    scan_cropped = scan_verts[keep_mask].astype(np.float32)
    if verbose:
        print(
            f"scan crop: kept {keep_mask.sum()}/{len(scan_verts)} verts "
            f"(Y range {scan_cropped[:,1].min():.3f}..{scan_cropped[:,1].max():.3f})"
        )

    # Initial centroid alignment uses the cropped scan (avoids hair pulling
    # the initial transl upward).
    with torch.no_grad():
        canon = body_model().vertices[0].cpu().numpy()
    transl_init = align.initial_transl(scan_cropped, canon).astype(np.float32)
    transl = torch.nn.Parameter(
        torch.from_numpy(transl_init).unsqueeze(0).to(device)
    )
    body_model.transl = transl

    scan_t = torch.from_numpy(scan_cropped).to(device)
    scan_tree = cKDTree(scan_cropped)

    final_loss = float("inf")

    for stage_i, sw in enumerate(cfg.stage_weights):
        if sw.get("use_vposer", False) and vposer is None:
            # No VPoser available — fall back to optimizing body_pose with L2.
            sw = {**sw, "use_vposer": False,
                  "unfreeze": tuple(
                      "body_pose" if n == "z" else n for n in sw["unfreeze"])}

        _set_requires_grad(body_model, transl, z, sw["unfreeze"])

        params = [p for p in body_model.parameters() if p.requires_grad]
        if z is not None and z.requires_grad:
            params.append(z)

        optimizer = torch.optim.LBFGS(
            params,
            lr=1.0,
            max_iter=20,
            line_search_fn="strong_wolfe",
            tolerance_grad=1e-6,
            tolerance_change=1e-9,
        )

        use_vposer = sw.get("use_vposer", False) and vposer is not None

        def closure():
            optimizer.zero_grad()
            if use_vposer:
                body_pose_aa = vposer.decode(z).view(1, 63)
                out = body_model(body_pose=body_pose_aa, return_full_pose=False)
            else:
                out = body_model(return_full_pose=False)
            v = out.vertices[0]
            l_chamfer = chamfer_bidirectional(v, scan_t, scan_tree)
            l_shape = shape_prior(body_model.betas)
            if use_vposer:
                l_pose = pose_prior_z_l2(z)
            else:
                l_pose = pose_prior_l2(body_model.body_pose)
            l_angle = angle_prior_elbow_knee(
                vposer.decode(z).view(1, 63) if use_vposer
                else body_model.body_pose
            )
            loss = (
                sw["chamfer"] * l_chamfer
                + sw["shape"] * l_shape
                + sw["pose"] * l_pose
                + sw["angle"] * l_angle
            )
            loss.backward()
            closure.last = float(loss.item())
            closure.parts = (
                float(l_chamfer.item()),
                float(l_shape.item()),
                float(l_pose.item()),
                float(l_angle.item()),
            )
            return loss

        for it in range(sw["iters"]):
            optimizer.step(closure)
            if verbose and (it % 10 == 0 or it == sw["iters"] - 1):
                lc, ls, lp, la = closure.parts
                print(
                    f"  stage {stage_i+1} iter {it:3d}  "
                    f"loss={closure.last:.6f}  "
                    f"chamfer={lc:.6f}  shape={ls:.3f}  "
                    f"pose={lp:.3f}  angle={la:.4f}"
                )
        final_loss = closure.parts[0]
        if verbose:
            print(f"stage {stage_i+1} done — chamfer={final_loss:.6f}")

        # If we just left a VPoser stage and the next stage uses raw
        # body_pose, copy the decoded pose into body_model.body_pose so we
        # start from the converged latent rather than zero.
        next_uses_raw = (
            stage_i + 1 < len(cfg.stage_weights)
            and not cfg.stage_weights[stage_i + 1].get("use_vposer", False)
            and use_vposer
        )
        if next_uses_raw:
            with torch.no_grad():
                aa = vposer.decode(z).view(1, 63)
                body_model.body_pose[:] = aa

    with torch.no_grad():
        if vposer is not None and cfg.stage_weights[-1].get("use_vposer", False):
            body_pose_aa = vposer.decode(z).view(1, 63)
            out = body_model(body_pose=body_pose_aa, return_full_pose=False)
            bp_out = body_pose_aa.detach().cpu().numpy()[0].reshape(21, 3)
        else:
            out = body_model()
            bp_out = body_model.body_pose.detach().cpu().numpy()[0].reshape(21, 3)

    return FitResult(
        betas=body_model.betas.detach().cpu().numpy()[0],
        body_pose=bp_out,
        global_orient=body_model.global_orient.detach().cpu().numpy()[0],
        transl=transl.detach().cpu().numpy()[0],
        z=z.detach().cpu().numpy()[0] if z is not None else None,
        smplx_vertices=out.vertices[0].detach().cpu().numpy(),
        smplx_joints=out.joints[0].detach().cpu().numpy(),
        final_chamfer=final_loss,
    )


def save_fit(result: FitResult, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_path,
        betas=result.betas,
        body_pose=result.body_pose,
        global_orient=result.global_orient,
        transl=result.transl,
        z=result.z if result.z is not None else np.array([]),
        smplx_vertices=result.smplx_vertices,
        smplx_joints=result.smplx_joints,
        final_chamfer=np.array([result.final_chamfer]),
    )
