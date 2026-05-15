#!/usr/bin/env python3
"""Phase 0 verification — load SMPL-X, run a forward pass, render the T-pose.

Run after dropping the SMPL-X model files into data/body_models/smplx/.

Required file (minimum): data/body_models/smplx/SMPLX_FEMALE.npz
   from https://smpl-x.is.tue.mpg.de/  (zip: models_smplx_v1_1.zip)

Gender: female. The project is single-user and female-target end-to-end,
so the gendered model is used here as well — its shape space fits a
female body better than NEUTRAL. See SPEC.md section 13.

Pass criteria (SPEC.md section 14):
   - smplx loads without error
   - model.faces.shape == (20908, 3)
   - forward-pass vertices.shape == (1, 10475, 3)
   - an Open3D window shows the T-posed female mesh

Usage:
   python scripts/verify_phase0.py            # open viewer
   python scripts/verify_phase0.py --no-viz   # asserts only (for CI / SSH)

API note (verified against smplx source, vchoutas/smplx body_models.py):
   smplx.create() joins model_path with model_type when model_path is a
   directory, so model_path must be the PARENT of the smplx/ subfolder.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Path to the parent of the model-type subfolder. The smplx loader appends
# model_type to this path, so this must be data/body_models, not
# data/body_models/smplx/. See SPEC.md section 14.
MODEL_PARENT = Path(__file__).resolve().parent.parent / "data" / "body_models"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="skip the Open3D viewer (useful headless or in CI)",
    )
    args = parser.parse_args()

    print(f"[1/4] loading smplx from: {MODEL_PARENT}/smplx/")
    model_file = MODEL_PARENT / "smplx" / "SMPLX_FEMALE.npz"
    if not model_file.exists():
        print(
            f"FAIL: {model_file} does not exist.\n"
            "      download models_smplx_v1_1.zip from https://smpl-x.is.tue.mpg.de/\n"
            "      and extract SMPLX_FEMALE.npz into data/body_models/smplx/",
            file=sys.stderr,
        )
        return 2

    import smplx  # noqa: PLC0415  imported here so missing-deps message is clearer
    import torch  # noqa: PLC0415

    model = smplx.create(
        str(MODEL_PARENT),
        model_type="smplx",
        gender="female",
        use_pca=False,
    )

    print(f"[2/4] asserting faces.shape == (20908, 3)")
    faces = model.faces  # numpy.ndarray
    assert faces.shape == (20908, 3), f"unexpected faces shape: {faces.shape}"

    print(f"[3/4] forward pass with zero betas/pose")
    with torch.no_grad():
        output = model()
    vertices = output.vertices
    assert tuple(vertices.shape) == (1, 10475, 3), (
        f"unexpected vertices shape: {tuple(vertices.shape)}"
    )

    print(f"      faces:    {faces.shape}  dtype={faces.dtype}")
    print(f"      vertices: {tuple(vertices.shape)}  dtype={vertices.dtype}")
    print(f"      joints:   {tuple(output.joints.shape)}")

    if args.no_viz:
        print("[4/4] viewer skipped (--no-viz). all asserts passed.")
        return 0

    print(f"[4/4] opening Open3D viewer — close the window to exit")
    import numpy as np  # noqa: PLC0415
    import open3d as o3d  # noqa: PLC0415

    verts_np = vertices[0].detach().cpu().numpy().astype(np.float64)
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(verts_np)
    mesh.triangles = o3d.utility.Vector3iVector(faces.astype(np.int32))
    mesh.compute_vertex_normals()
    mesh.paint_uniform_color([0.85, 0.78, 0.72])

    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3)
    o3d.visualization.draw_geometries(
        [mesh, axes],
        window_name="Phase 0 — SMPL-X female T-pose",
        mesh_show_back_face=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
