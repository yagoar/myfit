"""CLI: run extractor on a fit.npz, print measurements + skipped reasons.

Two modes:
  default        — run the merged.yaml extractor (Aldrich + dpm subset)
  --seamly       — run the Seamly catalog extractor (all 245 codes,
                   per references/seamly/extraction_audit.md)
  --both         — run both and label output
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import smplx

from .exports import write_csv, write_obj, write_smis_from_catalog
from .extractor import extract
from .seamly_extractor import extract_catalog


def _print_table(values: dict, label: str = "measurement", unit: str = "cm") -> None:
    print(f"{label:<40} {'value (' + unit + ')':>10}")
    print("-" * 52)
    for k in sorted(values):
        print(f"{k:<40} {values[k]:>10.2f}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract measurements from a fit.")
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=100)
    p.add_argument("--seamly", action="store_true",
                   help="Run the Seamly catalog extractor (all codes).")
    p.add_argument("--both", action="store_true",
                   help="Run both extractors.")
    p.add_argument("--show-skipped", action="store_true")
    p.add_argument(
        "--save-seamly-json",
        type=Path,
        help="Write {seamly_code: value_cm} JSON",
    )
    p.add_argument(
        "--save-csv",
        type=Path,
        help="Write CSV: code, seamly_name, value_cm",
    )
    p.add_argument(
        "--save-obj",
        type=Path,
        help="Write fitted SMPL-X body mesh as Wavefront OBJ (for CLO3D)",
    )
    p.add_argument(
        "--save-smis",
        type=Path,
        help="Write SeamlyMe .smis directly (no intermediate JSON)",
    )
    p.add_argument(
        "--smis-template",
        type=Path,
        default=Path.home() / "seamly2d" / "templates" /
                "all_measurements_template.smis",
        help="Reference .smis whose measurement order is preserved",
    )
    p.add_argument(
        "--no-bent-arm",
        action="store_true",
        help="Skip the bent-arm re-pose pass (L01/L02/L03/L04 then "
             "fall through as A-pose values, which are incorrect).",
    )
    p.add_argument(
        "--bent-elbow-flex-deg", type=float, default=80.0,
        help="Elbow flex angle for the bent-arm override (default 80°).",
    )
    p.add_argument(
        "--bent-elbow-axis", type=str, default="0,-1,0",
        help="Elbow rotation axis in the L_Elbow local frame "
             "(default '0,-1,0' = forearm forward in the Seamly pose).",
    )
    p.add_argument(
        "--bent-shoulder-forward-deg", type=float, default=30.0,
        help="Extra L_Shoulder forward rotation (around world X) so the "
             "forearm doesn't collide with the torso when bent.",
    )
    args = p.parse_args(argv)

    fit = np.load(args.fit_npz)
    verts = fit["smplx_vertices"].astype(np.float32)
    joints = (fit["smplx_joints"].astype(np.float32)
              if "smplx_joints" in fit.files else None)
    bm = smplx.create(
        model_path=args.model_folder, model_type="smplx",
        gender=args.gender, num_betas=args.num_betas,
        use_pca=False, batch_size=1,
    )
    faces = np.asarray(bm.faces, dtype=np.int32)

    run_named = not args.seamly or args.both
    run_seamly = args.seamly or args.both

    if run_named:
        rep = extract(verts, faces, joints=joints)
        print("=" * 52)
        print("merged.yaml (Aldrich + dpm) extractor")
        print("=" * 52)
        _print_table(rep.values)
        print(f"\n{len(rep.values)} extracted   {len(rep.skipped)} skipped")
        if args.show_skipped:
            print("\nSkipped:")
            for k, reason in sorted(rep.skipped.items()):
                print(f"  {k}: {reason}")

    if run_seamly:
        cat = extract_catalog(verts, faces, joints=joints)
        # Bent-arm override: L01/L02/L04 (and the L03 formula) need an
        # elbow-flexed mesh. Re-pose the SMPL-X body, recompute those
        # codes on the bent verts, then overwrite the A-pose values.
        if not args.no_bent_arm and "body_pose" in fit.files:
            try:
                import torch
                from .seamly_catalog import RECIPES as _CAT
                from .landmarks import build_landmark_set
                betas_t = torch.tensor(fit["betas"][None], dtype=torch.float32)
                body_pose_t = torch.tensor(fit["body_pose"][None],
                                            dtype=torch.float32)
                global_orient_t = torch.tensor(fit["global_orient"][None],
                                                dtype=torch.float32)
                transl_t = torch.tensor(fit["transl"][None],
                                         dtype=torch.float32)
                theta = np.deg2rad(args.bent_elbow_flex_deg)
                axis = np.array([float(c) for c in
                                  args.bent_elbow_axis.split(",")],
                                  dtype=np.float32)
                axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
                elbow_aa = (axis * theta).astype(np.float32)
                body_pose_t[0, 17] = torch.tensor(elbow_aa)  # L_Elbow
                shoulder_aa = fit["body_pose"][15].copy()
                shoulder_aa[0] += np.deg2rad(args.bent_shoulder_forward_deg)
                body_pose_t[0, 15] = torch.tensor(shoulder_aa.astype(np.float32))
                out = bm(
                    betas=betas_t,
                    body_pose=body_pose_t.reshape(1, -1),
                    global_orient=global_orient_t,
                    transl=transl_t,
                    return_verts=True,
                )
                bv = out.vertices.detach().numpy()[0]
                bj = out.joints.detach().numpy()[0]
                disp = fit.get("displacement") if hasattr(fit, "get") else None
                if disp is None and "displacement" in fit.files:
                    disp = fit["displacement"]
                if disp is not None and disp.shape == bv.shape:
                    bv = bv + disp
                bl = build_landmark_set(bv, joints=bj, faces=faces)
                for code in ("L01", "L02", "L04"):
                    try:
                        cat.values[code] = float(
                            _CAT[code].compute(bv, faces, bl))
                    except Exception as e:  # noqa: BLE001
                        print(f"bent {code}: {e}")
                if "L01" in cat.values and "L02" in cat.values:
                    cat.values["L03"] = cat.values["L01"] - cat.values["L02"]
            except Exception as e:  # noqa: BLE001
                print(f"bent-arm override skipped: {e}")
        if run_named:
            print()
        print("=" * 52)
        print("Seamly catalog extractor")
        print("=" * 52)
        _print_table(cat.values, label="seamly_code")
        print(f"\n{len(cat.values)} extracted   {len(cat.skipped)} skipped")
        if args.show_skipped:
            print("\nSkipped:")
            for k, reason in sorted(cat.skipped.items()):
                print(f"  {k}: {reason}")
        if args.save_seamly_json:
            args.save_seamly_json.parent.mkdir(parents=True, exist_ok=True)
            args.save_seamly_json.write_text(
                json.dumps({k: float(v) for k, v in cat.values.items()}, indent=2)
            )
            print(f"\nsaved {args.save_seamly_json}")
        if args.save_csv:
            write_csv(cat.values, args.save_csv)
            print(f"saved {args.save_csv}")
        if args.save_smis:
            template = (args.smis_template
                        if args.smis_template and args.smis_template.is_file()
                        else None)
            write_smis_from_catalog(cat.values, args.save_smis, template)
            print(f"saved {args.save_smis}")

    if args.save_obj:
        write_obj(verts, faces, args.save_obj)
        print(f"saved {args.save_obj}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
