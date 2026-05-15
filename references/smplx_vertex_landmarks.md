# SMPL-X Vertex Landmarks for Body Measurement

**Status:** Phase 5 planning artifact. Empty — to be filled as landmarks
are picked. **Per [GUARDRAILS.md §3](../GUARDRAILS.md), every vertex ID
must be visually verified in Blender (with the SMPL-X addon) and
committed alongside a screenshot before being treated as authoritative.**

Authoritative columns:

- `proposed_vertex_id` — first-pass pick from `scripts/pick_smplx_landmarks.py`
  (Open3D Shift+click). Not authoritative until verified.
- `verified_vertex_id` — value committed after the Blender check.
- `screenshot` — relative path to the Blender screenshot showing the
  vertex selected on the T-pose mesh. Stored under
  `references/smplx_landmark_screenshots/`.

A row is **authoritative** only when `verified_vertex_id` is populated
and `screenshot` exists.

## Workflow

1. Run `python scripts/pick_smplx_landmarks.py`. The Open3D window opens
   on the SMPL-X female T-pose with body skeleton joints rendered as
   colored spheres for orientation (torso=blue, left=red, right=green).
2. Shift+click each landmark vertex. Pick in any order; the script
   prints `vertex_id (x, y, z)` for each pick after the window closes.
3. Paste the proposed IDs into the `proposed_vertex_id` column below.
4. Open the same T-pose mesh in Blender (with the SMPL-X addon
   installed), jump to each proposed vertex, screenshot it.
5. If the proposed vertex sits where the landmark belongs anatomically,
   copy the ID into `verified_vertex_id` and save the screenshot to
   `references/smplx_landmark_screenshots/<landmark_name>.png`.
6. If not, find a better vertex in Blender, commit that ID, screenshot.

## Model conventions

- Model: `data/body_models/smplx/SMPLX_FEMALE.npz` (SMPL-X v1.1 female).
- Pose: T-pose (zero betas, zero pose).
- 10,475 mesh vertices, 20,908 triangular faces.
- Coordinate system: Y-up (verify in your Blender setup; SMPL-X default
  in the Python package is Y-up after the standard load).
