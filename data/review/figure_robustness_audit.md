# Figure-robustness audit

Every constant in the measurement pipeline that depends on Yaiza's body
shape and could mis-fire on a different figure. Each entry rates the
risk and suggests a mitigation.

Risk levels:
- **H** High — fails or gives wrong number on common shape variation
- **M** Medium — likely OK across normal range, edge cases drift
- **L** Low — defensive default, unlikely to matter

## A. Lerp / midpoint of vertex pairs — Yaiza-tuned t

| Landmark | Op | t | Notes | Risk |
|---|---|---|---|---|
| `bust_apex_left` | lerp_vids 5646, 3230 | 0.5 | Picked so apex Y lands at Y=-0.048 between the two SMPL-X canonical apex vids. For larger / smaller / lower bust, true apex may not be midpoint. | **M** |
| `bust_apex_right` | lerp_vids 8340, 5993 | 0.5 | Mirror of left, same issue | **M** |

**Mitigation**: replace with a dynamic-search landmark — find max-Z
vertex in a Y window around the lerp point. Was attempted earlier (per
landmarks.py comment around L196: "tested with a bust_apex_left/right
-> max-Z search which made J01 worse"). Alternative: keep lerp but
make t shape-aware (function of breast volume from betas) — out of
scope.

## B. Mirror approximations

| Landmark | Vid | Notes | Risk |
|---|---|---|---|
| `bicep_max_left` | alias_vid 3259 | Mirror of right bicep_max_right vid 6022, dist 0.0046 m off in Yaiza fit | **L** |
| `calf_widest_left` | vid 3725 | Algorithmic max-girth-Y on Yaiza | **L** |
| `calf_widest_right` | vid 6486 | Mirror of left | **L** |

**Mitigation**: replace `alias_vid` with a `body_at_xy` dynamic search
inside the limb region (X around limb axis, Y around the original vid).
Cheap to add.

## C. Absolute metric offsets (don't scale with body)

| Landmark | Offset | Anatomical role | Risk |
|---|---|---|---|
| `neck_base_level` | +0.04 m above front_neck_point | Base of neck cylinder | **M** |
| `ankle_high_level` | +0.03 m above ankle bone | Narrowest leg point | **L** |
| `high_hip_level` | -0.11 m below waist_string | "4-5 inches below waist" rule | **M** |
| `low_hip_level` | -0.20 m below waist_string | Widest hip below waist | **H** |

**Risk explained**: a 150 cm figure and a 190 cm figure share the same
0.11/0.20 m offsets. The 190 cm figure's true high-hip is further from
the waist; low_hip especially. Comments in landmarks.py acknowledge the
placeholder:

> "low_hip_level: dpm 'widest girth below waist'. For scaffolding we
> use 20cm below the waist as a placeholder horizontal level; the
> proper implementation searches for the maximum-girth slice in a Y
> range."

**Mitigation**: replace `low_hip_level` with a dynamic-search landmark
that finds the maximum-girth horizontal slice in Y ∈ [waist - 0.10,
waist - 0.35]. Same pattern for high_hip if needed. The infrastructure
exists (PlanarGirth helpers).

## D. body_at_xy x_band / y_band (hardcoded metres, don't scale)

All `body_at_xy` dynamic searches use defaults `x_band=0.02` (2 cm),
`y_band=0.01` (1 cm) unless overridden:

| Landmark | x_band | y_band | Notes | Risk |
|---|---|---|---|---|
| `waist_front_at_apex_x_left` | 0.02 | 0.01 | | **L** |
| `bust_front_at_sn_x_left` | 0.02 | 0.01 | | **L** |
| `highbust_front_at_sn_x_left` | 0.02 | 0.01 | | **L** |
| `waist_front_at_sn_x_left` | 0.02 | 0.01 | | **L** |
| `h06_endpoint_left` | 0.025 | 0.012 | Already widened | **L** |
| `bust_front_cf` | 0.010 | 0.008 | TIGHT — must hit midline | **M** |
| `bust_apex_left_at_lowbust_y_body` | 0.025 | 0.012 | | **L** |

**Mitigation**: `_search_body_at_xy` already has a 2x widening fallback
(landmarks.py:633). Robust enough. `bust_front_cf` is the only
borderline case — for a figure with deep cleavage / narrow midline, the
1 cm band may miss. Already protected by 2x widen → 2 cm band.

## E. Hardcoded thresholds in primitives

| Site | Value | Role | Risk |
|---|---|---|---|
| `SurfacePlumb.x_band` default | 0.015 m | X slab for plane slice | **L** |
| `SurfacePlumb.y_band` default | 0.006 m | (currently unused) | n/a |
| `SurfacePlumb._path` band buffer | ±0.005 m | Y inclusion past start/end | **L** |
| `SmoothLoop._curve` outward normal offset | 0.006 m | Viz offset | **L** |
| `DiagonalSurfacePlumb` z_thresh | ±0.01 m | Opposite-side body filter | **L** |
| `DiagonalSurfacePlumb` t_mask buffer | ±0.02 | Outside-chord t allowance | **L** |
| `DiagonalSurfacePlumb` endpoint snap | 0.02 m | Skip-prepend distance | **L** |
| `DiagonalYardstick.y_band` default | 0.012 m | Mid touch point Y slab | **L** |
| `LimbGirth._slice_loop` fallback radius | 0.20 m | When no closed loop | **L** |
| `TapeLoop._half_hull` x_lim margin | +0.005 m | Beyond underarm endpoints | **L** |
| `drape_polyline_on_body` mid_dist threshold | 0.025 m | In-air chord detector | **L** |
| `drape_polyline_on_body` offset_m default | 0.008 m | Viz offset | **L** |

All defaults are wide enough for normal shape variation. The only
borderline case is `DiagonalSurfacePlumb` z_thresh ±0.01 — for very
thin figures the body can sit within 1 cm of the slice plane on both
sides, defeating the side filter. In practice DSP also uses the
loop-pick `_score` which prefers loops containing both endpoints.

## F. Underbust-crease detection

```
"underbust_crease_left": {
    "min_offset": 0.03,           # search 3-12 cm below apex
    "max_offset": 0.12,
    "drop_fraction": 0.5,         # fold = 50% Z drop
    "min_drop": 0.005,
    "chest_y_offset": 0.08,       # chest-wall Y reference 8 cm above apex
    "chest_y_band": 0.01,
    "chest_slab_dx": 0.03,
}
```

| Param | Risk |
|---|---|
| `min_offset` / `max_offset` (search range) | **M** — extreme bust drop > 12 cm not covered |
| `drop_fraction = 0.5` | **M** — comment says "tune up for larger busts" |
| `chest_y_offset = 0.08` | **L** — 8 cm above apex usually safe, but shorter torsos may have collarbone at that Y (chest ref then wrong) |

**Mitigation**: expose `drop_fraction` per-fit by making it a function
of bust depth (smaller fraction for small busts, larger for large
busts). Or use a steeper-gradient detector instead of a Z-drop
threshold.

## G. Bent-arm pose

`body_scanner.measure.bent_arm`:
- `DEFAULT_ELBOW_FLEX_DEG = 80°`
- `DEFAULT_ELBOW_AXIS = "0,-1,0"` (L_Elbow local frame)
- `DEFAULT_SHOULDER_FORWARD_DEG = 30°`

All in SMPL-X local joint frames → shape-independent. Universal across
figures. **L**

## H. Region masks (`regions.py`)

Derived from SMPL-X canonical skinning weights. Pose-invariant,
shape-invariant. Universal. **L**

## I. Vertex IDs from `references/smplx_landmark_review.json`

Verified per-anatomical-feature on the SMPL-X canonical mesh. SMPL-X
shape blendshapes deform these consistently across figures (the vid
labeled "front_neck_point" stays at the throat hollow regardless of
shape). **L** for the catalog as a whole.

The exceptions are the ones listed in sections A/B — landmarks
synthesised from multiple vids whose lerp/mirror was tuned on Yaiza.

## Priority fix list

If the next figure shows drift, fix in this order:

1. **`low_hip_level` → dynamic max-girth search** (section C). Most
   likely to be wrong on a different figure; the comment already flags
   it as a placeholder.
2. **`high_hip_level` → 4-5" rule scaled by figure height**, or also
   convert to max-curvature search (section C).
3. **`bust_apex_left/right` → max-Z search in a Y window** (section
   A). The lerp t=0.5 was chosen for one body.
4. **`underbust_crease drop_fraction` → bust-depth aware** (section
   F). 0.5 is a Yaiza-specific tune.
5. **Mirror approximations → body_at_xy in limb region** (section B).
   Cheap, low return — defer unless L13 / L04 misbehave.

Sections D, E, G, H, I are robust enough to leave alone.

## How to test on a new figure

1. Fit the new scan to SMPL-X (`body_scanner.fit.cli`).
2. Run `scripts/dump_recipe_table.py` against the new fit (point it
   at the new `<name>_seamly_catalog.json`) — get a coverage table.
3. Run the review viewer:
   `python -m body_scanner.measure.review_viewer <fit.npz> --port 8051`
   and step through the catalog visually.
4. Flag drifts in `data/review/<name>_notes.json` via the viewer's
   "Add note" button.
5. Diff the new figure's CSV against Yaiza's relative to anthropometric
   ratios — any code more than ~5% off the height-normalised expected
   value is suspect.
