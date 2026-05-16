"""CLI entry for SMPL-X mesh-to-mesh fitting.

Usage:
    python -m body_scanner.fit.cli data/body_models/yaiza_model.obj \\
        --out data/results/yaiza_smplx_fit.npz \\
        --viz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from .fit import FitConfig, fit_scan, save_fit


def _load_scan(path: Path):
    m = trimesh.load(path, process=False)
    V = np.asarray(m.vertices, dtype=np.float32)
    F = np.asarray(m.faces, dtype=np.int32)
    return V, F


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fit SMPL-X to a scan mesh.")
    p.add_argument("scan", type=Path, help="Path to scan OBJ/PLY")
    p.add_argument(
        "--model-folder",
        type=str,
        default="data/body_models",
        help="Folder containing smplx/SMPLX_FEMALE.npz",
    )
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=300)
    p.add_argument(
        "--use-displacement",
        action="store_true",
        help="Enable SMPL-X+D stages (per-vertex displacement). Default off — "
             "parametric-only fit is smoother and matches addon mesh fidelity.",
    )
    p.add_argument(
        "--smooth-d",
        action="store_true",
        help="Run only the heavy-smooth D stage after parametric fit. "
             "Improves fit residual (~3mm) without baking scan noise.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data/results/scan_fit.npz"),
        help="Where to save the .npz fit result",
    )
    p.add_argument(
        "--viz",
        action="store_true",
        help="Open an interactive heatmap viewer after fitting",
    )
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    scan_v, scan_f = _load_scan(args.scan)
    print(f"loaded scan {args.scan}: {len(scan_v)} verts, {len(scan_f)} faces")

    cfg = FitConfig(
        model_folder=args.model_folder,
        gender=args.gender,
        num_betas=args.num_betas,
        device="cpu",
        use_displacement=args.use_displacement,
        use_smooth_displacement=args.smooth_d,
    )
    result = fit_scan(scan_v, cfg=cfg, verbose=not args.quiet,
                      scan_faces=scan_f)
    save_fit(result, args.out)
    print(f"saved {args.out}")
    print(f"final chamfer (sum of bidirectional means) = {result.final_chamfer:.6f}")

    if args.viz:
        # Lazy import — Open3D adds a few seconds to startup.
        from .viz import visualize_fit
        import smplx

        bm = smplx.create(
            model_path=args.model_folder,
            model_type="smplx",
            gender=args.gender,
            use_pca=False,
            batch_size=1,
        )
        smplx_faces = np.asarray(bm.faces, dtype=np.int32)
        visualize_fit(scan_v, scan_f, result.smplx_vertices, smplx_faces)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
