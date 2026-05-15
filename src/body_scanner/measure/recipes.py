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
from scipy.spatial import ConvexHull

from .landmarks import LandmarkSet


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
# Planar slice through a triangle mesh.
# ---------------------------------------------------------------------------


def slice_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    plane_origin: np.ndarray,
    plane_normal: np.ndarray,
) -> list[np.ndarray]:
    """Intersect a mesh with a plane. Returns a list of polylines, each an
    (N, 3) array of consecutive vertices on the slice. Polylines are
    open-form line segments per triangle, not joined into closed loops yet.

    Implementation: for each triangle, compute signed distance of vertices
    to the plane; if they don't all share sign, find the two crossing
    edges and interpolate the crossing point.
    """
    n = plane_normal / np.linalg.norm(plane_normal)
    d = (verts - plane_origin) @ n  # signed distance per vertex
    segs: list[np.ndarray] = []
    for tri in faces:
        d0, d1, d2 = d[tri[0]], d[tri[1]], d[tri[2]]
        signs = np.array([d0, d1, d2]) > 0.0
        if signs.all() or (~signs).all():
            continue  # whole triangle on one side
        edges = [(0, 1), (1, 2), (2, 0)]
        crossings = []
        for a, b in edges:
            da, db = d[tri[a]], d[tri[b]]
            if (da > 0) != (db > 0):
                t = da / (da - db)
                p = verts[tri[a]] * (1 - t) + verts[tri[b]] * t
                crossings.append(p)
        if len(crossings) == 2:
            segs.append(np.stack(crossings))
    return segs


def _build_loops(segs: list[np.ndarray], merge_tol: float = 1e-6) -> list[np.ndarray]:
    """Stitch unordered line segments into closed loops.

    Each segment has two endpoints. We walk a graph over endpoints,
    snapping near-duplicates within merge_tol.
    """
    if not segs:
        return []
    pts: list[np.ndarray] = []
    edges: list[tuple[int, int]] = []

    def find_or_add(p: np.ndarray) -> int:
        for i, q in enumerate(pts):
            if np.linalg.norm(p - q) < merge_tol:
                return i
        pts.append(p)
        return len(pts) - 1

    for s in segs:
        i = find_or_add(s[0])
        j = find_or_add(s[1])
        if i != j:
            edges.append((i, j))

    adj: dict[int, list[int]] = {}
    for i, j in edges:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)

    visited_edge: set[tuple[int, int]] = set()
    loops: list[np.ndarray] = []
    for start, nbrs in list(adj.items()):
        for first in nbrs:
            key = (min(start, first), max(start, first))
            if key in visited_edge:
                continue
            # Walk a loop.
            loop_idx = [start, first]
            visited_edge.add(key)
            prev, curr = start, first
            while curr != start:
                nxt = None
                for n in adj.get(curr, []):
                    if n == prev:
                        continue
                    k = (min(curr, n), max(curr, n))
                    if k in visited_edge:
                        continue
                    nxt = n
                    visited_edge.add(k)
                    break
                if nxt is None:
                    break
                loop_idx.append(nxt)
                prev, curr = curr, nxt
            if curr == start and len(loop_idx) >= 4:
                loops.append(np.stack([pts[k] for k in loop_idx[:-1]]))
    return loops


def _loop_xz(loop3d: np.ndarray, plane_normal: np.ndarray) -> np.ndarray:
    """Project a loop in 3D onto the plane and return its (N, 2) coords."""
    n = plane_normal / np.linalg.norm(plane_normal)
    # Build two orthogonal basis vectors in the plane.
    ref = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = ref - (ref @ n) * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    centred = loop3d - loop3d.mean(axis=0)
    return np.stack([centred @ u, centred @ v], axis=1)


def _pick_torso_loop(loops: list[np.ndarray]) -> np.ndarray | None:
    """Pick the loop containing the X≈0 midline — that's the torso, vs arms
    which sit at |X|>0.2 in A-pose. Falls back to the longest loop."""
    if not loops:
        return None

    def contains_midline(loop3d: np.ndarray) -> bool:
        xs = loop3d[:, 0]
        return xs.min() < 0.0 < xs.max()

    candidates = [lp for lp in loops if contains_midline(lp)]
    return max(candidates if candidates else loops, key=len)


def _polygon_perimeter(xy: np.ndarray) -> float:
    """Closed polygon perimeter (sum of edge lengths, wrap to start)."""
    diffs = np.diff(np.vstack([xy, xy[:1]]), axis=0)
    return float(np.sqrt((diffs ** 2).sum(axis=1)).sum())


def _convex_hull_perimeter(xy: np.ndarray) -> float:
    if len(xy) < 3:
        return 0.0
    hull = ConvexHull(xy)
    return _polygon_perimeter(xy[hull.vertices])


# ---------------------------------------------------------------------------
# Public recipes.
# ---------------------------------------------------------------------------


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
        output: convex_hull_perimeter
    """
    origin = _resolve_origin(params["plane"]["origin"], landmarks)
    if "offset" in params["plane"]:
        off = params["plane"]["offset"]
        axis = _resolve_axis(off["along"])
        origin = origin + axis * (float(off["distance_cm"]) / 100.0)
    normal = _resolve_axis(params["plane"]["normal"])
    segs = slice_mesh(verts, faces, origin, normal)
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
        segs = slice_mesh(verts, faces, origin, normal)
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


# Dispatch table — extended as more types are wired up.
RECIPE_DISPATCH: dict[str, Callable] = {
    "planar_slice": planar_slice,
    "planar_segment": planar_segment,
}
