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
    _pick_largest_loop,
    _pick_loop_near_point,
    _pick_torso_loop,
    _polygon_perimeter,
    slice_mesh,
)
from .regions import region_vertex_mask


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
    """Convex-hull perimeter of the horizontal slice at the landmark's Y.

    regions: tuple of region names from regions.REGIONS. If set, only
    triangles entirely inside those regions are sliced. Default ("torso",)
    keeps arms/legs out of torso-circumference slices."""
    landmark: str
    regions: tuple[str, ...] = ("torso",)

    def _slice_loop(self, verts, faces, landmarks):
        origin = landmarks[self.landmark]
        mask = region_vertex_mask(self.regions) if self.regions else None
        segs = slice_mesh(verts, faces, origin, _y_axis(), vertex_mask=mask)
        loops = _build_loops(segs)
        if not loops:
            return None
        # For non-torso regions (e.g. left_arm), the mask isolates the body
        # part; if both knees survive (e.g. mid_knee slice across both legs),
        # pick the loop closest to the landmark's actual 3D position.
        if "torso" in self.regions:
            return _pick_torso_loop(loops)
        return _pick_loop_near_point(loops, origin)

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        loop = self._slice_loop(verts, faces, landmarks)
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
    regions: tuple[str, ...] = ("torso",)

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        origin = landmarks[self.landmark_plane]
        mask = region_vertex_mask(self.regions) if self.regions else None
        segs = slice_mesh(verts, faces, origin, _y_axis(), vertex_mask=mask)
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops) if "torso" in self.regions \
            else _pick_largest_loop(loops)
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
    regions: tuple[str, ...] = ("torso",)

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        origin = landmarks[self.landmark]
        mask = region_vertex_mask(self.regions) if self.regions else None
        segs = slice_mesh(verts, faces, origin, _y_axis(), vertex_mask=mask)
        loops = _build_loops(segs)
        loop = _pick_torso_loop(loops) if "torso" in self.regions \
            else _pick_largest_loop(loops)
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
    """Closed geodesic loop through ordered landmark waypoints (>=3).

    We compute each pair (w_i, w_{i+1}) as an open geodesic path and
    concatenate. This guarantees the loop *visits* every waypoint, unlike
    potpourri3d's find_geodesic_loop which iteratively shortens past
    them — fine for finding the canonical shortest loop, wrong when the
    waypoints are constraints (e.g. forcing the highbust path to pass
    through a midline-back point higher than the lateral armfolds)."""
    waypoints: tuple[str, ...]

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        solver = _get_solver(verts, faces)
        v_ids = [_nearest_vertex(verts, landmarks[w]) for w in self.waypoints]
        v_ids.append(v_ids[0])  # close the loop
        total = 0.0
        for a, b in zip(v_ids, v_ids[1:]):
            try:
                path = solver.find_geodesic_path(a, b)
            except Exception:
                return float("nan")
            if len(path) < 2:
                continue
            diffs = np.diff(path, axis=0)
            total += float(np.sqrt((diffs ** 2).sum(axis=1)).sum())
        return total * 100.0


@dataclass(frozen=True)
class Formula:
    """Arithmetic over already-computed Seamly codes.
    expr is a Python expression; locals = {seamly_code: value_cm}."""
    expr: str

    def compute_from(self, values: dict[str, float]) -> float:
        return float(eval(self.expr, {"__builtins__": {}}, dict(values)))


