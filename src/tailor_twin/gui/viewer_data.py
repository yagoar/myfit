"""Viewer-side data loading: discover scans + compute measurement polylines.

Heavy imports (numpy, smplx, the measure subpackage) are deferred to
the first call so importing the GUI module stays cheap. Results are
cached per scan prefix to amortise the SMPL-X-load cost across page
reloads, and persisted to a `<name>_viewer_payload.json` next to the
fit npz so subsequent process restarts are instant. The on-disk
payload is invalidated when its mtime is older than the fit npz, or
when the persisted ``schema_version`` doesn't match ``_SCHEMA_VERSION``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Per-prefix payload cache. Keyed by the absolute results dir + the
# scan prefix so different repos / out dirs don't collide if anyone
# imports this from a custom path.
_CACHE: dict[tuple[str, str], dict[str, Any]] = {}

# Bump when the payload shape changes (new fields, renamed fields,
# different unit conventions). Older persisted payloads are recomputed.
_SCHEMA_VERSION = 1


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

    Read order: in-process cache → ``<name>_viewer_payload.json`` on
    disk (if newer than the fit npz) → fresh compute. The fresh-compute
    path also writes the disk cache so subsequent process restarts
    skip the ~30s recipe evaluation.
    """
    key = (str(results_dir.resolve()), name)
    if key in _CACHE:
        return _CACHE[key]

    npz = results_dir / f"{name}_smplx_fit.npz"
    obj = results_dir / f"{name}_fit_body.obj"
    if not npz.is_file():
        raise FileNotFoundError(f"fit npz not found: {npz}")

    cache_path = results_dir / f"{name}_viewer_payload.json"
    if (cache_path.is_file()
            and cache_path.stat().st_mtime >= npz.stat().st_mtime):
        try:
            persisted = json.loads(cache_path.read_text())
            if persisted.get("schema_version") == _SCHEMA_VERSION:
                _CACHE[key] = persisted
                return persisted
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable cache — fall through to recompute.
            pass

    # Deferred imports — heavy.
    import numpy as np

    from tailor_twin.fit.fit import fit_gender
    from tailor_twin.measure.landmarks import build_landmark_set
    from tailor_twin.measure.primitives import (
        drape_polyline_on_body,
        recipe_polyline,
        should_drape,
    )
    from tailor_twin.measure.seamly_catalog import (
        CODE_TO_NAME,
        FORMULAS,
        RECIPES,
    )
    from tailor_twin.measure.seamly_extractor import extract_catalog
    from tailor_twin.measure.viewer import (
        _load_fit,
        _load_obj,
        _offset_along_normals,
        _vertex_normals,
    )

    gender = fit_gender(np.load(npz))
    verts, faces, joints = _load_fit(
        npz, "data/body_models", gender, 300,
    )
    landmarks = build_landmark_set(verts, joints=joints, faces=faces,
                                    gender=gender)
    report = extract_catalog(verts, faces, joints=joints, gender=gender)

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
        "schema_version": _SCHEMA_VERSION,
        "name": name,
        "gender": gender,
        "obj_url": f"/api/scan/{name}/obj" if obj.is_file() else "",
        "centroid": centroid,
        "extent": extent,
        "measurements": measurements,
        "polylines": polylines,
    }
    try:
        cache_path.write_text(json.dumps(payload))
    except OSError:
        pass  # read-only filesystem etc. — keep the in-memory cache.
    _CACHE[key] = payload
    return payload
