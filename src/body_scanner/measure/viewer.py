"""Interactive measurement viewer — Dash + Plotly.

Loads a fit.npz, runs the Seamly catalog extractor, and serves a single-page
web app:
  - left pane: fitted SMPL-X mesh in 3D
  - right pane: scrollable measurement list grouped by Seamly group letter,
                with checkboxes that overlay the measurement's slice / arc /
                geodesic / chord on the body
  - header line with bust/waist/hip + height

Run:
    python -m body_scanner.measure.viewer data/results/yaiza_smplx_fit.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import smplx
from dash import Dash, Input, Output, dcc, html

from .landmarks import build_landmark_set
from .primitives import recipe_polyline
from .seamly_catalog import CODE_TO_NAME, FORMULAS, RECIPES
from .seamly_extractor import extract_catalog


GROUP_LABELS = {
    "A": "Heights",
    "B": "Widths",
    "G": "Circumferences & Arcs",
    "H": "Vertical Distances",
    "I": "Shoulder & Across",
    "J": "Bustpoint",
    "K": "Shoulder/Neck Paths",
    "L": "Arm",
    "M": "Leg",
    "N": "Crotch & Rise",
    "O": "Natural Waist & Arm Ext",
    "P": "Complex Torso Paths",
}


# ---------------------------------------------------------------------------
# Data pipeline (runs once at startup).
# ---------------------------------------------------------------------------


def _load_fit(npz_path: Path, model_folder: str, gender: str,
              num_betas: int) -> tuple[np.ndarray, np.ndarray]:
    fit = np.load(npz_path)
    verts = fit["smplx_vertices"].astype(np.float32)
    bm = smplx.create(model_path=model_folder, model_type="smplx",
                      gender=gender, num_betas=num_betas, use_pca=False,
                      batch_size=1)
    faces = np.asarray(bm.faces, dtype=np.int32)
    return verts, faces


def _build_polylines(verts, faces, landmarks):
    """Map code -> (N, 3) polyline. Skips codes without a visualisable shape."""
    out: dict[str, np.ndarray] = {}
    for code, recipe in RECIPES.items():
        poly = recipe_polyline(recipe, verts, faces, landmarks)
        if poly is not None and len(poly) >= 2:
            out[code] = poly
    return out


# ---------------------------------------------------------------------------
# Plotly figure builders.
# ---------------------------------------------------------------------------


def _body_mesh_trace(verts: np.ndarray, faces: np.ndarray) -> go.Mesh3d:
    return go.Mesh3d(
        x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
        i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        color="#dadada",
        opacity=1.0,
        flatshading=False,
        lighting=dict(ambient=0.55, diffuse=0.8, specular=0.05),
        lightposition=dict(x=200, y=400, z=300),
        hoverinfo="skip",
        name="body",
        showscale=False,
    )


def _line_trace(poly: np.ndarray, label: str) -> go.Scatter3d:
    return go.Scatter3d(
        x=poly[:, 0], y=poly[:, 1], z=poly[:, 2],
        mode="lines",
        line=dict(color="#1e6fff", width=6),
        name=label,
        hoverinfo="name",
    )


def _figure(body_trace, selected_polylines: dict[str, tuple[np.ndarray, str]]) -> go.Figure:
    fig = go.Figure(data=[body_trace] + [
        _line_trace(poly, label) for poly, label in selected_polylines.values()
    ])
    # Body is roughly 0.95m wide x 1.6m tall; lock aspect.
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#888c93",
            aspectmode="data",
            camera=dict(eye=dict(x=0, y=0.2, z=2.4),
                        up=dict(x=0, y=1, z=0)),
        ),
        paper_bgcolor="#888c93",
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        uirevision="locked",  # preserve user's rotation across callbacks
    )
    return fig


# ---------------------------------------------------------------------------
# Layout builders.
# ---------------------------------------------------------------------------


def _measurement_panel(
    catalog_values: dict[str, float],
    has_polyline: set[str],
) -> html.Div:
    """Right-side panel. Groups by Seamly letter; each group is a section
    with a checklist."""
    sections = []
    all_codes = sorted(set(catalog_values))
    for group, label in GROUP_LABELS.items():
        codes = [c for c in all_codes if c.startswith(group)]
        if not codes:
            continue
        options = []
        for code in codes:
            name = CODE_TO_NAME.get(code, "")
            v = catalog_values.get(code)
            v_str = f"{v:.2f}" if v is not None else "—"
            disabled = code not in has_polyline
            label_text = f"{code}  {name}  ({v_str})"
            if disabled:
                label_text += "  [derived]"
            options.append(
                {"label": html.Span(label_text,
                                    style={"opacity": 0.6 if disabled else 1.0,
                                           "fontSize": "12px"}),
                 "value": code, "disabled": disabled}
            )
        sections.append(
            html.Details([
                html.Summary(f"{group} — {label} ({len(codes)})",
                             style={"fontWeight": 600, "fontSize": "13px",
                                    "padding": "8px 4px", "cursor": "pointer"}),
                dcc.Checklist(
                    id={"type": "group-checklist", "group": group},
                    options=options,
                    value=[],
                    style={"padding": "4px 12px"},
                    inputStyle={"marginRight": "6px"},
                ),
            ], open=group in ("G", "B", "A"))
        )
    return html.Div(sections, style={
        "overflowY": "auto", "height": "100vh", "padding": "12px",
        "borderLeft": "1px solid #ccc", "background": "#fff",
    })


def _header(catalog_values: dict[str, float], npz_path: Path) -> html.Div:
    """Mimic the top strip of the inspiration UI: name + Height/Bust/Waist/Hip."""
    quick = []
    for code, label in [("A01", "Height"), ("G04", "Bust"),
                        ("G07", "Waist"), ("G09", "Hip")]:
        v = catalog_values.get(code)
        v_str = f"{v:.1f} cm" if v is not None else "—"
        quick.append(html.Span(f"{label}: {v_str}",
                               style={"marginRight": "18px"}))
    return html.Div(
        [html.Span(f"{npz_path.name}",
                   style={"fontWeight": 600, "fontSize": "14px",
                          "marginRight": "20px"})] + quick,
        style={"padding": "10px 18px", "borderBottom": "1px solid #ccc",
               "fontSize": "13px", "background": "#fff"},
    )


# ---------------------------------------------------------------------------
# App.
# ---------------------------------------------------------------------------


def build_app(npz_path: Path, model_folder: str, gender: str,
              num_betas: int) -> Dash:
    verts, faces = _load_fit(npz_path, model_folder, gender, num_betas)
    landmarks = build_landmark_set(verts)
    report = extract_catalog(verts, faces)
    polylines = _build_polylines(verts, faces, landmarks)
    body_trace = _body_mesh_trace(verts, faces)
    initial_fig = _figure(body_trace, {})

    app = Dash(__name__, title="body-scanner viewer")
    app.layout = html.Div([
        _header(report.values, npz_path),
        html.Div([
            html.Div(
                dcc.Graph(
                    id="body-graph", figure=initial_fig,
                    style={"height": "calc(100vh - 50px)", "width": "100%"},
                    config={"displayModeBar": False},
                ),
                style={"flex": "1 1 70%", "background": "#888c93"},
            ),
            html.Div(
                _measurement_panel(report.values, set(polylines)),
                style={"flex": "0 0 360px"},
            ),
        ], style={"display": "flex", "height": "calc(100vh - 50px)"}),
    ], style={"margin": 0, "fontFamily": "system-ui, sans-serif"})

    # Store the polylines + body_trace in closure for the callback.
    @app.callback(
        Output("body-graph", "figure"),
        Input({"type": "group-checklist", "group": "A"}, "value"),
        Input({"type": "group-checklist", "group": "B"}, "value"),
        Input({"type": "group-checklist", "group": "G"}, "value"),
        Input({"type": "group-checklist", "group": "H"}, "value"),
        Input({"type": "group-checklist", "group": "I"}, "value"),
        Input({"type": "group-checklist", "group": "J"}, "value"),
        Input({"type": "group-checklist", "group": "K"}, "value"),
        Input({"type": "group-checklist", "group": "L"}, "value"),
        Input({"type": "group-checklist", "group": "M"}, "value"),
        Input({"type": "group-checklist", "group": "N"}, "value"),
        Input({"type": "group-checklist", "group": "O"}, "value"),
        Input({"type": "group-checklist", "group": "P"}, "value"),
    )
    def update_figure(*group_selections):
        selected_codes: list[str] = []
        for sel in group_selections:
            if sel:
                selected_codes.extend(sel)
        selected: dict[str, tuple[np.ndarray, str]] = {}
        for code in selected_codes:
            if code in polylines:
                name = CODE_TO_NAME.get(code, code)
                v = report.values.get(code)
                label = f"{code} {name} = {v:.2f} cm" if v is not None else code
                selected[code] = (polylines[code], label)
        return _figure(body_trace, selected)

    return app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Interactive measurement viewer.")
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=100)
    p.add_argument("--port", type=int, default=8050)
    args = p.parse_args(argv)

    app = build_app(args.fit_npz, args.model_folder, args.gender,
                    args.num_betas)
    app.run(debug=False, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
