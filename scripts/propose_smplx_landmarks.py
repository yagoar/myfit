#!/usr/bin/env python3
"""Propose SMPL-X vertex IDs for every body landmark using joint positions.

All output is PROPOSED / unverified. Verify each in Blender per GUARDRAILS §3.

Usage:
    python scripts/propose_smplx_landmarks.py
    python scripts/propose_smplx_landmarks.py --output proposals.json
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np

MODEL_PARENT = Path(__file__).resolve().parent.parent / "data" / "body_models"

# Coordinate system (SMPL-X native, Y-up):
#   +Y = up       +X = model anatomical LEFT    +Z = ANTERIOR (front)
#   -Y = down     -X = model anatomical RIGHT   -Z = POSTERIOR (back)


def load_smplx_tpose():
    import smplx, torch
    model = smplx.create(str(MODEL_PARENT), model_type="smplx", gender="female", use_pca=False)
    with torch.no_grad():
        out = model()
    verts  = out.vertices[0].cpu().numpy().astype(np.float64)
    joints = out.joints[0].cpu().numpy().astype(np.float64)
    return verts, joints


def nv(verts, target, mask=None):
    """Index of vertex nearest to target, optionally within boolean mask."""
    if mask is not None and mask.any():
        sub = np.where(mask)[0]
        return int(sub[np.argmin(np.linalg.norm(verts[sub] - target, axis=1))])
    return int(np.argmin(np.linalg.norm(verts - target, axis=1)))


def box(verts, **kw):
    """Boolean mask for vertices inside an axis-aligned box.
    Keys: x_min, x_max, y_min, y_max, z_min, z_max  (any subset).
    """
    ax = dict(x=0, y=1, z=2)
    m = np.ones(len(verts), dtype=bool)
    for k, v in kw.items():
        a = ax[k[0]]
        m &= (verts[:, a] >= v) if k.endswith("_min") else (verts[:, a] <= v)
    return m


def propose(verts, J):
    """Return {landmark_name: vertex_id} for all 48 landmarks."""

    # ── Joint shortcuts (SMPL-X body joints 0-21) ───────────────────────────
    pel  = J[0];  lhip = J[1];   rhip = J[2]
    sp1  = J[3];  lkne = J[4];   rkne = J[5]
    sp2  = J[6];  lank = J[7];   rank = J[8]
    sp3  = J[9]
    neck = J[12]; lcol = J[13];  rcol = J[14]; head = J[15]
    lsho = J[16]; rsho = J[17]
    lelb = J[18]; relb = J[19]
    lwri = J[20]; rwri = J[21]

    p = {}

    # ── Midline torso (6) ────────────────────────────────────────────────────
    p["top_of_head"] = int(np.argmax(verts[:, 1]))

    m = box(verts, y_min=neck[1]-0.05, y_max=neck[1]+0.05,
                   z_min=neck[2]+0.01, x_min=-0.03, x_max=0.03)
    p["front_neck_point"] = nv(verts, neck + [0, 0, 0.08], m)

    m = box(verts, y_min=neck[1]-0.10, y_max=neck[1]-0.01,
                   z_min=neck[2]+0.01, x_min=-0.03, x_max=0.03)
    p["front_collar_bone"] = nv(verts, neck + [0, -0.06, 0.07], m)

    m = box(verts, y_min=neck[1]-0.05, y_max=neck[1]+0.05,
                   z_max=neck[2]-0.01, x_min=-0.03, x_max=0.03)
    p["c7"] = nv(verts, neck + [0, 0, -0.08], m)

    m = box(verts, y_min=sp2[1]-0.04, y_max=sp2[1]+0.04,
                   z_min=sp2[2]+0.02, x_min=-0.03, x_max=0.03)
    p["waist_cf"] = nv(verts, sp2 + [0, 0, 0.14], m)

    m = box(verts, y_min=sp2[1]-0.04, y_max=sp2[1]+0.04,
                   z_max=sp2[2]-0.02, x_min=-0.03, x_max=0.03)
    p["waist_cb"] = nv(verts, sp2 + [0, 0, -0.14], m)

    # ── Crotch (1) ──────────────────────────────────────────────────────────
    m = box(verts, y_min=pel[1]-0.22, y_max=pel[1]-0.04,
                   x_min=-0.05, x_max=0.05)
    p["crotch_midpoint"] = int(np.where(m)[0][np.argmin(verts[m, 1])])

    # ── Shoulders + neck-shoulder corners (4) ───────────────────────────────
    p["shoulder_neck_left"]  = nv(verts, lcol)
    p["shoulder_neck_right"] = nv(verts, rcol)

    m = box(verts, y_min=lsho[1]-0.06, y_max=lsho[1]+0.06,
                   z_min=lsho[2]-0.07, z_max=lsho[2]+0.07,
                   x_min=lsho[0]-0.02, x_max=lsho[0]+0.10)
    p["acromion_left"]  = int(np.where(m)[0][np.argmax(verts[m, 0])])

    m = box(verts, y_min=rsho[1]-0.06, y_max=rsho[1]+0.06,
                   z_min=rsho[2]-0.07, z_max=rsho[2]+0.07,
                   x_min=rsho[0]-0.10, x_max=rsho[0]+0.02)
    p["acromion_right"] = int(np.where(m)[0][np.argmin(verts[m, 0])])

    # ── Front shoulder midpoints (2) ────────────────────────────────────────
    for side, col, sho in [("left", lcol, lsho), ("right", rcol, rsho)]:
        mid = (col + sho) / 2
        m = box(verts, y_min=mid[1]-0.05, y_max=mid[1]+0.05,
                       z_min=mid[2],
                       x_min=mid[0]-0.05, x_max=mid[0]+0.05)
        p[f"front_shoulder_centre_{side}"] = nv(verts, mid + [0, 0, 0.02], m)

    # ── Underarm (2) ────────────────────────────────────────────────────────
    # Bottom of the armhole: lowest-Y vertex in a box around the shoulder joint
    for side, sho in [("left", lsho), ("right", rsho)]:
        m = box(verts, y_min=sho[1]-0.10, y_max=sho[1]+0.02,
                       x_min=sho[0]-0.07, x_max=sho[0]+0.07,
                       z_min=sho[2]-0.07, z_max=sho[2]+0.07)
        p[f"underarm_{side}"] = int(np.where(m)[0][np.argmin(verts[m, 1])])

    # ── Armscye + armfold (8) ───────────────────────────────────────────────
    # Upper-bust level = shoulder joint Y - small offset
    ub_y = lsho[1] - 0.03
    for side, sho in [("left", lsho), ("right", rsho)]:
        # Narrow band at upper-bust height, around the shoulder X
        m_band = box(verts, y_min=ub_y-0.05, y_max=ub_y+0.05,
                            x_min=sho[0]-0.07, x_max=sho[0]+0.07)
        # Armscye front: most anterior in band
        mf = m_band & box(verts, z_min=sho[2])
        p[f"armscye_front_{side}"] = nv(verts, sho + [0, -0.04, 0.05], mf) if mf.any() else -1
        # Armscye back: most posterior in band
        mb = m_band & box(verts, z_max=sho[2])
        p[f"armscye_back_{side}"]  = nv(verts, sho + [0, -0.04, -0.05], mb) if mb.any() else -1

        # Armfold = lower than armscye (inferior), at side-seam level
        m_low = box(verts, y_min=ub_y-0.09, y_max=ub_y-0.01,
                           x_min=sho[0]-0.06, x_max=sho[0]+0.06)
        mf2 = m_low & box(verts, z_min=sho[2])
        p[f"armfold_front_{side}"] = nv(verts, sho + [0, -0.09, 0.03], mf2) if mf2.any() else -1
        mb2 = m_low & box(verts, z_max=sho[2])
        p[f"armfold_back_{side}"]  = nv(verts, sho + [0, -0.09, -0.03], mb2) if mb2.any() else -1

    # ── Bust (3) ────────────────────────────────────────────────────────────
    # Bust apex: most anterior vertex in the breast region (between sp2 and sp3, lateral)
    bust_y = (sp2[1] + sp3[1]) / 2 + 0.04
    m = box(verts, y_min=bust_y-0.06, y_max=bust_y+0.07,
                   x_min=0.06, x_max=0.24, z_min=sp3[2]+0.02)
    p["bust_apex_left"]  = int(np.where(m)[0][np.argmax(verts[m, 2])]) if m.any() else -1

    m = box(verts, y_min=bust_y-0.06, y_max=bust_y+0.07,
                   x_min=-0.24, x_max=-0.06, z_min=sp3[2]+0.02)
    p["bust_apex_right"] = int(np.where(m)[0][np.argmax(verts[m, 2])]) if m.any() else -1

    lb_y = sp2[1] + (sp3[1] - sp2[1]) * 0.28
    m = box(verts, y_min=lb_y-0.04, y_max=lb_y+0.05,
                   z_min=sp2[2]+0.05, x_min=-0.03, x_max=0.03)
    p["lowbust_apex"] = nv(verts, [0, lb_y, sp2[2]+0.14], m) if m.any() else -1

    # ── Bra side seam (2) ───────────────────────────────────────────────────
    # Slightly posterior to underarm, at upper-bust level
    ub_y2 = lsho[1] - 0.02
    m = box(verts, y_min=ub_y2-0.04, y_max=ub_y2+0.04,
                   x_min=lsho[0]-0.10, x_max=lsho[0]-0.01)
    p["bra_side_seam_left"]  = int(np.where(m)[0][np.argmin(verts[m, 2])]) if m.any() else -1

    m = box(verts, y_min=ub_y2-0.04, y_max=ub_y2+0.04,
                   x_min=rsho[0]+0.01, x_max=rsho[0]+0.10)
    p["bra_side_seam_right"] = int(np.where(m)[0][np.argmin(verts[m, 2])]) if m.any() else -1

    # ── Waist sides (2) ─────────────────────────────────────────────────────
    m = box(verts, y_min=sp2[1]-0.05, y_max=sp2[1]+0.05, x_min=0.09)
    p["waist_side_left"]  = int(np.where(m)[0][np.argmax(verts[m, 0])]) if m.any() else -1

    m = box(verts, y_min=sp2[1]-0.05, y_max=sp2[1]+0.05, x_max=-0.09)
    p["waist_side_right"] = int(np.where(m)[0][np.argmin(verts[m, 0])]) if m.any() else -1

    # ── Arm (5) ─────────────────────────────────────────────────────────────
    for side, elb in [("left", lelb), ("right", relb)]:
        m = box(verts, y_min=elb[1]-0.06, y_max=elb[1]+0.06,
                       x_min=elb[0]-0.06, x_max=elb[0]+0.06)
        p[f"elbow_back_{side}"] = int(np.where(m)[0][np.argmin(verts[m, 2])]) if m.any() else -1

    for side, wri in [("left", lwri), ("right", rwri)]:
        m = box(verts, y_min=wri[1]-0.05, y_max=wri[1]+0.05,
                       x_min=wri[0]-0.06, x_max=wri[0]+0.06)
        p[f"wrist_ulnar_{side}"] = int(np.where(m)[0][np.argmin(verts[m, 2])]) if m.any() else -1

    # bicep: most anterior vertex midway between right shoulder and elbow
    bicep_y = (rsho[1] + relb[1]) / 2
    m = box(verts, y_min=bicep_y-0.08, y_max=bicep_y+0.05,
                   x_min=rsho[0]-0.05, x_max=rsho[0]+0.04)
    p["bicep_max_right"] = int(np.where(m)[0][np.argmax(verts[m, 2])]) if m.any() else -1

    # ── Leg (8) ─────────────────────────────────────────────────────────────
    for side, hip, fn in [("left", lhip, np.argmax), ("right", rhip, np.argmin)]:
        m = box(verts, y_min=hip[1]-0.10, y_max=hip[1]+0.05)
        sel = np.where(m)[0]
        sel = sel[np.abs(verts[sel, 0]) > 0.07]
        if side == "left":
            sel = sel[verts[sel, 0] > 0]
        else:
            sel = sel[verts[sel, 0] < 0]
        p[f"thigh_at_crotch_{side}"] = int(sel[fn(verts[sel, 0])]) if len(sel) else -1

    for side, hip, fn in [("left", lhip, np.argmax), ("right", rhip, np.argmin)]:
        crot_y = (pel[1] + hip[1]) / 2
        m = box(verts, y_min=crot_y-0.06, y_max=crot_y+0.06)
        sel = np.where(m)[0]
        sel = sel[np.abs(verts[sel, 0]) > 0.02]
        if side == "left":
            sel = sel[verts[sel, 0] > 0]
        else:
            sel = sel[verts[sel, 0] < 0]
        p[f"crotch_lateral_{side}"] = int(sel[fn(verts[sel, 0])]) if len(sel) else -1

    for side, kne in [("left", lkne), ("right", rkne)]:
        m = box(verts, y_min=kne[1]-0.07, y_max=kne[1]+0.06,
                       x_min=kne[0]-0.08, x_max=kne[0]+0.08)
        p[f"knee_back_{side}"] = int(np.where(m)[0][np.argmin(verts[m, 2])]) if m.any() else -1

    for side, ank, fn in [("left", lank, np.argmax), ("right", rank, np.argmin)]:
        m = box(verts, y_min=ank[1]-0.06, y_max=ank[1]+0.06)
        sel = np.where(m)[0]
        p[f"ankle_bone_lateral_{side}"] = int(sel[fn(verts[sel, 0])]) if len(sel) else -1

    # ── Plane anchors (2) ───────────────────────────────────────────────────
    rib_y = sp2[1] + (sp3[1] - sp2[1]) * 0.52
    m = box(verts, y_min=rib_y-0.04, y_max=rib_y+0.04,
                   z_min=sp2[2]+0.04, x_min=-0.03, x_max=0.03)
    p["rib_front"] = nv(verts, [0, rib_y, sp2[2]+0.13], m) if m.any() else -1

    mneck_y = (neck[1] + head[1]) / 2
    m = box(verts, y_min=mneck_y-0.04, y_max=mneck_y+0.04,
                   z_min=neck[2], x_min=-0.025, x_max=0.025)
    p["mid_neck_front"] = nv(verts, [0, mneck_y, neck[2]+0.06], m) if m.any() else -1

    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=None,
                        help="save proposals as JSON")
    args = parser.parse_args()

    print("loading SMPL-X female T-pose…")
    verts, joints = load_smplx_tpose()
    print(f"  {len(verts)} vertices, {len(joints)} joints")

    proposals = propose(verts, joints)

    # ── Print table ─────────────────────────────────────────────────────────
    failed = [k for k, v in proposals.items() if v == -1]
    print(f"\n{'Landmark':<35} {'vertex_id':>9}   {'coord (x, y, z)'}")
    print("-" * 80)
    for name, vid in proposals.items():
        if vid == -1:
            print(f"  {name:<33}  {'FAILED':>9}   (widen filter manually)")
        else:
            x, y, z = verts[vid]
            print(f"  {name:<33}  {vid:>9}   ({x:+.4f}, {y:+.4f}, {z:+.4f})")

    print(f"\n{len(proposals) - len(failed)}/{len(proposals)} proposed  "
          f"({len(failed)} failed)")

    if args.output:
        records = [
            {"landmark": k, "proposed_vertex_id": v,
             "coord": verts[v].tolist() if v != -1 else None}
            for k, v in proposals.items()
        ]
        args.output.write_text(json.dumps(records, indent=2))
        print(f"wrote {args.output}")

    if failed:
        print("\nFAILED landmarks need manual filter widening:")
        for f in failed:
            print(f"  {f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
