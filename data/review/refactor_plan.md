# Measure-module refactor plan

Goal: improve structure + docs without changing any measurement value.
Gating: snapshot regression test passes after every step.

## Step 1 — Regression test (gate)
- `tests/test_yaiza_snapshot.py`: extract on `yaiza_smplx_fit.npz`, compare CSV byte-equal to `data/results/yaiza_measurements.baseline.csv`.
- Smoke-import `body_scanner.measure.bent_arm`, `cli`, `primitives`.
- Run via `pytest tests/`.

## Step 2 — Docs
- `src/body_scanner/measure/README.md`: pipeline diagram + module map + add-a-measurement HOWTO.
- `docs/recipes.md`: per-primitive table (mental model, inputs, failure modes).
- `docs/catalog_coverage.md`: auto-generated table of 245 codes.
- `scripts/dump_recipe_table.py`: introspect `RECIPES` + extract on Yaiza → write `docs/catalog_coverage.md`.

## Step 3 — Split `primitives.py` (1400 → ~5 × 250 LOC)
- New package `primitives/`:
  - `chord.py`: Height, LandmarkChord, VerticalDrop, PolylineChord
  - `girth.py`: PlanarGirth, PlanarArc, LateralChord, LimbGirth
  - `geodesic.py`: Geodesic, GeodesicLoop, _get_solver, _GEODESIC_CACHE
  - `surface.py`: SurfacePlumb, SurfacePlumbThenDrop, DiagonalSurfacePlumb, DiagonalYardstick, GeodesicThenDrop
  - `loop.py`: HybridLoop, TapeLoop, SmoothLoop
  - `viz.py`: recipe_polyline, drape_polyline_on_body, should_drape, DRAPE_ON_BODY_RECIPES
  - `__init__.py`: re-export everything (back-compat for callers using `from .primitives import X`)
- Move shared helpers (`_y_axis`, `_floor_y`, `_nearest_vertex`, `_densify_last`) to `primitives/_shared.py`.

## Step 4 — `mesh_ops.py` (kill circular import)
- Extract `_build_loops`, `_pick_torso_loop`, `_pick_loop_near_point`, `_pick_largest_loop`, `_loop_xz`, `_convex_hull_perimeter`, `_polygon_perimeter`, `slice_mesh` from `recipes.py` → `mesh_ops.py`.
- `recipes.py` and `primitives/*` both import from `mesh_ops`.
- Remove the `from .primitives import Geodesic/GeodesicLoop` lazy imports inside `recipes.geodesic_path/loop` once cycle is gone.

## Step 5 — Tolerance constants
- New `primitives/_constants.py`:
  - `EPS_AXIS_NORM = 1e-9`        # unit-axis normalization guard
  - `EPS_VECTOR_NORM = 1e-6`      # zero-length vector guard
  - `EPS_Y_PLANE_HIT = 1e-4`      # already-on-plane skip
  - `EPS_BIN_EDGE = 1e-9`         # t-binning right-edge tolerance
  - `EPS_DEGEN = 1e-12`           # division degenerate
- Replace literals in primitives. No numeric change.

## Step 6 — `LandmarkSet._dynamic` dispatch
- Replace 200-line if/elif with `DYNAMIC_SEARCHES: dict[str, Callable]` registry.
- Same for compound ops in `LandmarkSet.__getitem__`.

## Step 7 — `recipe_polyline` dispatch
- Add `def polyline(self, verts, faces, lm) -> np.ndarray | None` on each recipe dataclass.
- `recipe_polyline` collapses to `recipe.polyline(...)`.

## Step 8 — Narrow exceptions
- Per `except Exception` site: identify real exceptions raised (`RuntimeError`, `IndexError`, `ValueError`, `scipy.spatial.QhullError`).
- Narrow to those; let unknown ones surface.
- Snapshot test catches NaN drift.

## Step 9 — Safe small fixes
- `fit.py`: `10475` → `body_model.v_template.shape[0]`.
- `np.load` → context managers in `cli.py`, `extract_bent_arm.py`.
- VPoser ckpt: SHA256 verification before `torch.load(weights_only=False)`.

## Out of scope (this pass)
- `Formula.eval()` → `asteval`. Needs new dep.
- LBFGS double-step semantics. Needs fit-convergence test.
- Two parallel extractors (`extractor.py` vs `seamly_extractor.py`) consolidation. Needs user decision.
