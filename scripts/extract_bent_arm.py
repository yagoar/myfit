"""Compute bent-arm measurements (L01, L02, L04) by re-posing the fitted
SMPL-X body with the left elbow flexed.

A-pose scans don't capture bent-elbow geometry. Rather than require a
second scan, we re-evaluate the SMPL-X body model with the L_Elbow
joint rotated ~90° from its T-pose / fit-pose orientation, then compute
the measurements on the bent mesh.

Outputs (per fit):
  data/results/<basename>_bent_arm.json
    L01 cm  (acromion → wrist, bent)
    L02 cm  (acromion → elbow, bent)
    L03 cm  (= L01 - L02)
    L04 cm  (elbow girth, bent)

Caveats:
  * SMPL-X pose blend shapes handle skin deformation at the elbow but
    do NOT simulate flexed-muscle bulge — elbow girth may be off by
    ~1-2 cm vs a real bent-arm scan.
  * Per-vertex displacement (SMPL-X+D) is reused unchanged. It was fit
    in A-pose, so artefacts on the arm are possible but small.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import smplx
import torch

from body_scanner.measure.landmarks import build_landmark_set
from body_scanner.measure.primitives import Geodesic, LimbGirth


L_ELBOW_BODY_POSE_INDEX = 17  # SMPL-X joint 18 (L_Elbow) → body_pose row 17
L_SHOULDER_BODY_POSE_INDEX = 15  # SMPL-X joint 16 (L_Shoulder) → body_pose row 15


def _rebuild_mesh(
    fit_npz: Path,
    model_folder: str,
    gender: str,
    num_betas: int,
    elbow_axis_angle: np.ndarray,
    shoulder_axis_angle: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fit = np.load(fit_npz, allow_pickle=True)
    betas = torch.tensor(fit["betas"][None], dtype=torch.float32)
    body_pose = torch.tensor(fit["body_pose"][None], dtype=torch.float32)
    global_orient = torch.tensor(fit["global_orient"][None], dtype=torch.float32)
    transl = torch.tensor(fit["transl"][None], dtype=torch.float32)

    # Override L_Elbow axis-angle with the bent-arm rotation.
    body_pose[0, L_ELBOW_BODY_POSE_INDEX] = torch.tensor(
        elbow_axis_angle, dtype=torch.float32)
    if shoulder_axis_angle is not None:
        # Replace shoulder axis-angle outright so the bent pose lifts
        # the upper arm away from the torso (so the forearm doesn't
        # collide with the body when flexed).
        body_pose[0, L_SHOULDER_BODY_POSE_INDEX] = torch.tensor(
            shoulder_axis_angle, dtype=torch.float32)

    bm = smplx.create(
        model_path=model_folder,
        model_type="smplx",
        gender=gender,
        num_betas=num_betas,
        use_pca=False,
        batch_size=1,
    )
    out = bm(
        betas=betas,
        body_pose=body_pose.reshape(1, -1),
        global_orient=global_orient,
        transl=transl,
        return_verts=True,
    )
    verts = out.vertices.detach().numpy()[0]
    joints = out.joints.detach().numpy()[0]
    faces = np.asarray(bm.faces, dtype=np.int32)

    disp = fit.get("displacement")
    if disp is not None and disp.shape == verts.shape:
        verts = verts + disp

    return verts, joints, faces


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=300)
    p.add_argument(
        "--elbow-flex-deg", type=float, default=80.0,
        help="Elbow flex angle in degrees (rotation magnitude).",
    )
    p.add_argument(
        "--elbow-axis", type=str, default="0,-1,0",
        help="Comma-separated 3D axis-angle direction for the elbow "
             "rotation, in the L_Elbow local frame. Default '0,-1,0' "
             "bends the forearm forward in front of the body (Seamly "
             "tailoring pose).",
    )
    p.add_argument(
        "--shoulder-forward-deg", type=float, default=30.0,
        help="Rotate the shoulder forward by this many degrees (around "
             "world X). 0 keeps the fitted A-pose shoulder.",
    )
    p.add_argument(
        "--out-json", type=Path, default=None,
        help="Default: <fit_npz>_bent_arm.json next to the input.",
    )
    args = p.parse_args()

    # Elbow flex along the user-supplied axis (default = local X for
    # the Seamly tailoring pose: forearm raised vertical, biceps still
    # at the side, elbow pointing back).
    theta = np.deg2rad(args.elbow_flex_deg)
    axis = np.array([float(c) for c in args.elbow_axis.split(",")],
                     dtype=np.float32)
    axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
    elbow_aa = (axis * theta).astype(np.float32)

    # Shoulder forward (around world X). 0 keeps the fitted A-pose
    # shoulder unchanged.
    fit_in_for_pose = np.load(args.fit_npz, allow_pickle=True)
    shoulder_aa = fit_in_for_pose["body_pose"][L_SHOULDER_BODY_POSE_INDEX].copy()
    shoulder_aa[0] += np.deg2rad(args.shoulder_forward_deg)

    verts, joints, faces = _rebuild_mesh(
        args.fit_npz, args.model_folder, args.gender, args.num_betas,
        elbow_aa,
        shoulder_axis_angle=shoulder_aa.astype(np.float32),
    )
    landmarks = build_landmark_set(verts, joints=joints, faces=faces)

    # Use the catalog's bent-arm recipes directly so the script's
    # output matches the viewer / render. Catalog L01/L02 route via
    # bicep_max_left so the path stays on the OUTSIDE of the arm.
    from body_scanner.measure.seamly_catalog import RECIPES as _CAT
    bent_recipes = {c: _CAT[c] for c in ("L01", "L02", "L04")}
    values: dict[str, float] = {}
    for code, recipe in bent_recipes.items():
        try:
            values[code] = float(recipe.compute(verts, faces, landmarks))
        except Exception as e:  # noqa: BLE001
            values[code] = float("nan")
            print(f"  {code}: ERROR {e}")
    values["L03"] = values["L01"] - values["L02"]

    out_path = (
        args.out_json
        if args.out_json is not None
        else args.fit_npz.with_name(args.fit_npz.stem + "_bent_arm.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fit": str(args.fit_npz),
        "elbow_flex_deg": args.elbow_flex_deg,
        "elbow_axis_angle": elbow_aa.tolist(),
        "values_cm": {k: round(v, 2) for k, v in values.items()},
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out_path}")
    for code, val in sorted(values.items()):
        print(f"  {code}: {val:.2f} cm")

    # Save bent mesh as an npz with the same key layout as the input
    # fit so render_measurement_review.py / review_viewer.py can load
    # it directly. `displacement` is zeroed because it has already been
    # baked into `verts` here.
    npz_path = args.fit_npz.with_name(args.fit_npz.stem + "_bent_arm.npz")
    fit_in = np.load(args.fit_npz, allow_pickle=True)
    bent_npz = {
        "betas": fit_in["betas"],
        "body_pose": fit_in["body_pose"].copy(),
        "global_orient": fit_in["global_orient"],
        "transl": fit_in["transl"],
        "smplx_vertices": verts.astype(np.float32),
        "smplx_joints": joints.astype(np.float32),
        "displacement": np.zeros_like(verts, dtype=np.float32),
    }
    bent_npz["body_pose"][L_ELBOW_BODY_POSE_INDEX] = elbow_aa
    bent_npz["body_pose"][L_SHOULDER_BODY_POSE_INDEX] = shoulder_aa
    if "z" in fit_in.files:
        bent_npz["z"] = fit_in["z"]
    if "final_chamfer" in fit_in.files:
        bent_npz["final_chamfer"] = fit_in["final_chamfer"]
    np.savez(npz_path, **bent_npz)
    print(f"wrote {npz_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
