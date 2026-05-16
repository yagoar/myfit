"""Review-focused Dash viewer.

One measurement at a time. Prev/Next navigation. Five preset camera
angles (front, 45f, side, 45b, back). Per-code flag toggle + free-text
note. Notes persisted to disk on every edit and downloadable as JSON.

Run:
    python -m body_scanner.measure.review_viewer data/results/yaiza_smplx_fit.npz \
        --notes-json data/review/notes.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html

from .landmarks import build_landmark_set
from .primitives import recipe_polyline
from .seamly_catalog import CODE_TO_DIAGRAM, CODE_TO_NAME, RECIPES
from .seamly_extractor import extract_catalog
from .viewer import (
    _body_mesh_trace,
    _load_fit,
    _load_obj,
    _offset_along_normals,
    _vertex_normals,
)

ROOT = Path(__file__).resolve().parents[3]
DIAGRAM_DIR = ROOT / "references" / "seamly" / "diagrams"

ANGLE_PRESETS = {
    # azimuth (around vertical Y), elevation
    "front": (0, 0),
    "45f":   (45, 0),
    "side":  (90, 0),
    "45b":   (135, 0),
    "back":  (180, 0),
}


def _camera(centroid: np.ndarray, radius: float,
            az_deg: float, el_deg: float) -> dict:
    az = np.deg2rad(az_deg)
    el = np.deg2rad(el_deg)
    return dict(
        eye=dict(
            x=float(centroid[0] + radius * np.cos(el) * np.sin(az)),
            y=float(centroid[1] + radius * np.sin(el)),
            z=float(centroid[2] + radius * np.cos(el) * np.cos(az)),
        ),
        center=dict(x=float(centroid[0]),
                    y=float(centroid[1]),
                    z=float(centroid[2])),
        up=dict(x=0, y=1, z=0),
        projection=dict(type="perspective"),
    )


def _line_trace(poly: np.ndarray) -> go.Scatter3d:
    return go.Scatter3d(
        x=poly[:, 0], y=poly[:, 1], z=poly[:, 2],
        mode="lines",
        line=dict(color="#1e6fff", width=8),
        hoverinfo="skip",
    )


def _figure(body_trace, polyline: np.ndarray | None,
            camera: dict) -> go.Figure:
    traces = [body_trace]
    if polyline is not None and len(polyline) >= 2:
        traces.append(_line_trace(polyline))
    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#5a5e63",
            aspectmode="data",
            camera=camera,
        ),
        paper_bgcolor="#5a5e63",
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        # uirevision is shared so the user's free rotation persists when
        # cycling codes; the preset buttons set a fresh uirevision to force
        # the camera update.
        uirevision="locked",
    )
    return fig


def _load_notes(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text())
    return {}


def _save_notes(path: Path, notes: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=2, sort_keys=True))


def build_app(
    npz_path: Path,
    model_folder: str,
    gender: str,
    num_betas: int,
    notes_path: Path,
    scan_obj: Path | None = None,
    flagged_only: bool = False,
    filter_from: Path | None = None,
) -> Dash:
    verts, faces, joints = _load_fit(npz_path, model_folder, gender, num_betas)
    landmarks = build_landmark_set(verts, joints=joints, faces=faces)
    report = extract_catalog(verts, faces, joints=joints)

    polylines: dict[str, np.ndarray] = {}
    for code, recipe in RECIPES.items():
        try:
            poly = recipe_polyline(recipe, verts, faces, landmarks)
        except Exception:
            poly = None
        if poly is not None and len(poly) >= 2:
            polylines[code] = poly

    body_verts = verts
    body_faces = faces
    if scan_obj is not None:
        body_verts, body_faces = _load_obj(scan_obj)
    body_trace = _body_mesh_trace(body_verts, body_faces)
    body_normals = _vertex_normals(body_verts, body_faces)
    from .primitives import drape_polyline_on_body, should_drape
    new_polylines = {}
    for c, p in polylines.items():
        if should_drape(RECIPES.get(c)):
            new_polylines[c] = drape_polyline_on_body(
                p, body_verts, body_normals, faces=body_faces)
        else:
            new_polylines[c] = _offset_along_normals(p, body_verts, body_normals)
    polylines = new_polylines

    centroid = body_verts.mean(axis=0)
    extent = float(np.linalg.norm(body_verts.max(0) - body_verts.min(0)))
    radius = extent * 1.6

    notes = _load_notes(notes_path)
    # Filter source: either the live notes file or a separate filter file.
    # Lets us reset notes (empty) while still cycling only through a fixed
    # subset (e.g. the set of codes flagged in a prior review pass).
    filter_source = filter_from if filter_from is not None else notes_path
    if flagged_only:
        src = _load_notes(filter_source)
        flagged = {c for c, v in src.items() if v.get("flagged")}
        codes = sorted(c for c in polylines if c in flagged)
        if not codes:
            raise SystemExit(
                f"--flagged-only set but no flagged codes in {filter_source}.")
    else:
        codes = sorted(polylines.keys())
    if not codes:
        raise SystemExit("No renderable measurements.")
    # Initial camera = front view.
    cam_front = _camera(centroid, radius, *ANGLE_PRESETS["front"])

    app = Dash(__name__, title="measurement review")
    # Inject a keyboard listener that fires the prev/next buttons on
    # ArrowLeft / ArrowRight. Ignored when the focus is on the textarea
    # or a checkbox so notes don't get hijacked.
    app.index_string = """<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head>
