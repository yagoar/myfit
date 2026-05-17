"""Viewer-side data loading: discover scans + compute measurement polylines.

Heavy imports (numpy, smplx, the measure subpackage) are deferred to
the first call so importing the GUI module stays cheap. Results are
cached per scan prefix to amortise the SMPL-X-load cost across page
reloads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Per-prefix payload cache. Keyed by the absolute results dir + the
# scan prefix so different repos / out dirs don't collide if anyone
# imports this from a custom path.
_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def list_scans(results_dir: Path) -> list[dict[str, str]]:
    """Discover scan prefixes under ``results_dir``.

    A "scan" is any ``<prefix>_smplx_fit.npz`` file. The matching
    fitted OBJ is reported alongside so the front-end can disable
    entries without an OBJ.
    """
    out: list[dict[str, str]] = []
    if not results_dir.is_dir():
        return out
    for npz in sorted(results_dir.glob("*_smplx_fit.npz")):
        name = npz.name.removesuffix("_smplx_fit.npz")
        obj = results_dir / f"{name}_fit_body.obj"
        out.append({
            "name": name,
            "has_obj": obj.is_file(),
            "obj_url": f"/api/scan/{name}/obj" if obj.is_file() else "",
        })
    return out


def scan_payload(results_dir: Path, name: str) -> dict[str, Any]:
    """Build the JSON payload for a single scan.

    Returns measurement values + per-code polylines (lists of ``[x, y,
    z]`` points in metres, world frame) + the scan name + OBJ URL.
    """
    key = (str(results_dir.resolve()), name)
    if key in _CACHE:
        return _CACHE[key]

    npz = results_dir / f"{name}_smplx_fit.npz"
    obj = results_dir / f"{name}_fit_body.obj"
    if not npz.is_file():
        raise FileNotFoundError(f"fit npz not found: {npz}")

    # Deferred imports — heavy.
    import numpy as np

    from body_scanner.measure.landmarks import build_landmark_set
    from body_scanner.measure.primitives import (
        drape_polyline_on_body,
        recipe_polyline,
        should_drape,
    )
    from body_scanner.measure.seamly_catalog import (
        CODE_TO_NAME,
        FORMULAS,
        RECIPES,
    )
    from body_scanner.measure.seamly_extractor import extract_catalog
    from body_scanner.measure.viewer import (
        _load_fit,
        _load_obj,
        _offset_along_normals,
        _vertex_normals,
    )

    verts, faces, joints = _load_fit(
        npz, "data/body_models", "female", 300,
    )
    landmarks = build_landmark_set(verts, joints=joints, faces=faces)
    report = extract_catalog(verts, faces, joints=joints)

    body_verts, body_faces = (
        _load_obj(obj) if obj.is_file() else (verts, faces)
    )
    body_normals = _vertex_normals(body_verts, body_faces)

    polylines: dict[str, list[list[float]]] = {}
    for code, recipe in RECIPES.items():
        try:
            poly = recipe_polyline(recipe, verts, faces, landmarks)
        except Exception:  # noqa: BLE001 — recipe may fail on any figure.
            poly = None
        if poly is None or len(poly) < 2:
            continue
        if should_drape(recipe):
            poly = drape_polyline_on_body(
                poly, body_verts, body_normals, faces=body_faces)
        else:
            poly = _offset_along_normals(poly, body_verts, body_normals)
        polylines[code] = np.asarray(poly, dtype=float).tolist()

    measurements = []
    for code in sorted(set(polylines) | set(report.values)):
        v = report.values.get(code)
        formula = FORMULAS.get(code)
        measurements.append({
            "code": code,
            "name": CODE_TO_NAME.get(code, ""),
            "value_cm": (float(v) if v is not None else None),
            "has_polyline": code in polylines,
            "formula": formula.expr if formula is not None else None,
        })

    centroid = body_verts.mean(axis=0).tolist()
    extent = float(np.linalg.norm(
        body_verts.max(axis=0) - body_verts.min(axis=0)))

    payload = {
        "name": name,
        "obj_url": f"/api/scan/{name}/obj" if obj.is_file() else "",
        "centroid": centroid,
        "extent": extent,
        "measurements": measurements,
        "polylines": polylines,
    }
    _CACHE[key] = payload
    return payload
