"""CLI: run extractor on a fit.npz, print measurements + skipped reasons.

Usage:
    python -m body_scanner.measure.cli data/results/yaiza_smplx_fit.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import smplx

from .extractor import extract


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract measurements from a fit.")
    p.add_argument("fit_npz", type=Path)
    p.add_argument(
        "--model-folder", default="data/body_models",
        help="Folder containing smplx/SMPLX_FEMALE.npz (for face indices)",
    )
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=100)
    p.add_argument("--show-skipped", action="store_true")
    args = p.parse_args(argv)

    fit = np.load(args.fit_npz)
    verts = fit["smplx_vertices"].astype(np.float32)
    bm = smplx.create(
        model_path=args.model_folder, model_type="smplx",
        gender=args.gender, num_betas=args.num_betas,
        use_pca=False, batch_size=1,
    )
    faces = np.asarray(bm.faces, dtype=np.int32)

    report = extract(verts, faces)

    # Print values, sorted by name for stable output.
    print(f"{'measurement':<40} {'value (cm)':>10}")
    print("-" * 52)
    for name in sorted(report.values):
        print(f"{name:<40} {report.values[name]:>10.2f}")
    print(f"\n{len(report.values)} extracted   {len(report.skipped)} skipped")
    if args.show_skipped:
        print("\nSkipped:")
        for name, reason in sorted(report.skipped.items()):
            print(f"  {name}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
