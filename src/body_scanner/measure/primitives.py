"""Recipe primitives for the Seamly catalog extractor.

Per references/seamly/extraction_audit.md section "Implementation sketch":
the Phase 6 generic extractor maps Seamly catalog code -> recipe primitive,
where each primitive is one of:

    Height(landmark)            -> vertical distance floor -> landmark
    PlanarGirth(plane)          -> convex-hull perimeter at horizontal plane
    PlanarArc(plane, a, b, side)-> chord-clipped arc on the plane slice
    LateralChord(plane)         -> widest X chord at the plane
    LandmarkChord(a, b)         -> straight-line 3D distance
    Geodesic(waypoints)         -> surface path through ordered points
    GeodesicLoop(waypoints)     -> closed surface loop through waypoints (G03)
    Formula(others, expr)       -> arithmetic over other Seamly codes

Recipes operate on (verts, faces, LandmarkSet). Output is centimetres.

The G03/G11 geodesic-vs-planar warning from extraction_audit.md is honoured
by routing those codes through Geodesic/GeodesicLoop in seamly_catalog.py,
not PlanarGirth/PlanarArc.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import potpourri3d as pp3d

from .landmarks import LandmarkSet
from .recipes import (  # reuse the slicing utilities already built
    _build_loops,
    _convex_hull_perimeter,
    _loop_xz,
    _pick_torso_loop,
    _polygon_perimeter,
    slice_mesh,
)


# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------


def _y_axis() -> np.ndarray:
    return np.array([0.0, 1.0, 0.0])


def _floor_y(verts: np.ndarray) -> float:
    """Floor is the minimum Y of the fitted mesh."""
    return float(verts[:, 1].min())


def _nearest_vertex(verts: np.ndarray, p: np.ndarray) -> int:
    return int(np.argmin(np.linalg.norm(verts - p, axis=1)))


# ---------------------------------------------------------------------------
# Recipe protocol — each subclass implements compute(verts, faces, landmarks).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Height:
    """Vertical distance from floor (min Y) to landmark, in cm."""
    landmark: str

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        p = landmarks[self.landmark]
        return (p[1] - _floor_y(verts)) * 100.0


@dataclass(frozen=True)
class PlanarGirth:
    """Convex-hull perimeter of the horizontal slice at the landmark's Y."""
    landmark: str

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        origin = landmarks[self.landmark]
        segs = slice_mesh(verts, faces, origin, _y_axis())
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops)
        if loop is None:
            return float("nan")
        xy = _loop_xz(loop, _y_axis())
        return _convex_hull_perimeter(xy) * 100.0


@dataclass(frozen=True)
class PlanarArc:
    """Arc on a horizontal slice, clipped between two landmarks. side='front'
    picks the higher-Z arc; side='back' the lower-Z arc."""
    landmark_plane: str
    clip_start: str
    clip_end: str
    side: str  # "front" | "back"

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        origin = landmarks[self.landmark_plane]
        segs = slice_mesh(verts, faces, origin, _y_axis())
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops)
        if loop is None:
            return float("nan")
        start = landmarks[self.clip_start]
        end = landmarks[self.clip_end]
        i0 = int(np.argmin(np.linalg.norm(loop - start, axis=1)))
        i1 = int(np.argmin(np.linalg.norm(loop - end, axis=1)))
        if i0 == i1:
            return float("nan")
        n = len(loop)
        a_idx = (list(range(i0, i1 + 1)) if i0 < i1
                 else list(range(i0, n)) + list(range(0, i1 + 1)))
        b_idx = (list(range(i1, i0 + 1)) if i1 < i0
                 else list(range(i1, n)) + list(range(0, i0 + 1)))
        arc_a, arc_b = loop[a_idx], loop[b_idx]
        is_front = self.side == "front"
        if (arc_a[:, 2].mean() > arc_b[:, 2].mean()) == is_front:
            arc = arc_a
        else:
            arc = arc_b
        diffs = np.diff(arc, axis=0)
        return float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) * 100.0


@dataclass(frozen=True)
class LateralChord:
    """Maximum X-extent of the horizontal slice at the landmark plane."""
    landmark: str

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        origin = landmarks[self.landmark]
        segs = slice_mesh(verts, faces, origin, _y_axis())
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops)
        if loop is None:
            return float("nan")
        return float(loop[:, 0].max() - loop[:, 0].min()) * 100.0


@dataclass(frozen=True)
class LandmarkChord:
    """Straight-line 3D distance between two landmarks."""
    a: str
    b: str

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        pa = landmarks[self.a]
        pb = landmarks[self.b]
        return float(np.linalg.norm(pb - pa)) * 100.0


# Geodesic solvers are expensive to construct (build edge structure); cache
# per mesh-id.
_GEODESIC_CACHE: dict[int, pp3d.EdgeFlipGeodesicSolver] = {}


def _get_solver(verts: np.ndarray, faces: np.ndarray) -> pp3d.EdgeFlipGeodesicSolver:
    key = id(verts)
    if key not in _GEODESIC_CACHE:
        _GEODESIC_CACHE[key] = pp3d.EdgeFlipGeodesicSolver(
            verts.astype(np.float64), faces.astype(np.int64)
        )
    return _GEODESIC_CACHE[key]


@dataclass(frozen=True)
class Geodesic:
    """Open geodesic path through ordered landmark waypoints (>=2)."""
    waypoints: tuple[str, ...]

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        solver = _get_solver(verts, faces)
        v_ids = [_nearest_vertex(verts, landmarks[w]) for w in self.waypoints]
        try:
            path = solver.find_geodesic_path_poly(v_ids)
        except Exception:
            return float("nan")
        if len(path) < 2:
            return float("nan")
        diffs = np.diff(path, axis=0)
        return float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) * 100.0


@dataclass(frozen=True)
class GeodesicLoop:
    """Closed geodesic loop through ordered landmark waypoints (>=3)."""
    waypoints: tuple[str, ...]

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        solver = _get_solver(verts, faces)
        v_ids = [_nearest_vertex(verts, landmarks[w]) for w in self.waypoints]
        try:
            path = solver.find_geodesic_loop(v_ids)
        except Exception:
            return float("nan")
        if len(path) < 3:
            return float("nan")
        diffs = np.diff(np.vstack([path, path[:1]]), axis=0)
        return float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) * 100.0


@dataclass(frozen=True)
class Formula:
    """Arithmetic over already-computed Seamly codes.
    expr is a Python expression; locals = {seamly_code: value_cm}."""
    expr: str

    def compute_from(self, values: dict[str, float]) -> float:
        return float(eval(self.expr, {"__builtins__": {}}, dict(values)))


# Convenience union for dispatch / typing.
PrimitiveRecipe = (
    Height | PlanarGirth | PlanarArc | LateralChord
    | LandmarkChord | Geodesic | GeodesicLoop
)
