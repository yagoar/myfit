"""Render every Seamly measurement line on the fitted SMPL-X body from
5 camera angles + assemble a per-code review.md alongside the Seamly
reference diagram.

Outputs to data/review/<code>/:
  - <code>_front.png, _45f.png, _side.png, _45b.png, _back.png
  - diagram.svg (copy of references/seamly/diagrams/<base>.svg)
  - meta.json (code, name, value_cm, recipe repr, diagram base)

A top-level data/review/index.md lists every code with thumbnails so the
human reviewer can compare angles against the diagram.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import smplx

from body_scanner.measure.landmarks import build_landmark_set
from body_scanner.measure.primitives import (
    drape_polyline_on_body,
    recipe_polyline,
    should_drape,
)
from body_scanner.measure.seamly_catalog import (
    CODE_TO_DIAGRAM,
    CODE_TO_NAME,
    RECIPES,
)

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = ROOT / "references" / "seamly" / "diagrams"

ANGLES = {
    # name : (azimuth_deg, elevation_deg)  - azimuth around vertical Y axis,
    # 0 = front (+Z), 90 = +X side, 180 = back (-Z), -90 = -X side.
    "front": (0, 0),
    "45f":   (45, 0),
    "side":  (90, 0),
    "45b":   (135, 0),
    "back":  (180, 0),
}


def _camera_eye(centroid: np.ndarray, radius: float,
                az_deg: float, el_deg: float) -> dict:
    az = np.deg2rad(az_deg)
    el = np.deg2rad(el_deg)
    eye_x = centroid[0] + radius * np.cos(el) * np.sin(az)
    eye_y = centroid[1] + radius * np.sin(el)
    eye_z = centroid[2] + radius * np.cos(el) * np.cos(az)
    return dict(
        eye=dict(x=float(eye_x), y=float(eye_y), z=float(eye_z)),
        center=dict(x=float(centroid[0]), y=float(centroid[1]),
                    z=float(centroid[2])),
        up=dict(x=0, y=1, z=0),
        projection=dict(type="perspective"),
    )


def _mesh_trace(verts, faces):
    return go.Mesh3d(
        x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
        i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        color="#d8dde2", opacity=0.55,
        flatshading=False, hoverinfo="skip",
        lighting=dict(ambient=0.35, diffuse=0.95, specular=0.08,
                      roughness=0.55, fresnel=0.10),
        lightposition=dict(x=-200, y=300, z=600),
    )


def _line_trace(poly: np.ndarray):
    return go.Scatter3d(
        x=poly[:, 0], y=poly[:, 1], z=poly[:, 2],
        mode="lines",
        line=dict(color="#1e7df0", width=8),
        hoverinfo="skip",
    )


def _render_code(code: str, body_trace, body_verts, polyline, out_dir: Path,
                 width: int = 600, height: int = 800):
    centroid = body_verts.mean(axis=0)
    extent = float(np.linalg.norm(body_verts.max(0) - body_verts.min(0)))
    radius = extent * 1.6
    line = _line_trace(polyline)
    for name, (az, el) in ANGLES.items():
        cam = _camera_eye(centroid, radius, az, el)
        fig = go.Figure(data=[body_trace, line])
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="#5a5e63",
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                bgcolor="#5a5e63",
                aspectmode="data",
                camera=cam,
            ),
        )
        fig.write_image(out_dir / f"{code}_{name}.png", width=width, height=height)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=300)
    p.add_argument("--out-dir", type=Path, default=Path("data/review"))
    p.add_argument("--codes", nargs="*", help="Restrict to these codes")
    args = p.parse_args()

    fit = np.load(args.fit_npz, allow_pickle=True)
    bm = smplx.create(
        model_path=args.model_folder,
        model_type="smplx",
        gender=args.gender,
        num_betas=args.num_betas,
        use_pca=False,
        batch_size=1,
    )
    verts = fit["smplx_vertices"]
    faces = np.asarray(bm.faces, dtype=np.int32)
    landmarks = build_landmark_set(verts, joints=fit["smplx_joints"])

    body_trace = _mesh_trace(verts, faces)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Per-vertex normals for draping straight-chord polylines onto the
    # body surface.
    from body_scanner.measure.viewer import _vertex_normals
    body_normals = _vertex_normals(verts, faces)

    codes = sorted(args.codes) if args.codes else sorted(RECIPES.keys())
    written = []
    for i, code in enumerate(codes, 1):
        recipe = RECIPES[code]
        try:
            poly = recipe_polyline(recipe, verts, faces, landmarks)
        except Exception as e:
            print(f"[{i}/{len(codes)}] {code}: polyline error {e}")
            continue
        if poly is None or len(poly) < 2:
            print(f"[{i}/{len(codes)}] {code}: no polyline (value-only)")
            continue
        if should_drape(recipe):
            poly = drape_polyline_on_body(poly, verts, body_normals, faces=faces)
        try:
            value = recipe.compute(verts, faces, landmarks)
        except Exception:
            value = float("nan")
        d = args.out_dir / code
        d.mkdir(exist_ok=True)
        try:
            _render_code(code, body_trace, verts, poly, d)
        except Exception as e:
            print(f"[{i}/{len(codes)}] {code}: render failed ({e}); retrying once")
            try:
                _render_code(code, body_trace, verts, poly, d)
            except Exception as e2:
                print(f"[{i}/{len(codes)}] {code}: render failed twice ({e2}); skipping")
                continue
        diag_base = CODE_TO_DIAGRAM.get(code)
        if diag_base:
            src = DIAGRAM_DIR / f"{diag_base}.svg"
            if src.is_file():
                shutil.copy(src, d / "diagram.svg")
        (d / "meta.json").write_text(json.dumps({
            "code": code,
            "name": CODE_TO_NAME.get(code, ""),
            "value_cm": float(value),
            "recipe": repr(recipe),
            "diagram_base": diag_base,
        }, indent=2))
        written.append(code)
        print(f"[{i}/{len(codes)}] {code}  {value:.2f} cm")

    # Index markdown.
    lines = ["# Measurement review", "",
             f"Fit: `{args.fit_npz}`  ({len(written)} codes rendered)", ""]
    for code in written:
        meta = json.loads((args.out_dir / code / "meta.json").read_text())
        lines.append(f"## {code} — {meta['name']}  ({meta['value_cm']:.2f} cm)")
        lines.append("")
        if (args.out_dir / code / "diagram.svg").is_file():
            lines.append(f"![diagram]({code}/diagram.svg)")
        for ang in ANGLES:
            lines.append(f"![{ang}]({code}/{code}_{ang}.png)")
        lines.append("")
        lines.append("**Notes:** (review TBD)")
        lines.append("")
    (args.out_dir / "index.md").write_text("\n".join(lines))
    print(f"wrote {args.out_dir / 'index.md'} ({len(written)} codes)")


if __name__ == "__main__":
    raise SystemExit(main())
