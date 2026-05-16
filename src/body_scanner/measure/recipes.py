"""Measurement recipes operating on a fitted SMPL-X mesh.

Each recipe takes the fitted mesh (verts, faces), the LandmarkSet, and a
parameter dict from merged.yaml. Returns a value in centimetres.

Recipes implemented in this first pass:
  - planar_slice (output: convex_hull_perimeter)
  - planar_segment (outputs: chord_distance, arc_length_front,
                     arc_length_back, straight_surface_distance)
  - derived (formula over previously computed measurements)

Skipped for now (Phase 6 follow-up):
  - geodesic_path (needs potpourri3d heat method)
  - contoured_path
  - table_lookup
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .landmarks import LandmarkSet
from .mesh_ops import (
    _build_loops,
    _convex_hull_perimeter,
    _loop_xz,
    _pick_largest_loop,
    _pick_loop_near_point,
    _pick_torso_loop,
    _polygon_perimeter,
    slice_mesh,
)
from .primitives import Geodesic, GeodesicLoop
from .regions import region_vertex_mask


# Back-compat re-exports for callers that import these from recipes.
__all__ = [
    "_build_loops",
    "_convex_hull_perimeter",
    "_loop_xz",
    "_pick_largest_loop",
    "_pick_loop_near_point",
    "_pick_torso_loop",
    "_polygon_perimeter",
    "slice_mesh",
    "RECIPE_DISPATCH",
    "derived",
]


# ---------------------------------------------------------------------------
# Plane resolver — turns a yaml plane spec into (origin, normal) in metres.
# ---------------------------------------------------------------------------


def _resolve_axis(spec: str) -> np.ndarray:
    """Map an axis spec (e.g. 'pose.measurement_default.vertical_axis' or
    '-pose.measurement_default.vertical_axis') to a unit vector. We assume
    the fitted mesh is in SMPL-X canonical axes: +Y up, +X anatomical
    left, +Z anterior. The 'measurement_default' pose currently inherits
    these axes (pose-aware un-posing is Phase 6+)."""
    sign = -1.0 if spec.startswith("-") else 1.0
    key = spec.lstrip("-")
    if key.endswith("vertical_axis"):
        return sign * np.array([0.0, 1.0, 0.0])
    if key.endswith("anterior_axis"):
        return sign * np.array([0.0, 0.0, 1.0])
    if key.endswith("lateral_axis"):
        return sign * np.array([1.0, 0.0, 0.0])
    raise ValueError(f"unknown axis spec: {spec!r}")


def _resolve_origin(spec: Any, landmarks: LandmarkSet) -> np.ndarray:
    """Resolve a plane origin: either a bare landmark name, or a dict
    {along: <axis>, from_origin: <landmark>, distance_cm: N}."""
    if isinstance(spec, str):
        return landmarks[spec]
    if isinstance(spec, dict) and "from_origin" in spec:
        base = landmarks[spec["from_origin"]]
        axis = _resolve_axis(spec["along"])
        return base + axis * (float(spec["distance_cm"]) / 100.0)
    raise ValueError(f"cannot resolve plane origin: {spec!r}")


# ---------------------------------------------------------------------------
# Public recipes.
# ---------------------------------------------------------------------------


_REGION_ALIAS = {
    # merged.yaml uses singular names; expand to region tuples used by
    # body_scanner.measure.regions.REGIONS.
    "torso": ("torso",),
    "torso_no_head": ("torso_no_head",),
    "lower_body": ("torso", "left_leg", "right_leg"),
    "left_arm": ("left_arm",),
    "right_arm": ("right_arm",),
    "left_leg": ("left_leg",),
    "right_leg": ("right_leg",),
}


def _vertex_mask_from_params(params: dict) -> np.ndarray | None:
    rm = params.get("region_mask")
    if not rm:
        return None
    regions = _REGION_ALIAS.get(rm, (rm,))
    return region_vertex_mask(regions)


def planar_slice(
    verts: np.ndarray,
    faces: np.ndarray,
    landmarks: LandmarkSet,
    params: dict,
) -> float:
    """Horizontal slice through the mesh, convex-hull perimeter in cm.

    yaml shape:
      parameters:
        plane:
          origin: landmarks.X     (or {along, from_origin, distance_cm})
          normal: pose.measurement_default.vertical_axis
        region_mask: torso        (optional — restrict to body region)
        output: convex_hull_perimeter
    """
    origin = _resolve_origin(params["plane"]["origin"], landmarks)
    if "offset" in params["plane"]:
        off = params["plane"]["offset"]
        axis = _resolve_axis(off["along"])
        origin = origin + axis * (float(off["distance_cm"]) / 100.0)
    normal = _resolve_axis(params["plane"]["normal"])
    mask = _vertex_mask_from_params(params)
    segs = slice_mesh(verts, faces, origin, normal, vertex_mask=mask)
    loops = _build_loops(segs)
    loop = _pick_torso_loop(loops)
    if loop is None:
        return float("nan")
    xy = _loop_xz(loop, normal)
    output = params.get("output", "convex_hull_perimeter")
    if output == "convex_hull_perimeter":
        return _convex_hull_perimeter(xy) * 100.0  # m -> cm
    if output == "closed_geodesic_perimeter":
        return _polygon_perimeter(xy) * 100.0
    raise NotImplementedError(f"planar_slice output {output!r}")


def planar_segment(
    verts: np.ndarray,
    faces: np.ndarray,
    landmarks: LandmarkSet,
    params: dict,
) -> float:
    """Straight-chord segment between two landmarks, or arc on a slice.

    For chord_distance: straight 3D distance between clip.start and clip.end.
    For arc_length_front/back: take the slice loop, find arcs between the
    two clip landmarks, pick the front (higher mean Z) or back (lower)
    arc, return its length in cm.
    """
    output = params.get("output", "chord_distance")
    start = landmarks[params["clip"]["start"]]
    end = landmarks[params["clip"]["end"]]
    if output in ("chord_distance", "straight_surface_distance"):
        return float(np.linalg.norm(end - start)) * 100.0

    if output in ("arc_length_front", "arc_length_back"):
        origin = _resolve_origin(params["plane"]["origin"], landmarks)
        if "offset" in params["plane"]:
            off = params["plane"]["offset"]
            axis = _resolve_axis(off["along"])
            origin = origin + axis * (float(off["distance_cm"]) / 100.0)
        normal = _resolve_axis(params["plane"]["normal"])
        mask = _vertex_mask_from_params(params)
        segs = slice_mesh(verts, faces, origin, normal, vertex_mask=mask)
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops)
        if loop is None:
            return float("nan")
        # Find the two loop vertices closest to start and end.
        i0 = int(np.argmin(np.linalg.norm(loop - start, axis=1)))
        i1 = int(np.argmin(np.linalg.norm(loop - end, axis=1)))
        if i0 == i1:
            return float("nan")
        # Two arcs along the loop; pick by mean Z.
        n = len(loop)
        a_idx = list(range(i0, i1 + 1)) if i0 < i1 else list(range(i0, n)) + list(range(0, i1 + 1))
        b_idx = list(range(i1, i0 + 1)) if i1 < i0 else list(range(i1, n)) + list(range(0, i0 + 1))
        arc_a, arc_b = loop[a_idx], loop[b_idx]
        is_front = output == "arc_length_front"
        # Anterior = +Z; pick the arc whose mean Z matches.
        if (arc_a[:, 2].mean() > arc_b[:, 2].mean()) == is_front:
            arc = arc_a
        else:
            arc = arc_b
        diffs = np.diff(arc, axis=0)
        return float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) * 100.0

    raise NotImplementedError(f"planar_segment output {output!r}")


def derived(
    verts: np.ndarray,
    faces: np.ndarray,
    landmarks: LandmarkSet,
    params: dict,
    measured: dict[str, float],
) -> float:
    """Compute a derived measurement from previously computed values.

    yaml shape:
      parameters:
        formula: "0.5 * aldrich_bust - 1.0"
    """
    expr = params.get("formula") or params.get("expression")
    if expr is None:
        raise ValueError("derived recipe requires `formula` or `expression`")
    # Restricted eval — only known names + arithmetic.
    safe_globals = {"__builtins__": {}}
    safe_locals = dict(measured)
    return float(eval(expr, safe_globals, safe_locals))


def geodesic_path(
    verts: np.ndarray,
    faces: np.ndarray,
    landmarks: LandmarkSet,
    params: dict,
) -> float:
    """Geodesic path through ordered waypoint landmarks.

    yaml shape:
      type: geodesic_path
      parameters:
        waypoints: [landmarks.A, landmarks.B, ...]    # >=2
    """
    wp = tuple(params["waypoints"])
    return Geodesic(wp).compute(verts, faces, landmarks)


def geodesic_loop(
    verts: np.ndarray,
    faces: np.ndarray,
    landmarks: LandmarkSet,
    params: dict,
) -> float:
    """Closed geodesic loop through ordered waypoints.

    yaml shape:
      type: geodesic_loop
      parameters:
        waypoints: [landmarks.A, landmarks.B, landmarks.C, ...]    # >=3
    """
    wp = tuple(params["waypoints"])
    return GeodesicLoop(wp).compute(verts, faces, landmarks)


# Dispatch table — extended as more types are wired up.
RECIPE_DISPATCH: dict[str, Callable] = {
    "planar_slice": planar_slice,
    "planar_segment": planar_segment,
    "geodesic_path": geodesic_path,
    "geodesic_loop": geodesic_loop,
}
