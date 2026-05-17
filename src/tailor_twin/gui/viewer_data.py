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
_SCHEMA_VERSION = 3


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
    # Invalidate disk cache if the fit npz OR any measure-module file
    # is newer than the cached payload. Code-mtime check catches
    # behavioural changes (e.g. hip_level landmark rewrite) that would
    # otherwise produce stale numbers without a schema bump.
    cache_floor = npz.stat().st_mtime
    try:
        from tailor_twin import measure as _measure_pkg
        measure_dir = Path(_measure_pkg.__file__).parent
        for py in measure_dir.glob("*.py"):
            cache_floor = max(cache_floor, py.stat().st_mtime)
    except Exception:  # noqa: BLE001
        pass
    if (cache_path.is_file()
            and cache_path.stat().st_mtime >= cache_floor):
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

    # Bent-arm codes need to be rendered against an elbow-flexed body,
    # not the A-pose. Repose once here and use the bent verts for both
    # the polyline compute and the OBJ that the viewer swaps in when
    # any L01/L02/L04 polyline is toggled visible.
    BENT_ARM_CODES = ("L01", "L02", "L04")
    bent_verts = None
    bent_body_path = npz.with_name(f"{name}_bent_arm_body.obj")
    try:
        import smplx
        from tailor_twin.measure.bent_arm import repose_bent_arm
        from tailor_twin.measure.exports import write_obj
        body_model = smplx.create(
            model_path="data/body_models", model_type="smplx",
            gender=gender, num_betas=300, use_pca=False, batch_size=1,
        )
        fit_data = np.load(npz)
        pose = repose_bent_arm(fit_data, body_model)
        bent_verts = pose.verts
        bent_landmarks = build_landmark_set(
            bent_verts, joints=pose.joints, faces=faces, gender=gender,
        )
        # Always rewrite — fast (no torch optim) and keeps the OBJ
        # in sync with the latest fit. mtime check is handled by the
        # outer payload cache.
        write_obj(bent_verts, faces, bent_body_path)
        bent_normals = _vertex_normals(bent_verts, faces)
    except Exception:  # noqa: BLE001
        bent_verts = None  # pipeline runs without bent-arm if smplx unavailable

    polylines: dict[str, list[list[float]]] = {}
    polyline_pose: dict[str, str] = {}  # code -> "a_pose" | "bent_arm"
    for code, recipe in RECIPES.items():
        # Skip codes the extractor dropped (female-only on male fits,
        # judgment-only, non-finite recipe output). No value -> no
        # selectable row in the viewer; computing the polyline anyway
        # would waste the heat-method pass and surface a checkbox that
        # toggles a curve with no number.
        if code not in report.values:
            continue
        use_bent = bent_verts is not None and code in BENT_ARM_CODES
        v_eval = bent_verts if use_bent else verts
        lm_eval = bent_landmarks if use_bent else landmarks
        body_v = bent_verts if use_bent else body_verts
        body_n = bent_normals if use_bent else body_normals
        body_f = faces if use_bent else body_faces
        try:
            poly = recipe_polyline(recipe, v_eval, faces, lm_eval)
        except Exception:  # noqa: BLE001 — recipe may fail on any figure.
            poly = None
        if poly is None or len(poly) < 2:
            continue
        if should_drape(recipe):
            poly = drape_polyline_on_body(
                poly, body_v, body_n, faces=body_f)
        else:
            poly = _offset_along_normals(poly, body_v, body_n)
        polylines[code] = np.asarray(poly, dtype=float).tolist()
        polyline_pose[code] = "bent_arm" if use_bent else "a_pose"

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
        "bent_arm_obj_url": (
            f"/api/scan/{name}/bent-arm-obj"
            if bent_body_path.is_file() else ""
        ),
        "centroid": centroid,
        "extent": extent,
        "measurements": measurements,
        "polylines": polylines,
        "polyline_pose": polyline_pose,
    }
    try:
        cache_path.write_text(json.dumps(payload))
    except OSError:
        pass  # read-only filesystem etc. — keep the in-memory cache.
    _CACHE[key] = payload
    return payload