<body>
{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
<script>
document.addEventListener('keydown', function(e) {
  var tag = (document.activeElement && document.activeElement.tagName) || '';
  if (tag === 'TEXTAREA' || tag === 'INPUT') return;
  if (e.key === 'ArrowLeft') {
    var b = document.getElementById('prev-btn'); if (b) b.click();
  } else if (e.key === 'ArrowRight') {
    var b = document.getElementById('next-btn'); if (b) b.click();
  } else if (['1','2','3','4','5'].indexOf(e.key) !== -1) {
    var names = ['front','45f','side','45b','back'];
    var b = document.getElementById('angle-' + names[parseInt(e.key) - 1]);
    if (b) b.click();
  }
});
</script>
</body>
</html>"""
    app.layout = html.Div([
        # URL-based deeplink: visit /?code=H06 to land on H06 directly.
        # The URL search string is also kept in sync with the current
        # code so you can copy/paste the address bar to share a view.
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="state", data={
            "idx": 0,
            "codes": codes,
            "notes_path": str(notes_path),
        }),
        html.Div([
            html.Button("◀ Prev", id="prev-btn",
                        style={"marginRight": "8px"}),
            html.Span(id="code-label", style={
                "fontWeight": 700, "fontSize": "16px",
                "marginRight": "16px"}),
            html.Span(id="name-label", style={
                "color": "#444", "marginRight": "16px"}),
            html.Span(id="value-label", style={
                "color": "#444", "marginRight": "16px"}),
            html.Span(id="counter-label", style={
                "color": "#888", "fontSize": "12px", "marginRight": "8px"}),
            html.Button("Next ▶", id="next-btn",
                        style={"marginLeft": "8px"}),
            html.A(
                html.Button("⬇ Export notes JSON"),
                id="export-link",
                href="",
                download="review_notes.json",
                style={"marginLeft": "24px"},
            ),
        ], style={
            "padding": "10px 18px",
            "borderBottom": "1px solid #ccc",
            "background": "#fff",
            "display": "flex",
            "alignItems": "center",
        }),
        html.Div([
            html.Div([
                html.Div([
                    html.Button(f"{i+1}. {name}", id=f"angle-{name}",
                                style={"marginRight": "6px"})
                    for i, name in enumerate(ANGLE_PRESETS)
                ], style={"padding": "8px 12px", "background": "#eee",
                          "borderBottom": "1px solid #ccc"}),
                dcc.Graph(
                    id="body-graph",
                    figure=_figure(body_trace, polylines[codes[0]], cam_front),
                    style={"height": "calc(100vh - 110px)", "width": "100%"},
                    config={"displayModeBar": False},
                ),
            ], style={"flex": "1 1 60%", "background": "#5a5e63"}),
            html.Div([
                html.Div("Seamly diagram",
                         style={"fontWeight": 600, "padding": "8px",
                                "borderBottom": "1px solid #eee"}),
                html.Div(id="diagram-box",
                         style={"padding": "12px", "textAlign": "center",
                                "background": "#fff",
                                "minHeight": "260px"}),
                html.Div("Review notes",
                         style={"fontWeight": 600, "padding": "8px",
                                "borderTop": "1px solid #ccc",
                                "borderBottom": "1px solid #eee"}),
                html.Div([
                    dcc.Checklist(
                        id="flag",
                        options=[{"label": " 🚩 flag for follow-up",
                                  "value": "flagged"}],
                        value=[],
                        style={"padding": "8px 12px"},
                    ),
                    dcc.Textarea(
                        id="note",
                        placeholder="Notes on point locations, trajectory, "
                                    "contouring vs straight line…",
                        style={"width": "calc(100% - 24px)", "height": "180px",
                               "margin": "0 12px", "fontSize": "13px"},
                    ),
                    html.Div(id="save-status",
                             style={"padding": "6px 12px", "fontSize": "11px",
                                    "color": "#666"}),
                ]),
            ], style={"flex": "0 0 380px", "background": "#fff",
                      "borderLeft": "1px solid #ccc", "overflowY": "auto"}),
        ], style={"display": "flex", "height": "calc(100vh - 60px)"}),
        # Stores the body+radius for camera updates.
        dcc.Store(id="cam-config", data={
            "centroid": centroid.tolist(),
            "radius": radius,
        }),
        # Pre-built polylines list (only what we'll redraw on switch).
        dcc.Store(id="polylines", data={c: p.tolist() for c, p in polylines.items()}),
        dcc.Store(id="body-trace-key", data=0),
    ])

    # Navigation: prev/next buttons + URL search (?code=XYZ) drive the
    # shared index. Whichever fires last wins. URL stays in sync via
    # the sync_url callback below.
    @app.callback(
        Output("state", "data"),
        Output("flag", "value"),
        Output("note", "value"),
        Input("prev-btn", "n_clicks"),
        Input("next-btn", "n_clicks"),
        Input("url", "search"),
        State("state", "data"),
    )
    def navigate(_p, _n, search, state):
        trig = ctx.triggered_id
        i = state["idx"]
        if trig == "prev-btn":
            i = (i - 1) % len(state["codes"])
        elif trig == "next-btn":
            i = (i + 1) % len(state["codes"])
        elif trig == "url" or trig is None:
            # Parse ?code=XYZ from the URL search string.
            from urllib.parse import parse_qs
            qs = parse_qs((search or "").lstrip("?"))
            code = (qs.get("code") or [None])[0]
            if code and code in state["codes"]:
                i = state["codes"].index(code)
        state["idx"] = i
        code = state["codes"][i]
        entry = notes.get(code, {})
        return state, (["flagged"] if entry.get("flagged") else []), entry.get("note", "")

    @app.callback(
        Output("url", "search"),
        Input("state", "data"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    def sync_url(state, current_search):
        code = state["codes"][state["idx"]]
        new = f"?code={code}"
        if (current_search or "") == new:
            from dash import no_update
            return no_update
        return new

    @app.callback(
        Output("code-label", "children"),
        Output("name-label", "children"),
        Output("value-label", "children"),
        Output("counter-label", "children"),
        Output("diagram-box", "children"),
        Input("state", "data"),
    )
    def update_header(state):
        code = state["codes"][state["idx"]]
        name = CODE_TO_NAME.get(code, "")
        val = report.values.get(code)
        val_s = f"{val:.2f} cm" if val is not None else "—"
        counter = f"{state['idx'] + 1} / {len(state['codes'])}"
        diag_base = CODE_TO_DIAGRAM.get(code)
        diagram = html.Span("(no diagram)", style={"color": "#999"})
        if diag_base:
            diag_path = DIAGRAM_DIR / f"{diag_base}.svg"
            if diag_path.is_file():
                # Serve through Dash assets by embedding inline.
                diagram = html.Img(
                    src=f"/diagram/{diag_base}.svg",
                    style={"maxWidth": "100%", "maxHeight": "280px"},
                )
        return code, name, val_s, counter, diagram

    @app.callback(
        Output("body-graph", "figure"),
        Input("state", "data"),
        *[Input(f"angle-{name}", "n_clicks") for name in ANGLE_PRESETS],
        State("cam-config", "data"),
    )
    def update_graph(state, *args):
        cam_cfg = args[-1]
        trig = ctx.triggered_id
        angle = "front"
        if isinstance(trig, str) and trig.startswith("angle-"):
            angle = trig[len("angle-"):]
        cam = _camera(
            np.array(cam_cfg["centroid"]),
            cam_cfg["radius"],
            *ANGLE_PRESETS[angle],
        )
        code = state["codes"][state["idx"]]
        fig = _figure(body_trace, polylines[code], cam)
        # Force camera apply by changing uirevision per angle click.
        fig.update_layout(uirevision=f"{code}-{angle}")
        return fig

    @app.callback(
        Output("save-status", "children"),
        Output("export-link", "href"),
        Input("flag", "value"),
        Input("note", "value"),
        State("state", "data"),
    )
    def save_note(flag, note, state):
        code = state["codes"][state["idx"]]
        notes.setdefault(code, {})
        notes[code]["flagged"] = bool(flag and "flagged" in flag)
        notes[code]["note"] = note or ""
        if not notes[code]["flagged"] and not notes[code]["note"]:
            notes.pop(code, None)
        _save_notes(notes_path, notes)
        # Build a data URI so the export link always carries the freshest
        # JSON without a separate route.
        payload = json.dumps(notes, indent=2, sort_keys=True)
        href = "data:application/json;charset=utf-8," + payload.replace("#", "%23")
        flagged = sum(1 for v in notes.values() if v.get("flagged"))
        return f"saved → {notes_path}  ({len(notes)} codes annotated, {flagged} flagged)", href

    # Serve diagram SVGs. Dash reserves /assets/, so use /diagram/.
    @app.server.route("/diagram/<path:filename>")
    def serve_diagram(filename):
        from flask import send_from_directory
        return send_from_directory(DIAGRAM_DIR, filename)

    return app


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--model-folder", default="data/body_models")
    p.add_argument("--gender", default="female")
    p.add_argument("--num-betas", type=int, default=300)
    p.add_argument("--port", type=int, default=8051)
    p.add_argument("--scan-obj", type=Path, default=None)
    p.add_argument(
        "--notes-json", type=Path,
        default=Path("data/review/review_notes.json"),
        help="Where to persist review notes. Auto-loaded on startup.",
    )
    p.add_argument(
        "--flagged-only", action="store_true",
        help="Cycle only through codes flagged in --filter-from (if set) "
             "else --notes-json. Lets you reset notes while keeping the "
             "code subset.",
    )
    p.add_argument(
        "--filter-from", type=Path, default=None,
        help="JSON file whose 'flagged' entries determine the code subset "
             "when --flagged-only is set. Defaults to --notes-json.",
    )
    args = p.parse_args()

    app = build_app(
        npz_path=args.fit_npz,
        model_folder=args.model_folder,
        gender=args.gender,
        num_betas=args.num_betas,
        notes_path=args.notes_json,
        scan_obj=args.scan_obj,
        flagged_only=args.flagged_only,
        filter_from=args.filter_from,
    )
    app.run(debug=False, port=args.port, host="127.0.0.1")


if __name__ == "__main__":
    raise SystemExit(main())
