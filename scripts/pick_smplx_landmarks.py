#!/usr/bin/env python3
"""Open3D-based interactive picker for SMPL-X body-measurement landmarks.

Phase 5 helper. Loads the SMPL-X female T-pose mesh, renders it together
with the model's skeleton joints as colored spheres for anatomical
orientation, and opens an interactive Open3D `VisualizerWithEditing`
window so the user can pick vertices.

Per GUARDRAILS section 3, picks produced here are PROPOSED only. Every
vertex ID must still be verified in Blender (with the SMPL-X addon) and
committed to `references/smplx_vertex_landmarks.md` with a screenshot.

Controls (Open3D editing visualizer):
   Shift + left click     pick a vertex (red sphere marker drawn)
   Shift + right click    undo the last pick
   Q (or close window)    finish — picks are printed to stdout

Usage:
   python scripts/pick_smplx_landmarks.py
   python scripts/pick_smplx_landmarks.py --no-joints   # hide joint spheres
   python scripts/pick_smplx_landmarks.py --output picks.json   # also save JSON

After closing the window the script prints one line per pick in the
order they were made:
   [N] vertex_id=NNNN coord=(x, y, z)
Paste the IDs into the matching `proposed_vertex_id` rows in
`references/smplx_vertex_landmarks.md`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODEL_PARENT = Path(__file__).resolve().parent.parent / "data" / "body_models"

# Joint indices in the SMPL-X joint output that are most useful for body-
# measurement orientation. Skeleton joints are NOT mesh vertices, but
# their 3D positions help the user navigate the mesh in Open3D. Indices
# follow smplx.joint_names.JOINT_NAMES.
ORIENTATION_JOINTS = {
    "pelvis": 0,
    "left_hip": 1,
    "right_hip": 2,
    "spine1": 3,
    "left_knee": 4,
    "right_knee": 5,
    "spine2": 6,
    "left_ankle": 7,
    "right_ankle": 8,
    "spine3": 9,
    "neck": 12,
    "left_collar": 13,
    "right_collar": 14,
    "head": 15,
    "left_shoulder": 16,
    "right_shoulder": 17,
    "left_elbow": 18,
    "right_elbow": 19,
    "left_wrist": 20,
    "right_wrist": 21,
}


def load_smplx_tpose() -> tuple["np.ndarray", "np.ndarray", "np.ndarray"]:
    """Return (vertices Nx3, faces Mx3, joints Kx3) for the female T-pose."""
    model_file = MODEL_PARENT / "smplx" / "SMPLX_FEMALE.npz"
    if not model_file.exists():
        raise SystemExit(
            f"FAIL: {model_file} does not exist.\n"
            "      Run scripts/verify_phase0.py first to confirm the model is in place."
        )

    import numpy as np
    import smplx
    import torch

    model = smplx.create(
        str(MODEL_PARENT),
        model_type="smplx",
        gender="female",
        use_pca=False,
    )
    with torch.no_grad():
        output = model()
    verts = output.vertices[0].detach().cpu().numpy().astype(np.float64)
    joints = output.joints[0].detach().cpu().numpy().astype(np.float64)
    faces = model.faces.astype(np.int32)
    return verts, faces, joints


def build_mesh(verts, faces):
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(verts)
    mesh.triangles = o3d.utility.Vector3iVector(faces)
    mesh.compute_vertex_normals()
    mesh.paint_uniform_color([0.85, 0.78, 0.72])
    return mesh


def build_joint_markers(joints):
    """One small sphere per orientation joint, colored by region."""
    import open3d as o3d

    # Region colors so the user can visually distinguish torso vs limbs.
    colors = {
        "torso": [0.10, 0.45, 0.85],   # blue: pelvis, spine, neck, head
        "left":  [0.85, 0.30, 0.30],   # red: left arm + leg joints
        "right": [0.30, 0.70, 0.30],   # green: right arm + leg joints
    }
    region = {
        "pelvis": "torso", "spine1": "torso", "spine2": "torso",
        "spine3": "torso", "neck": "torso", "head": "torso",
        "left_hip": "left", "left_knee": "left", "left_ankle": "left",
        "left_collar": "left", "left_shoulder": "left",
        "left_elbow": "left", "left_wrist": "left",
        "right_hip": "right", "right_knee": "right", "right_ankle": "right",
        "right_collar": "right", "right_shoulder": "right",
        "right_elbow": "right", "right_wrist": "right",
    }

    markers = []
    for name, idx in ORIENTATION_JOINTS.items():
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.012)
        sphere.translate(joints[idx])
        sphere.paint_uniform_color(colors[region[name]])
        sphere.compute_vertex_normals()
        markers.append(sphere)
    return markers


def print_landmark_checklist():
    """Print the full landmark inventory to stdout before opening the picker.

    Mirrors `references/smplx_vertex_landmarks.md`. Pick in the order
    that makes sense visually (e.g. top-to-bottom, midline first); the
    mapping to landmark names happens after picking.
    """
    sections = [
        ("Midline torso (6)", [
            "top_of_head",
            "front_neck_point",
            "front_collar_bone (suprasternal notch)",
            "c7 (center back neck)",
            "waist_cf",
            "waist_cb",
        ]),
        ("Crotch + midline lower (1)", [
            "crotch_midpoint",
        ]),
        ("Shoulders + neck-shoulder corners (4)", [
            "shoulder_neck_left", "shoulder_neck_right",
            "acromion_left", "acromion_right",
        ]),
        ("Front shoulder midpoints (2)", [
            "front_shoulder_centre_left", "front_shoulder_centre_right",
        ]),
        ("Underarm + armhole anatomy (10)", [
            "underarm_left", "underarm_right",
            "armscye_front_left", "armscye_front_right",
            "armscye_back_left", "armscye_back_right",
            "armfold_front_left", "armfold_front_right",
            "armfold_back_left", "armfold_back_right",
        ]),
        ("Bust (3)", [
            "bust_apex_left", "bust_apex_right",
            "lowbust_apex",
        ]),
        ("Bra side seam (2)", [
            "bra_side_seam_left", "bra_side_seam_right",
        ]),
        ("Waist sides (2)", [
            "waist_side_left", "waist_side_right",
        ]),
        ("Arm (5)", [
            "elbow_back_left", "elbow_back_right",
            "wrist_ulnar_left", "wrist_ulnar_right",
            "bicep_max_right",
        ]),
        ("Leg (8)", [
            "thigh_at_crotch_left", "thigh_at_crotch_right",
            "crotch_lateral_left", "crotch_lateral_right",
            "knee_back_left", "knee_back_right",
            "ankle_bone_lateral_left", "ankle_bone_lateral_right",
        ]),
        ("Plane anchors (additional, 2)", [
            "rib_front", "mid_neck_front",
        ]),
        ("Audit judgment landmarks (optional, 3)", [
            "scapula_prominence_left", "scapula_prominence_right",
            "gluteal_fold_midpoint",
        ]),
    ]

    total = sum(len(items) for _, items in sections)
    print(f"\n=== Landmark inventory ({total} points) ===")
    for title, items in sections:
        print(f"\n{title}")
        for i, name in enumerate(items, 1):
            print(f"  - {name}")
    print(
        "\nPick the vertices in any order. After closing the window, the script"
        "\nprints the picks in click order. Map them back to landmark names by"
        "\nhand and paste vertex IDs into references/smplx_vertex_landmarks.md."
    )
    print("=" * 50, "\n")


def run_picker(verts: "np.ndarray", geometries) -> list[int]:
    """Hover-based picker: red sphere tracks nearest vertex to viewport centre.

    Controls:
      Left-click drag   rotate
      Right-click drag  pan
      Scroll            zoom
      P                 record current vertex
      U                 undo last pick
      Q / close         finish
    """
    import sys
    import open3d as o3d

    picked: list[int] = []
    current: dict = {"vid": -1}

    # Red indicator sphere that follows the nearest vertex to the aim ray.
    indicator = o3d.geometry.TriangleMesh.create_sphere(radius=0.010)
    indicator.paint_uniform_color([1.0, 0.15, 0.15])
    indicator.compute_vertex_normals()
    indicator.translate(verts[0])
    last_ind_pos = verts[0].copy()

    def _nearest_to_center_ray(vis):
        """Find vertex nearest to the ray through the viewport centre."""
        import numpy as np
        ctr = vis.get_view_control()
        cam = ctr.convert_to_pinhole_camera_parameters()
        ext = np.array(cam.extrinsic)          # 4x4 world-to-camera
        intr = cam.intrinsic
        R = ext[:3, :3]
        t = ext[:3, 3]
        cam_pos = -R.T @ t                     # camera centre in world space

        fx = intr.intrinsic_matrix[0, 0]
        fy = intr.intrinsic_matrix[1, 1]
        cx_px = intr.intrinsic_matrix[0, 2]
        cy_px = intr.intrinsic_matrix[1, 2]
        ray_cam = np.array(
            [(intr.width / 2 - cx_px) / fx,
             (intr.height / 2 - cy_px) / fy,
             1.0]
        )
        ray_world = R.T @ (ray_cam / np.linalg.norm(ray_cam))
        ray_world /= np.linalg.norm(ray_world)

        d = verts - cam_pos
        dists = np.linalg.norm(np.cross(d, ray_world), axis=1)
        dists[d @ ray_world < 0] = np.inf      # cull vertices behind camera
        return int(np.argmin(dists))

    def animation_callback(vis):
        nonlocal last_ind_pos
        vid = _nearest_to_center_ray(vis)
        current["vid"] = vid
        new_pos = verts[vid]
        indicator.translate(new_pos - last_ind_pos)
        last_ind_pos = new_pos.copy()
        vis.update_geometry(indicator)
        x, y, z = new_pos
        n = len(picked)
        sys.stdout.write(
            f"\r  aim → v{vid:5d} ({x:+.4f},{y:+.4f},{z:+.4f})  picks={n}  [P=pick U=undo Q=quit]   "
        )
        sys.stdout.flush()
        return False

    def on_pick(vis):
        vid = current["vid"]
        if vid >= 0:
            picked.append(vid)
            x, y, z = verts[vid]
            sys.stdout.write(
                f"\n[{len(picked):2d}] PICKED v{vid:5d} ({x:+.4f},{y:+.4f},{z:+.4f})\n"
            )
            sys.stdout.flush()
        return False

    def on_undo(vis):
        if picked:
            vid = picked.pop()
            sys.stdout.write(f"\n    UNDO  v{vid:5d}\n")
            sys.stdout.flush()
        return False

    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(
        window_name="SMPL-X picker — aim centre at landmark, P=pick, U=undo, Q=quit",
        width=1200,
        height=900,
    )
    for g in geometries:
        vis.add_geometry(g)
    vis.add_geometry(indicator)

    vis.register_animation_callback(animation_callback)
    vis.register_key_callback(ord("P"), on_pick)
    vis.register_key_callback(ord("U"), on_undo)

    vis.run()
    vis.destroy_window()
    print()
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-joints",
        action="store_true",
        help="hide the orientation joint spheres",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional path to save picks as JSON",
    )
    args = parser.parse_args()

    print("[1/3] loading SMPL-X female T-pose")
    verts, faces, joints = load_smplx_tpose()
    print(f"      vertices: {verts.shape}, faces: {faces.shape}, joints: {joints.shape}")

    print_landmark_checklist()

    print("[2/3] building geometries")
    mesh = build_mesh(verts, faces)
    geometries = [mesh]
    if not args.no_joints:
        geometries.extend(build_joint_markers(joints))

    import open3d as o3d
    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3)
    geometries.append(axes)

    print("[3/3] opening picker — aim viewport centre at landmark, P=pick, Q=quit")
    picked = run_picker(verts, geometries)

    if not picked:
        print("\nno picks recorded.")
        return 0

    print(f"\n=== picks ({len(picked)}) ===")
    records = []
    for i, vid in enumerate(picked, 1):
        x, y, z = verts[vid]
        print(f"[{i:2d}] vertex_id={vid:5d} coord=({x:+.4f}, {y:+.4f}, {z:+.4f})")
        records.append({
            "order": i,
            "vertex_id": int(vid),
            "coord": [float(x), float(y), float(z)],
        })

    if args.output:
        args.output.write_text(json.dumps(records, indent=2))
        print(f"\nwrote {len(records)} records to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
