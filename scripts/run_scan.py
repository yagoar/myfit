"""End-to-end body-scanner pipeline: Stray capture → measurements.

Steps:
  1. Load Stray Scanner frames (rgb + depth + confidence + pose).
  2. Segment body per-frame (depth_threshold / rembg / rvm).
  3. Filter depth (confidence + range + bilateral).
  4. TSDF-fuse into a triangle mesh.
  5. Cleanup (largest component → hole fill → smooth → decimate).
  6. SMPL-X+D fit (parametric A-pose body).
  7. Extract Seamly catalog measurements (167+ codes).
  8. Re-pose for bent-arm L01/L02/L03/L04 and overwrite those codes.
  9. Write all artefacts: scan.obj, fit.npz, fit_body.obj, csv, smis,
     seamly_catalog.json, bent_arm.npz, bent_arm.json.

Usage:
    python scripts/run_scan.py data/captures/<name>/ \\
        --out-prefix data/results/<name> \\
        --seg-backend rembg \\
        --voxel 0.005

Pass ``--skip-fusion`` to reuse an existing ``<prefix>_scan.obj`` —
useful when only re-running the fit/measure stages.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator

import numpy as np

from body_scanner.io.stray_loader import load_capture
from body_scanner.preprocess.depth_filter import (
    DEFAULT_MAX_DEPTH_MM,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_DEPTH_MM,
    apply_alpha_mask,
    filter_depth,
)
from body_scanner.preprocess.segment import Segmenter, available_backends
from body_scanner.reconstruct.cleanup import cleanup_mesh
from body_scanner.reconstruct.tsdf import (
    DEFAULT_SDF_TRUNC_M,
    DEFAULT_VOXEL_M,
    FusionInput,
    fuse_frames,
    save_mesh_obj,
)


def _iter_fusion_inputs(
    capture: Path,
    *,
    seg_backend: str,
    frame_stride: int,
    min_conf: int,
    min_depth_mm: int,
    max_depth_mm: int,
    bilateral: bool,
    alpha_threshold: float,
) -> Iterator[FusionInput]:
    """Stream segmented + filtered frames as FusionInput records."""
    segmenter = Segmenter(backend=seg_backend)
    needs_rgb = seg_backend != "depth_threshold"

    for i, frame in enumerate(
            load_capture(capture, decode_rgb=needs_rgb)):
        if i % frame_stride != 0:
            continue
        if frame.depth_mm is None:
            continue
        filt = filter_depth(
            frame.depth_mm,
            confidence=frame.confidence,
            min_confidence=min_conf,
            min_depth_mm=min_depth_mm,
            max_depth_mm=max_depth_mm,
            bilateral=bilateral,
        )
        if (filt > 0).sum() < 200:
            continue  # frame mostly empty after filter — skip
        seg = segmenter.segment(frame.rgb, filt)
        masked = apply_alpha_mask(filt, seg.alpha_depth,
                                   threshold=alpha_threshold)
        if (masked > 0).sum() < 200:
            continue
        yield FusionInput(
            depth_mm=masked,
            intrinsics=frame.intrinsics,
            pose_c2w=frame.pose_cam_to_world,
        )


def run(
    capture: Path,
    out_prefix: Path,
    *,
    seg_backend: str,
    voxel_m: float,
    sdf_trunc_m: float,
    frame_stride: int,
    min_conf: int,
    min_depth_mm: int,
    max_depth_mm: int,
    bilateral: bool,
    alpha_threshold: float,
    intrinsics_native_size: tuple[int, int] | None,
    skip_fusion: bool,
    model_folder: str,
    gender: str,
    num_betas: int,
    use_displacement: bool,
    smooth_d: bool,
) -> int:
    """Run the full pipeline; return process exit code."""
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    scan_obj = out_prefix.with_name(out_prefix.name + "_scan.obj")
    fit_npz = out_prefix.with_name(out_prefix.name + "_smplx_fit.npz")
    fit_obj = out_prefix.with_name(out_prefix.name + "_fit_body.obj")
    csv_path = out_prefix.with_name(out_prefix.name + "_measurements.csv")
    json_path = out_prefix.with_name(out_prefix.name + "_seamly_catalog.json")
    smis_path = out_prefix.with_name(out_prefix.name + ".smis")

    # ---- 1. Stray → segmented/filtered frames → TSDF mesh.
    if not skip_fusion:
        print(f"[1/5] TSDF fusion (backend={seg_backend}, voxel={voxel_m*1000:.1f}mm)")
        inputs = _iter_fusion_inputs(
            capture,
            seg_backend=seg_backend,
            frame_stride=frame_stride,
            min_conf=min_conf,
            min_depth_mm=min_depth_mm,
            max_depth_mm=max_depth_mm,
            bilateral=bilateral,
            alpha_threshold=alpha_threshold,
        )
        mesh = fuse_frames(
            inputs,
            voxel_length=voxel_m,
            sdf_trunc=sdf_trunc_m,
            intrinsics_native_size=intrinsics_native_size,
        )
        print("[2/5] cleanup")
        mesh = cleanup_mesh(mesh)
        save_mesh_obj(mesh, scan_obj)
        print(f"  wrote {scan_obj}")
    else:
        if not scan_obj.is_file():
            print(f"ERROR: --skip-fusion but {scan_obj} not found")
            return 1
        print(f"[1-2/5] reuse {scan_obj}")

    # ---- 3. SMPL-X fit.
    print(f"[3/5] SMPL-X fit (num_betas={num_betas})")
    import trimesh
    from body_scanner.fit.fit import FitConfig, fit_scan, save_fit
    scan = trimesh.load(scan_obj, process=False)
    sv = np.asarray(scan.vertices, dtype=np.float32)
    sf = np.asarray(scan.faces, dtype=np.int32)
    cfg = FitConfig(
        model_folder=model_folder,
        gender=gender,
        num_betas=num_betas,
        device="cpu",
        use_displacement=use_displacement,
        use_smooth_displacement=smooth_d,
    )
    result = fit_scan(sv, cfg=cfg, verbose=True, scan_faces=sf)
    save_fit(result, fit_npz)
    print(f"  wrote {fit_npz}  (chamfer={result.final_chamfer:.6f})")

    # ---- 4. Measurement extraction (incl. bent-arm override).
    print("[4/5] measurement extraction")
    import subprocess
    cmd = [
        ".venv/bin/python", "-m", "body_scanner.measure.cli", str(fit_npz),
        "--both", "--num-betas", str(num_betas),
        "--save-csv", str(csv_path),
        "--save-seamly-json", str(json_path),
        "--save-smis", str(smis_path),
        "--save-obj", str(fit_obj),
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  measure.cli failed (exit {r.returncode})")
        return r.returncode

    # ---- 5. Bent-arm npz + json (for review viewer + audit).
    print("[5/5] bent-arm re-pose for L01/L02/L03/L04")
    cmd = [
        ".venv/bin/python", "scripts/extract_bent_arm.py", str(fit_npz),
        "--num-betas", str(num_betas), "--gender", gender,
        "--model-folder", model_folder,
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  extract_bent_arm.py failed (exit {r.returncode})")
        return r.returncode

    print("\nDONE.")
    print(f"  scan mesh:     {scan_obj}")
    print(f"  fit npz:       {fit_npz}")
    print(f"  fit body obj:  {fit_obj}")
    print(f"  csv:           {csv_path}")
    print(f"  smis:          {smis_path}")
    print(f"  catalog json:  {json_path}")
    print("\nReview viewer:")
    print(f"  python -m body_scanner.measure.review_viewer {fit_npz} "
          f"--num-betas {num_betas} --port 8051")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("capture", type=Path,
                   help="Stray Scanner capture folder")
    p.add_argument("--out-prefix", type=Path, required=True,
                   help="e.g. data/results/<name>")
    p.add_argument(
        "--seg-backend", default="depth_threshold",
        choices=sorted({"rembg", "rvm", "depth_threshold"}),
        help=("body-segmentation backend. "
              f"available now: {available_backends()}. "
              "depth_threshold = depth-only, no extra deps. "
              "rembg = `pip install rembg` (~180 MB, U2Net body matting). "
              "rvm = torch.hub RVM mobilenetv3 (best edges)."))
    p.add_argument("--voxel", type=float, default=DEFAULT_VOXEL_M)
    p.add_argument("--sdf-trunc", type=float, default=DEFAULT_SDF_TRUNC_M)
    p.add_argument("--frame-stride", type=int, default=1,
                   help="Integrate every Nth frame (1 = all).")
    p.add_argument("--min-confidence", type=int,
                   default=DEFAULT_MIN_CONFIDENCE,
                   help="Drop depth pixels below this Stray confidence tier.")
    p.add_argument("--min-depth-mm", type=int,
                   default=DEFAULT_MIN_DEPTH_MM)
    p.add_argument("--max-depth-mm", type=int,
                   default=DEFAULT_MAX_DEPTH_MM)
    p.add_argument("--no-bilateral", action="store_true",
                   help="Disable per-frame depth bilateral smooth.")
    p.add_argument("--alpha-threshold", type=float, default=0.5,
                   help="Min seg alpha to keep depth pixel.")
    p.add_argument("--intrinsics-native-w", type=int, default=None,
                   help="Width of the pixel grid in which Stray reports "
                        "fx/fy/cx/cy. Omit if intrinsics already match "
                        "the depth resolution.")
    p.add_argument("--intrinsics-native-h", type=int, default=None)
    p.add_argument("--skip-fusion", action="store_true",
                   help="Reuse an existing <prefix>_scan.obj.")
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=300)
    p.add_argument("--use-displacement", action="store_true")
    p.add_argument("--smooth-d", action="store_true")
    args = p.parse_args()

    native_size = None
    if args.intrinsics_native_w and args.intrinsics_native_h:
        native_size = (args.intrinsics_native_w, args.intrinsics_native_h)

    return run(
        capture=args.capture,
        out_prefix=args.out_prefix,
        seg_backend=args.seg_backend,
        voxel_m=args.voxel,
        sdf_trunc_m=args.sdf_trunc,
        frame_stride=args.frame_stride,
        min_conf=args.min_confidence,
        min_depth_mm=args.min_depth_mm,
        max_depth_mm=args.max_depth_mm,
        bilateral=not args.no_bilateral,
        alpha_threshold=args.alpha_threshold,
        intrinsics_native_size=native_size,
        skip_fusion=args.skip_fusion,
        model_folder=args.model_folder,
        gender=args.gender,
        num_betas=args.num_betas,
        use_displacement=args.use_displacement,
        smooth_d=args.smooth_d,
    )


if __name__ == "__main__":
    raise SystemExit(main())