@dataclass(frozen=True)
class HybridLoop:
    """Closed loop combining a PLANAR arc on the back with a GEODESIC arc
    on the front (or vice versa). Used when one half of a girth tape
    should stay parallel to the floor (e.g. highbust back at underarm Y)
    while the other half follows the body surface over a bulge (e.g.
    highbust front over the bust).

    Inputs:
      plane_landmark: name of a landmark whose Y defines the planar
        slice plane (horizontal).
      planar_side: "back" or "front" — which side of the slice arc to use.
      arc_endpoints: (left_name, right_name) — landmarks where the planar
        arc starts/ends. The geodesic arc closes the loop from
        right_endpoint -> geodesic_waypoints -> left_endpoint.
      geodesic_waypoints: ordered landmark names visited by the geodesic
        portion of the loop, between the two arc endpoints.
      regions: region mask for the planar slice (default ("torso",)).
    """
    plane_landmark: str
    planar_side: str
    arc_endpoints: tuple[str, str]
    geodesic_waypoints: tuple[str, ...] = ()
    regions: tuple[str, ...] = ("torso",)

    def _planar_arc(self, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
        from .recipes import slice_mesh
        origin = landmarks[self.plane_landmark]
        # Strict torso mask so the slice doesn't include the arms. The
        # segments form OPEN polylines (one for the back, one for the
        # front, each cut at the arm-torso boundary near the underarms).
        mask = region_vertex_mask(self.regions) if self.regions else None
        segs = slice_mesh(verts, faces, origin, _y_axis(),
                          vertex_mask=mask, strict_mask=True)
        if not segs:
            return None
        # Collect all crossing points, then pick the BACK or FRONT subset
        # by Z and order along X.
        pts = np.vstack(segs)
        is_back = self.planar_side == "back"
        # Back: Z < 0 (in SMPL-X frame +Z = anterior). Front: Z > 0.
        mask_z = pts[:, 2] < 0 if is_back else pts[:, 2] > 0
        side_pts = pts[mask_z]
        if len(side_pts) < 4:
            return None
        a = landmarks[self.arc_endpoints[0]]
        b = landmarks[self.arc_endpoints[1]]
        # Sort by X going from a's X to b's X.
        order = np.argsort(side_pts[:, 0])
        sorted_pts = side_pts[order]
        if a[0] > b[0]:
            sorted_pts = sorted_pts[::-1]
        # Prepend/append the exact endpoints for a clean start/end.
        return np.vstack([a[None], sorted_pts, b[None]])

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        back_arc = self._planar_arc(verts, faces, landmarks)
        if back_arc is None:
            return float("nan")
        diffs = np.diff(back_arc, axis=0)
        back_len = float(np.sqrt((diffs ** 2).sum(axis=1)).sum())
        # Geodesic front: arc_endpoints[1] -> waypoints -> arc_endpoints[0]
        solver = _get_solver(verts, faces)
        v_ids = [_nearest_vertex(verts, landmarks[self.arc_endpoints[1]])]
        for w in self.geodesic_waypoints:
            v_ids.append(_nearest_vertex(verts, landmarks[w]))
        v_ids.append(_nearest_vertex(verts, landmarks[self.arc_endpoints[0]]))
        front_len = 0.0
        for u, v in zip(v_ids, v_ids[1:]):
            try:
                p = solver.find_geodesic_path(u, v)
            except Exception:
                return float("nan")
            if len(p) >= 2:
                d = np.diff(p, axis=0)
                front_len += float(np.sqrt((d ** 2).sum(axis=1)).sum())
        return (back_len + front_len) * 100.0


@dataclass(frozen=True)
class TapeLoop:
    """Closed loop that simulates a tape measure pulled taut across the
    chest at highbust level. Two halves:

    - BACK: planar slice at plane_y, convex-hulled from one side
      endpoint around the CB to the other. Flat at underarm Y, body-
      contour through the back, no scapular-gutter dip.
    - FRONT: by default the planar slice at plane_y on the front side,
      convex-hulled R -> L to bridge the CF cleavage. If
      `front_waypoints` is given, the front instead follows a GEODESIC
      path through those waypoints between the side endpoints — used to
      reuse an existing curve like G11 (armfold-to-armfold geodesic
      over the bust) as the front of the highbust loop.

    Args:
      plane_landmark: name of a landmark whose Y defines the underarm-
        height slice plane (e.g. "underarm_left").
      side_endpoints: (left, right) landmark names that anchor both arcs.
        For G03 these are ("underarm_left", "underarm_right").
      front_waypoints: optional ordered landmark names visited by the
        front geodesic between side_endpoints[0] -> ... ->
        side_endpoints[1]. If None, the front is the planar-slice half-
        hull.
      regions: region mask for the planar back slice (default torso).
    """
    plane_landmark: str
    side_endpoints: tuple[str, str]
    front_waypoints: tuple[str, ...] | None = None
    regions: tuple[str, ...] = ("torso",)

    def _planar_loop(self, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
        """Closed planar body loop at plane_y. With no region mask the
        slice produces a closed manifold loop that may also envelop
        nearby limbs (at A-pose, the arm region is topologically fused
        to the torso at the underarm) — that's fine because the consumer
        (_back_arc / _front_arch) restricts to the XZ convex hull, which
        drops any arm-side excursions."""
        from .recipes import slice_mesh, _build_loops, _pick_torso_loop
        plane_y = landmarks[self.plane_landmark][1]
        origin = np.array([0.0, plane_y, 0.0])
        segs = slice_mesh(verts, faces, origin, _y_axis())
        if not segs:
            return None
        loops = _build_loops(segs)
        return _pick_torso_loop(loops)

    def _half_hull(self, verts, faces, landmarks: LandmarkSet,
                    side: str) -> np.ndarray | None:
        """Half of the XZ-convex hull of the planar loop at plane_y.
        side="back" -> Z<midZ half, traversed L -> R through CB.
        side="front" -> Z>midZ half, traversed R -> L through CF.
        Convex-hulling drops CF/CB concavities the way a taut tape
        would. Loop points beyond the lateral underarm endpoints are
        dropped first so the planar slice cannot wrap into a fused
        arm cross-section at A-pose.
        """
        from scipy.spatial import ConvexHull
        loop = self._planar_loop(verts, faces, landmarks)
        if loop is None or len(loop) < 6:
            return None
        L = landmarks[self.side_endpoints[0]]
        R = landmarks[self.side_endpoints[1]]
        midZ = (L[2] + R[2]) / 2.0
        x_lim = max(abs(L[0]), abs(R[0])) + 0.005
        keep = np.abs(loop[:, 0]) <= x_lim
        loop = loop[keep]
        if len(loop) < 6:
            return None
        try:
            hidx = ConvexHull(loop[:, [0, 2]]).vertices  # CCW
        except Exception:
            return None
        hull = loop[hidx]
        d_L = np.linalg.norm(hull[:, [0, 2]] - L[[0, 2]], axis=1)
        d_R = np.linalg.norm(hull[:, [0, 2]] - R[[0, 2]], axis=1)
        pos_L = int(np.argmin(d_L))
        pos_R = int(np.argmin(d_R))
        if pos_L == pos_R:
            return None
        h = len(hull)
        # Two candidate arcs between L and R.
        if pos_L < pos_R:
            arc1 = list(range(pos_L, pos_R + 1))
            arc2 = list(range(pos_R, h)) + list(range(0, pos_L + 1))
        else:
            arc1 = list(range(pos_R, pos_L + 1))
            arc2 = list(range(pos_L, h)) + list(range(0, pos_R + 1))
        a1 = hull[arc1]; a2 = hull[arc2]
        want_back = side == "back"
        if want_back:
            chosen = a1 if a1[:, 2].mean() < a2[:, 2].mean() else a2
        else:
            chosen = a1 if a1[:, 2].mean() > a2[:, 2].mean() else a2
        # Orient endpoints. Back: L -> R; Front: R -> L.
        first, last = (L, R) if want_back else (R, L)
        if np.linalg.norm(chosen[0, [0, 2]] - first[[0, 2]]) > \
           np.linalg.norm(chosen[-1, [0, 2]] - first[[0, 2]]):
            chosen = chosen[::-1]
        return np.vstack([first[None], chosen[1:-1], last[None]])

    def _back_arc(self, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
        return self._half_hull(verts, faces, landmarks, "back")

    def _front_arch(self, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
        if self.front_waypoints is None:
            return self._half_hull(verts, faces, landmarks, "front")
        # Front = geodesic L -> waypoints -> R on the body surface.
        L = landmarks[self.side_endpoints[0]]
        R = landmarks[self.side_endpoints[1]]
        solver = _get_solver(verts, faces)
        names = (self.side_endpoints[0],
                 *self.front_waypoints,
                 self.side_endpoints[1])
        v_ids = [_nearest_vertex(verts, landmarks[n]) for n in names]
        segs = []
        for a, b in zip(v_ids, v_ids[1:]):
            try:
                p = np.asarray(solver.find_geodesic_path(a, b))
            except Exception:
                return None
            if len(p) >= 2:
                segs.append(p)
        if not segs:
            return None
        out = [segs[0]]
        for s in segs[1:]:
            out.append(s[1:])
        front = np.vstack(out)
        # Reorient: this _half_hull-style consumers expect R -> L.
        # Geodesic ran L -> R, so flip.
        front = front[::-1]
        return np.vstack([R[None], front[1:-1], L[None]])

    def compute(self, verts, faces, landmarks: LandmarkSet) -> float:
        back = self._back_arc(verts, faces, landmarks)
        front = self._front_arch(verts, faces, landmarks)
        if back is None or front is None:
            return float("nan")
        back_len = float(np.sqrt(np.diff(back, axis=0).__pow__(2).sum(-1)).sum())
        front_len = float(np.sqrt(np.diff(front, axis=0).__pow__(2).sum(-1)).sum())
        return (back_len + front_len) * 100.0

    def polyline(self, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
        back = self._back_arc(verts, faces, landmarks)
        front = self._front_arch(verts, faces, landmarks)
        if back is None or front is None:
            return None
        # back ends at R, front starts at R -> skip front[0] duplicate.
        return np.vstack([back, front[1:]])


# Convenience union for dispatch / typing.
PrimitiveRecipe = (
    Height | PlanarGirth | PlanarArc | LateralChord
    | LandmarkChord | Geodesic | GeodesicLoop | HybridLoop | TapeLoop
)


# ---------------------------------------------------------------------------
# Polyline extraction — for visualisation. Returns an (N, 3) numpy array of
# 3D points whose total length equals the recipe's measurement value.
# ---------------------------------------------------------------------------


def recipe_polyline(recipe, verts, faces, landmarks: LandmarkSet) -> np.ndarray | None:
    """Return the 3D polyline that visualises a recipe on the fitted mesh.

    None if the recipe is value-only (Formula) or cannot be visualised.
    """
    try:
        if isinstance(recipe, Height):
            p = landmarks[recipe.landmark]
            return np.array([[p[0], _floor_y(verts), p[2]], p])

        if isinstance(recipe, PlanarGirth):
            loop = recipe._slice_loop(verts, faces, landmarks)
            if loop is None:
                return None
            # Show the convex hull (= taut tape around the body) rather than
            # the body-surface contour. Matches the convex_hull_perimeter
            # value the recipe computes.
            from scipy.spatial import ConvexHull
            xy = _loop_xz(loop, _y_axis())
            if len(xy) < 3:
                return np.vstack([loop, loop[:1]])
            try:
                hull_idx = ConvexHull(xy).vertices
            except Exception:
                return np.vstack([loop, loop[:1]])
            hull_loop = loop[hull_idx]
            return np.vstack([hull_loop, hull_loop[:1]])

        if isinstance(recipe, PlanarArc):
            origin = landmarks[recipe.landmark_plane]
            mask = (region_vertex_mask(recipe.regions)
                    if recipe.regions else None)
            segs = slice_mesh(verts, faces, origin, _y_axis(),
                              vertex_mask=mask)
            loops = _build_loops(segs)
            loop = (_pick_torso_loop(loops) if "torso" in recipe.regions
                    else _pick_largest_loop(loops))
            if loop is None:
                return None
            start = landmarks[recipe.clip_start]
            end = landmarks[recipe.clip_end]
            i0 = int(np.argmin(np.linalg.norm(loop - start, axis=1)))
            i1 = int(np.argmin(np.linalg.norm(loop - end, axis=1)))
            if i0 == i1:
                return None
            n = len(loop)
            a_idx = (list(range(i0, i1 + 1)) if i0 < i1
                     else list(range(i0, n)) + list(range(0, i1 + 1)))
            b_idx = (list(range(i1, i0 + 1)) if i1 < i0
                     else list(range(i1, n)) + list(range(0, i0 + 1)))
            arc_a, arc_b = loop[a_idx], loop[b_idx]
            is_front = recipe.side == "front"
            if (arc_a[:, 2].mean() > arc_b[:, 2].mean()) == is_front:
                return arc_a
            return arc_b

        if isinstance(recipe, LateralChord):
            origin = landmarks[recipe.landmark]
            mask = (region_vertex_mask(recipe.regions)
                    if recipe.regions else None)
            segs = slice_mesh(verts, faces, origin, _y_axis(),
                              vertex_mask=mask)
            loops = _build_loops(segs)
            loop = (_pick_torso_loop(loops) if "torso" in recipe.regions
                    else _pick_largest_loop(loops))
            if loop is None:
                return None
            i_min = int(np.argmin(loop[:, 0]))
            i_max = int(np.argmax(loop[:, 0]))
            return np.array([loop[i_min], loop[i_max]])

        if isinstance(recipe, LandmarkChord):
            return np.array([landmarks[recipe.a], landmarks[recipe.b]])

        if isinstance(recipe, Geodesic):
            solver = _get_solver(verts, faces)
            v_ids = [_nearest_vertex(verts, landmarks[w]) for w in recipe.waypoints]
            return np.asarray(solver.find_geodesic_path_poly(v_ids))

        if isinstance(recipe, GeodesicLoop):
            solver = _get_solver(verts, faces)
            v_ids = [_nearest_vertex(verts, landmarks[w]) for w in recipe.waypoints]
            v_ids.append(v_ids[0])  # close the loop
            segments = []
            for a, b in zip(v_ids, v_ids[1:]):
                p = np.asarray(solver.find_geodesic_path(a, b))
                if len(p) >= 2:
                    segments.append(p)
            if not segments:
                return None
            full = [segments[0]]
            for s in segments[1:]:
                full.append(s[1:])
            return np.vstack(full)

        if isinstance(recipe, TapeLoop):
            return recipe.polyline(verts, faces, landmarks)

        if isinstance(recipe, HybridLoop):
            back_arc = recipe._planar_arc(verts, faces, landmarks)
            if back_arc is None:
                return None
            solver = _get_solver(verts, faces)
            v_ids = [_nearest_vertex(verts, landmarks[recipe.arc_endpoints[1]])]
            for w in recipe.geodesic_waypoints:
                v_ids.append(_nearest_vertex(verts, landmarks[w]))
            v_ids.append(_nearest_vertex(verts, landmarks[recipe.arc_endpoints[0]]))
            front_segs = []
            for u, v in zip(v_ids, v_ids[1:]):
                p = np.asarray(solver.find_geodesic_path(u, v))
                if len(p) >= 2:
                    front_segs.append(p)
            front = [front_segs[0]] if front_segs else []
            for s in front_segs[1:]:
                front.append(s[1:])
            front_poly = np.vstack(front) if front else np.empty((0, 3))
            # Close the loop: back_arc ends at arc_endpoints[1], front_poly
            # starts there; back_arc starts at arc_endpoints[0], front_poly
            # ends there. Concatenate skipping shared endpoint.
            if len(front_poly) > 0:
                return np.vstack([back_arc, front_poly[1:]])
            return back_arc
    except Exception:
        return None
    return None
