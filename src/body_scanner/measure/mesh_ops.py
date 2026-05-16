"""Mesh-slicing primitives shared by `recipes.py` and `primitives.py`.

Lives in its own module so neither file imports the other — the old
`recipes <-> primitives` lazy-import dance is gone.

Contents:
  - `slice_mesh(verts, faces, plane_origin, plane_normal, ...)`:
    triangle-plane intersection → unordered line segments.
  - `_build_loops(segs, merge_tol=1e-6)`: stitch the segments into
    closed loops.
  - `_pick_torso_loop` / `_pick_largest_loop` / `_pick_loop_near_point`:
    loop selection heuristics for multi-loop slices.
  - `_loop_xz(loop3d, plane_normal)`: project a 3D loop onto a 2D
    in-plane basis.
  - `_polygon_perimeter(xy)` / `_convex_hull_perimeter(xy)`: length
    helpers in 2D.

These names are kept with the underscore prefix for back-compat with
existing call sites that imported them from `recipes.py`.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull


def slice_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    plane_origin: np.ndarray,
    plane_normal: np.ndarray,
    vertex_mask: np.ndarray | None = None,
    strict_mask: bool = False,
) -> list[np.ndarray]:
    """Intersect a mesh with a plane. Returns a list of polylines, each an
    (N, 3) array of consecutive vertices on the slice. Polylines are
    open-form line segments per triangle, not joined into closed loops yet.

    Implementation: for each triangle, compute signed distance of vertices
    to the plane; if they don't all share sign, find the two crossing
    edges and interpolate the crossing point.

    vertex_mask: optional bool array over verts; triangles are kept only if
    all 3 vertices are in the mask. Used to restrict slicing to one body
    region (torso / left_arm / etc.).
    """
    n = plane_normal / np.linalg.norm(plane_normal)
    d = (verts - plane_origin) @ n  # signed distance per vertex
    segs: list[np.ndarray] = []
    for tri in faces:
        if vertex_mask is not None:
            if strict_mask:
                # All 3 verts must be in mask. Cuts loops at region boundary
                # but cleanly isolates the region's slice.
                if not (vertex_mask[tri[0]] and vertex_mask[tri[1]]
                        and vertex_mask[tri[2]]):
                    continue
            else:
                # Any-vertex rule: keep boundary triangles so the slice loop
                # closes across region junctions.
                if not (vertex_mask[tri[0]] or vertex_mask[tri[1]]
                        or vertex_mask[tri[2]]):
                    continue
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


def _build_loops(
    segs: list[np.ndarray], merge_tol: float = 1e-6,
) -> list[np.ndarray]:
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
    ref = (np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9
           else np.array([0.0, 1.0, 0.0]))
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


def _pick_largest_loop(loops: list[np.ndarray]) -> np.ndarray | None:
    """Pick the longest loop. Used when a region mask has already isolated
    the body part — typically only one loop survives."""
    return max(loops, key=len) if loops else None


def _pick_loop_near_point(
    loops: list[np.ndarray], target: np.ndarray,
) -> np.ndarray | None:
    """Pick the loop whose centroid is closest to a 3D target — useful for
    bilateral measurements where left/right side both pass the region
    filter (e.g. mid-knee plane cuts both knees)."""
    if not loops:
        return None
    return min(loops,
               key=lambda lp: np.linalg.norm(lp.mean(axis=0) - target))


def _polygon_perimeter(xy: np.ndarray) -> float:
    """Closed polygon perimeter (sum of edge lengths, wrap to start)."""
    diffs = np.diff(np.vstack([xy, xy[:1]]), axis=0)
    return float(np.sqrt((diffs ** 2).sum(axis=1)).sum())


def _convex_hull_perimeter(xy: np.ndarray) -> float:
    if len(xy) < 3:
        return 0.0
    hull = ConvexHull(xy)
    return _polygon_perimeter(xy[hull.vertices])