- Side conventions: `_left` and `_right` are the **model's** left and
  right (anatomical left/right, i.e. the body's own left is on the
  viewer's right when looking at the front of the mesh).

## Landmark inventory

### Midline torso (6)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `top_of_head` | Highest point of the cranium along Y. | `head` (15) | — | 9011 | — |
| `front_neck_point` | Mid centre-front at the neckline base. Sits roughly at the suprasternal-notch height but on the front of the neck rather than at the bone. dpm's "hollow of the neck" / "centre front neck". | `neck` (12) anterior | — | 5618 | — |
| `front_collar_bone` | Suprasternal notch (jugular notch) — the dip between the clavicles. | `neck` (12) anterior, slightly below `front_neck_point` | — | 5621 | — |
| `c7` | 7th cervical vertebra prominence at centre back. "Neck bone at centre back" (Aldrich). Alias: `center_back_neck`. | `neck` (12) posterior | — | 5920 | — |
| `waist_cf` | Centre-front at the waist plane (the height marked by the natural-waist string). | `spine2` (6) anterior | — | 3852 | — |
| `waist_cb` | Centre-back at the waist plane (same height as `waist_cf`). | `spine2` (6) posterior | — | 5495 | — |

### Crotch + lower midline (1)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `crotch_midpoint` | Midline crotch point — lowest centred vertex on the torso between the inner-thigh meshes. | midway between `left_hip` (1) and `right_hip` (2) | — | 3879 | — |

### Shoulders and neck-shoulder corners (4)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `shoulder_neck_left` | Corner where the left side of the neck meets the shoulder. dpm's "high neck point". Aliases: `high_neck_point_left`. | `left_collar` (13) | — | 3950 | — |
| `shoulder_neck_right` | Right corner where neck meets shoulder. | `right_collar` (14) | — | 6698 | — |
| `acromion_left` | Outer end of the left shoulder bone (acromion process). dpm's "shoulder point" / "shoulder tip". Alias: `shoulder_tip_left`. | `left_shoulder` (16) — lateral | — | 5627 | — |
| `acromion_right` | Outer end of the right shoulder bone. | `right_shoulder` (17) — lateral | — | 8321 | — |

### Front shoulder midpoints (2)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `front_shoulder_centre_left` | Midpoint of the left front shoulder seam, between `shoulder_neck_left` and `acromion_left`, on the front-of-shoulder surface. Used by Aldrich #15 Front shoulder to waist. | between `left_collar` (13) and `left_shoulder` (16), anterior | — | 3236 | — |
| `front_shoulder_centre_right` | Right side, mirror. | between `right_collar` (14) and `right_shoulder` (17), anterior | — | 5999 | — |

### Underarm + armhole anatomy (10)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `underarm_left` | Highest point where left-arm flesh meets left-torso flesh when the arm hangs at the side. Defines `upper_bust_level` height (per dpm bodice_front revision). | `left_shoulder` (16) — inferior | — | 3922 | — |
| `underarm_right` | Right-side mirror. | `right_shoulder` (17) — inferior | — | 6670 | — |
| `armscye_front_left` | Front intersection of the left armhole curve with the torso (front edge of the armpit where the armhole would be drafted). | left of `spine3` (9), at upper-bust level | — | 3234 | — |
| `armscye_front_right` | Right-side mirror. | right of `spine3` (9), at upper-bust level | — | 5997 | — |
| `armscye_back_left` | Back intersection of the left armhole curve with the torso. | left of `spine3` (9), back, at upper-bust level | — | 5610 | — |
| `armscye_back_right` | Right-side mirror. | right of `spine3` (9), back, at upper-bust level | — | 8315 | — |
| `armfold_front_left` | Front end of the left armhole curve where it meets the side seam — distinct from `armscye_front_left` which sits on the internal armhole boundary. (Seamly I04 endpoint.) | `left_shoulder` (16) — inferior anterior | — | 3834 | — |
| `armfold_front_right` | Right-side mirror. | `right_shoulder` (17) — inferior anterior | — | 6589 | — |
| `armfold_back_left` | Back end of the left armhole curve where it meets the side seam. (Seamly I09 endpoint.) | `left_shoulder` (16) — inferior posterior | — | 5481 | — |
| `armfold_back_right` | Right-side mirror. | `right_shoulder` (17) — inferior posterior | — | 8215 | — |

### Bust (3)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `bust_apex_left` | Fullest point of the left breast on the SMPL-X female mesh. | left of `spine3` (9), anterior, at breast height | — | 3572 | — |
| `bust_apex_right` | Right side. | right of `spine3` (9), anterior | — | 6333 | — |
| `lowbust_apex` | Centre-front at the under-bust crease (where a bra band sits). Single midline point. | `spine2` (6) anterior, above `waist_cf` | — | 3855 | — |

### Bra side seam (2)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `bra_side_seam_left` | dpm front/back split landmark at upper-bust level. Defined by a well-fitting bra side seam, or by a point 1.25-1.5 in (~3-4 cm) outboard from where the bra cup ends at the underarm, toward the back. See `dpm_bodice_measurements` transcript:L100-143. | between `underarm_left` and `armscye_back_left` | — | — | — |
| `bra_side_seam_right` | Right side. | between `underarm_right` and `armscye_back_right` | — | — | — |

### Waist sides (2)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `waist_side_left` | Left side at the waist-string height. | `spine2` (6) — lateral left, at waist height | — | 3273 | — |
| `waist_side_right` | Right side at the same height. | `spine2` (6) — lateral right | — | 6036 | — |

### Arm (5)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `elbow_back_left` | Olecranon — bony point at the back of the left elbow when the arm is bent. Picked from the T-pose mesh (same vertex moves with pose). | `left_elbow` (18) posterior | — | 4290 | — |
| `elbow_back_right` | Right side. | `right_elbow` (19) posterior | — | 7032 | — |
| `wrist_ulnar_left` | Left ulna styloid — bone at the pinky side of the wrist (NOT the radial / thumb-side bone, despite what Seamly L01 says — Aldrich convention is ulnar). | `left_wrist` (20), ulnar | — | 4722 | — |
| `wrist_ulnar_right` | Right side. | `right_wrist` (21), ulnar | — | 7458 | — |
| `bicep_max_right` | Fullest point of the right biceps (Aldrich #9 Top arm site, measured with the arm bent — but picked on the T-pose mesh; the vertex tracks with pose). | `right_shoulder` (17) — inferior, midway to `right_elbow` (19) | — | 6022 | — |

### Leg (8)

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `thigh_at_crotch_left` | Lateral side of the left thigh at the crotch level (where dpm's "upper thigh elastic" sits). | `left_hip` (1) — lateral | — | 3477 | — |
| `thigh_at_crotch_right` | Right side. | `right_hip` (2) — lateral | — | 6238 | — |
| `crotch_lateral_left` | Lateral side of the left crotch line — used for the standing-scan body-rise approximation (`aldrich_body_rise`). | between `left_hip` (1) and `crotch_midpoint` | — | 3866 | — |
| `crotch_lateral_right` | Right side. | between `right_hip` (2) and `crotch_midpoint` | — | 6617 | — |
| `knee_back_left` | Back of the left knee crease — sets the height of `mid_knee_level`. | `left_knee` (4) posterior | — | 3679 | — |
| `knee_back_right` | Right side. | `right_knee` (5) posterior | — | 6440 | — |
| `ankle_bone_lateral_left` | Lateral malleolus (outer ankle bone) on the left ankle. | `left_ankle` (7) — lateral | — | 5881 | — |
| `ankle_bone_lateral_right` | Right side. | `right_ankle` (8) — lateral | — | 8575 | — |

### Plane anchors (additional, 2)

These vertices exist to fix the height of a horizontal plane used by
some measurements; they are not anatomically named landmarks in their
own right.

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `rib_front` | Centre-front anchor at the lower-rib level — used by Seamly's `rib_circ` (G06) and `rib_to_waist_side` (H12). Between `lowbust_apex` and `waist_cf`. | `spine2` (6) anterior, between lowbust and waist | — | — | — |
| `mid_neck_front` | Centre-front anchor at mid-neck height — used by Seamly `neck_mid_circ` (G01). | `neck` (12) anterior, between `head` (15) and `front_collar_bone` | — | 5616 | — |

### Audit judgment landmarks (optional, 3)

These are in the audit's `judgment` set (see
`references/seamly/extraction_audit.md`) — fuzzy or pose-dependent. Pick
only if/when the parent measurement is required by a drafting block.

| Landmark | Description | Nearest SMPL-X joint | Proposed | Verified | Screenshot |
|----------|-------------|----------------------|----------|----------|------------|
| `scapula_prominence_left` | Most posterior point of the left scapula (shoulder blade prominence). Used by `height_scapula` (A03). | `spine3` (9) — posterior lateral left | — | — | — |
| `scapula_prominence_right` | Right side. | `spine3` (9) — posterior lateral right | — | — | — |
| `gluteal_fold_midpoint` | Midpoint of the gluteal fold (the crease where the buttock meets the back of the thigh). Used by `height_gluteal_fold` (A07). | midway below `left_hip` (1) / `right_hip` (2), posterior | — | — | — |

## Coverage map

- **Total point landmarks above:** 48 (45 required + 3 optional audit).
- **Plane definitions** derive from already-picked points by horizontal
  projection through Y; no separate vertex picks needed:
  - `waist_string` — from `waist_cb` / `waist_cf` / `waist_side_{L,R}`.
  - `upper_bust_level` — from `underarm_{L,R}`.
  - `bust_level` — from `bust_apex_{L,R}`.
  - `lowbust_level` — from `lowbust_apex`.
  - `rib_level` — from `rib_front`.
  - `mid_neck_level` — from `mid_neck_front`.
  - `crotch_level` — from `crotch_midpoint`.
  - `mid_knee_level` — from `knee_back_{L,R}`.
  - `ankle_level` — from `ankle_bone_lateral_{L,R}`.
  - `high_hip_level`, `low_hip_level`, `calf_level_widest` — geometric
    rules (offset below waist or widest-girth scan); no vertex needed.

## Derived / not-picked

- `bust_apex_midpoint` — midpoint of `bust_apex_left` and `bust_apex_right`.
- `floor_cb` — vertical projection of `waist_cb` onto the ground plane.
- Aliases (`shoulder_tip_*` = `acromion_*`, `high_neck_point_*` =
  `shoulder_neck_*`, `center_front_neck` = `front_neck_point`,
  `center_back_neck` = `c7`) resolve to the same vertex IDs.
- `bra_side_seam_left/right` — skipped during verification; aliased to
  `underarm_left/right` for dpm front/back arc split. ~3-4 cm posterior
  difference is acceptable given the bra_side_seam definition allows
  either reference.
- `rib_front` — skipped. Only used by Seamly `rib_circ` (G06) and
  `rib_to_waist_side` (H12); not needed for Aldrich or dpm.

## Notes

- Joints in the "Nearest SMPL-X joint" column are SMPL-X's skeleton
  joints (see `smplx/joint_names.py`, indices 0-21). They are not mesh
  vertices but their 3D positions help locate the right mesh region.
  Indices are shown in parentheses.
- Pose is T-pose only. The vertex IDs are pose-invariant — the same
  vertex moves with the body when the model is posed. Picks made on the
  T-pose work for any subsequent pose.
- The mesh under `data/body_models/smplx/SMPLX_FEMALE.npz` is the
  10,475-vertex SMPL-X female model. Older SMPL (6,890 vertices) and
  SMPL-H (6,890 + hand) use different IDs — do not transfer.
