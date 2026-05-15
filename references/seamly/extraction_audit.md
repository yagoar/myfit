# Seamly catalog extraction audit

Phase 6 planning artifact. Classifies each of the 245 catalog entries in
`references/seamly/README.md` for the proposed generic Seamly extractor.

## Classes

- **mechanical** — well-defined extraction from the scan + verified
  landmarks. One of:
  - height from floor to a named landmark (vertical distance);
  - planar slice at a named horizontal plane (convex-hull perimeter for
    a circumference, clipped arc for front/back splits);
  - lateral chord at a named plane (B-group widths);
  - landmark-pair chord (straight-line distance);
  - geodesic surface path between landmarks with documented waypoints.
  No new textual interpretation needed beyond the landmark glossary
  already in `merged.yaml`.
- **computed** — README marks the entry as `yes: <formula>`. Free at
  extract time: declare `type: derived`, evaluate from other entries.
  No mesh work.
- **judgment** — needs textual interpretation, pose-specific
  reasoning, or a fuzzy landmark that the SPEC §16 open questions have
  not yet resolved. E.g. "natural waist" geometric rule, scapula
  prominence, gluteal fold, indent depth conventions, anatomically
  ambiguous tape conventions, hand/foot mesh resolution.
- **standard** — not measured on the body. Sourced from a size chart
  (Aldrich p.13 / p.11) or user input. The Q-group dart widths are the
  only catalog entries that fall here.

## Summary by group

| Group | Topic | Mech | Judg | Comp | Std | Total |
|-------|-------|------|------|------|-----|-------|
| A | Heights | 15 | 2 | 6 | 0 | 23 |
| B | Widths | 4 | 1 | 0 | 0 | 5 |
| C | Indents | 0 | 3 | 0 | 0 | 3 |
| D | Hand | 0 | 5 | 0 | 0 | 5 |
| E | Foot | 0 | 4 | 0 | 0 | 4 |
| F | Head | 0 | 4 | 2 | 0 | 6 |
| G | Circumferences & Arcs | 18 | 3 | 25 | 0 | 46 |
| H | Vertical Distances | 34 | 3 | 5 | 0 | 42 |
| I | Shoulder & Across | 10 | 0 | 4 | 0 | 14 |
| J | Bustpoint | 9 | 0 | 2 | 0 | 11 |
| K | Shoulder/Neck Paths | 13 | 0 | 0 | 0 | 13 |
| L | Arm | 17 | 0 | 5 | 0 | 22 |
| M | Leg | 11 | 0 | 3 | 0 | 14 |
| N | Crotch & Rise | 3 | 2 | 3 | 0 | 8 |
| O | Natural Waist & Arm Ext | 8 | 5 | 1 | 0 | 14 |
| P | Complex Torso Paths | 12 | 0 | 0 | 0 | 12 |
| Q | Dart Widths | 0 | 0 | 0 | 3 | 3 |
| **Total** | | **154** | **32** | **56** | **3** | **245** |

**Headline:** 154 + 56 = **210 entries (86%) are "free" or mechanical**
once landmarks are verified. 32 entries (13%) need textual judgment.
3 entries are size-chart values.

The judgment set is small enough to add to `merged.yaml` by hand once a
specific block requires the slot. The mechanical set justifies a single
generic extractor pass that emits all 154 slots in one go.

## Per-measurement classification

### Group A — Heights (23)

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| A01 | `height` | mechanical | top-of-head to floor |
| A02 | `height_neck_back` | mechanical | C7 to floor |
| A03 | `height_scapula` | judgment | scapula prominence is a fuzzy landmark |
| A04 | `height_armpit` | mechanical | underarm to floor |
| A05 | `height_waist_side` | mechanical | waist_string side to floor |
| A06 | `height_hip` | mechanical | low_hip plane to floor |
| A07 | `height_gluteal_fold` | judgment | gluteal fold detection on mesh is non-trivial |
| A08 | `height_knee` | mechanical | mid-knee plane to floor |
| A09 | `height_calf` | mechanical | calf-widest plane to floor |
| A10 | `height_ankle_high` | mechanical | ~5 cm above ankle bone — fixed offset |
| A11 | `height_ankle` | mechanical | lateral malleolus to floor |
| A12 | `height_highhip` | mechanical | high_hip plane to floor |
| A13 | `height_waist_front` | mechanical | waist_cf to floor |
| A14 | `height_bustpoint` | mechanical | bust apex to floor |
| A15 | `height_shoulder_tip` | mechanical | acromion to floor |
| A16 | `height_neck_front` | mechanical | front neck point to floor |
| A17 | `height_neck_side` | mechanical | shoulder_neck to floor |
| A18 | `height_neck_back_to_knee` | computed | |
| A19 | `height_waist_side_to_knee` | computed | |
| A20 | `height_waist_side_to_hip` | computed | |
| A21 | `height_knee_to_ankle` | computed | |
| A22 | `height_neck_back_to_waist_side` | computed | |
| A23 | `height_waist_back` | computed | |

### Group B — Widths (5)

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| B01 | `width_shoulder` | mechanical | acromion-to-acromion lateral chord |
| B02 | `width_bust` | mechanical | bust-level lateral chord |
| B03 | `width_waist` | mechanical | waist-level lateral chord |
| B04 | `width_hip` | mechanical | hip-level lateral chord |
| B05 | `width_abdomen_to_hip` | judgment | abdomen plane is fuzzy; depends on figure shape |

### Group C — Indents (3)

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| C01 | `indent_neck_back` | judgment | indent = body-vs-vertical-plane depth, needs convention |
| C02 | `indent_waist_back` | judgment | same convention question |
| C03 | `indent_ankle_high` | judgment | same convention question |

### Group D — Hand (5)

All five are **judgment**. The LiDAR scan resolution at hands is borderline
and fingers/palm details are typically poor without a dedicated close-up
scan. Likely better captured by tape or a separate hand-scan pose.

| Code | Name | Class |
|------|------|-------|
| D01 | `hand_palm_length` | judgment |
| D02 | `hand_length` | judgment |
| D03 | `hand_palm_width` | judgment |
| D04 | `hand_palm_circ` | judgment |
| D05 | `hand_circ` | judgment |

### Group E — Foot (4)

All four are **judgment**. Feet are at the scan boundary, often partially
occluded by the floor mesh. Better as tape or dedicated foot scan.

| Code | Name | Class |
|------|------|-------|
| E01 | `foot_width` | judgment |
| E02 | `foot_length` | judgment |
| E03 | `foot_circ` | judgment |
| E04 | `foot_instep_circ` | judgment |

### Group F — Head (6)

Head measurements are pose-specific (hair interference, neck cant) and
typically taken with a tape.

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| F01 | `head_circ` | judgment | hair interference; tape convention |
| F02 | `head_length` | judgment | front-to-back vs ear-to-ear convention |
| F03 | `head_depth` | judgment | depends on orientation convention |
| F04 | `head_width` | judgment | ear-to-ear width — depends on head pose |
| F05 | `head_crown_to_neck_back` | computed | |
| F06 | `head_chin_to_neck_back` | computed | |

### Group G — Circumferences & Arcs (46)

G01-G09 are planar girths at named horizontal planes. G10-G17 are the
front arcs (chord-clipped slices). G18-G41 are all halves or back arcs,
all formula-derived. G42-G45 are torso variants. G46 computed.

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| G01 | `neck_mid_circ` | mechanical | planar slice at mid-neck height |
| G02 | `neck_circ` | mechanical | planar slice at neck base |
| G03 | `highbust_circ` | mechanical | planar slice at upper_bust_level |
| G04 | `bust_circ` | mechanical | planar slice at bust_level |
| G05 | `lowbust_circ` | mechanical | planar slice below bust |
| G06 | `rib_circ` | mechanical | planar slice at lower rib |
| G07 | `waist_circ` | mechanical | planar slice at waist_string |
| G08 | `highhip_circ` | mechanical | planar slice at high_hip_level |
| G09 | `hip_circ` | mechanical | planar slice at low_hip_level |
| G10 | `neck_arc_f` | mechanical | front arc at neck base, clipped at bra_side_seam or equivalent |
| G11 | `highbust_arc_f` | mechanical | front arc at upper_bust_level |
| G12 | `bust_arc_f` | mechanical | front arc at bust_level |
| G13 | `lowbust_arc_f` | mechanical | front arc at lowbust |
| G14 | `rib_arc_f` | mechanical | front arc at rib |
| G15 | `waist_arc_f` | mechanical | front arc at waist |
| G16 | `highhip_arc_f` | mechanical | front arc at high_hip |
| G17 | `hip_arc_f` | mechanical | front arc at low_hip |
| G18-G25 | half-front arcs | computed | divisions by 2 |
| G26-G33 | back arcs | computed | circ − front arc |
| G34-G41 | half-back arcs | computed | |
| G42 | `hip_with_abdomen_arc_f` | judgment | abdomen-protrusion variant; figure-shape dependent |
| G43 | `body_armfold_circ` | mechanical | circ through armfold level |
| G44 | `body_bust_circ` | judgment | "body" prefix in Seamly means arms-included — pose dependent |
| G45 | `body_torso_circ` | judgment | full torso including arms — pose dependent |
| G46 | `hip_circ_with_abdomen` | computed | |

### Group H — Vertical Distances Front & Back (42)

Most H entries are landmark-to-landmark vertical distances along the
body. Mechanical given the landmarks. The shoulder-slope-angle entries
(H36, H38, H40) are judgment because they require a shoulder-slope
direction convention.

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| H01 | `neck_front_to_waist_f` | mechanical | |
| H02 | `neck_front_to_waist_flat_f` | mechanical | |
| H03 | `armpit_to_waist_side` | mechanical | |
| H04 | `shoulder_tip_to_waist_side_f` | mechanical | |
| H05 | `neck_side_to_waist_f` | mechanical | |
| H06 | `neck_side_to_waist_bustpoint_f` | mechanical | |
| H07 | `neck_front_to_highbust_f` | mechanical | |
| H08 | `highbust_to_waist_f` | computed | |
| H09 | `neck_front_to_bust_f` | mechanical | |
| H10 | `bust_to_waist_f` | computed | |
| H11 | `lowbust_to_waist_f` | mechanical | |
| H12 | `rib_to_waist_side` | mechanical | |
| H13 | `shoulder_tip_to_armfold_f` | mechanical | |
| H14 | `neck_side_to_bust_f` | mechanical | |
| H15 | `neck_side_to_highbust_f` | mechanical | |
| H16 | `shoulder_center_to_highbust_f` | mechanical | |
| H17 | `shoulder_tip_to_waist_side_b` | mechanical | |
| H18 | `neck_side_to_waist_b` | mechanical | |
| H19 | `neck_back_to_waist_b` | mechanical | |
| H20 | `neck_side_to_waist_scapula_b` | mechanical | scapula not strictly needed; vertical distance |
| H21 | `neck_back_to_highbust_b` | mechanical | |
| H22 | `highbust_to_waist_b` | computed | |
| H23 | `neck_back_to_bust_b` | mechanical | |
| H24 | `bust_to_waist_b` | computed | |
| H25 | `lowbust_to_waist_b` | mechanical | |
| H26 | `shoulder_tip_to_armfold_b` | mechanical | |
| H27 | `neck_side_to_bust_b` | mechanical | |
| H28 | `neck_side_to_highbust_b` | mechanical | |
| H29 | `shoulder_center_to_highbust_b` | mechanical | |
| H30 | `waist_to_highhip_f` | mechanical | |
| H31 | `waist_to_hip_f` | mechanical | |
| H32 | `waist_to_highhip_side` | mechanical | |
| H33 | `waist_to_highhip_b` | mechanical | |
| H34 | `waist_to_hip_b` | mechanical | |
| H35 | `waist_to_hip_side` | mechanical | |
| H36 | `shoulder_slope_neck_side_angle` | judgment | angle definition + slope reference axis |
| H37 | `shoulder_slope_neck_side_length` | mechanical | landmark-pair geodesic |
| H38 | `shoulder_slope_neck_back_angle` | judgment | angle definition |
| H39 | `shoulder_slope_neck_back_height` | mechanical | vertical distance |
| H40 | `shoulder_slope_shoulder_tip_angle` | judgment | angle definition |
| H41 | `neck_back_to_across_back` | mechanical | |
| H42 | `across_back_to_waist_b` | computed | |

### Group I — Shoulder & Across (14)

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| I01 | `shoulder_length` | mechanical | geodesic shoulder_neck → acromion |
| I02 | `shoulder_tip_to_shoulder_tip_f` | mechanical | front-side path |
| I03 | `across_chest_f` | mechanical | already mapped (`dpm_bodice_across_chest`) |
| I04 | `armfold_to_armfold_f` | mechanical | front armfold-to-armfold path |
| I05 | `shoulder_tip_to_shoulder_tip_half_f` | computed | |
| I06 | `across_chest_half_f` | computed | |
| I07 | `shoulder_tip_to_shoulder_tip_b` | mechanical | back-side path |
| I08 | `across_back_b` | mechanical | already mapped (`dpm_bodice_across_back` / `aldrich_back_width`) |
| I09 | `armfold_to_armfold_b` | mechanical | back armfold-to-armfold path |
| I10 | `shoulder_tip_to_shoulder_tip_half_b` | computed | |
| I11 | `across_back_half_b` | computed | |
| I12 | `neck_front_to_shoulder_tip_f` | mechanical | |
| I13 | `neck_back_to_shoulder_tip_b` | mechanical | |
| I14 | `neck_width` | mechanical | shoulder_neck_left to shoulder_neck_right chord |

### Group J — Bustpoint (11)

All 9 raw J entries are landmark-pair distances from the bust apex to
another named landmark. Mechanical given the two endpoints.

| Code | Name | Class |
|------|------|-------|
| J01 | `bustpoint_to_bustpoint` | mechanical (already mapped: `dpm_bodice_bust_span`) |
| J02 | `bustpoint_to_neck_side` | mechanical |
| J03 | `bustpoint_to_lowbust` | mechanical |
| J04 | `bustpoint_to_waist` | mechanical (added this session) |
| J05 | `bustpoint_to_bustpoint_half` | computed |
| J06 | `bustpoint_neck_side_to_waist` | computed |
| J07 | `bustpoint_to_shoulder_tip` | mechanical |
| J08 | `bustpoint_to_waist_front` | mechanical |
| J09 | `bustpoint_to_bustpoint_halter` | mechanical |
| J10 | `bustpoint_to_shoulder_center` | mechanical (added this session) |
| J11 | `bustpoint_to_neck_front` | mechanical |

### Group K — Shoulder/Neck Paths (13)

All 13 are geodesic paths between named landmarks. Mechanical.

| Code | Name | Class |
|------|------|-------|
| K01 | `shoulder_tip_to_waist_front` | mechanical |
| K02 | `neck_front_to_waist_side` | mechanical |
| K03 | `neck_side_to_waist_side_f` | mechanical |
| K04 | `shoulder_tip_to_waist_back` | mechanical |
| K05 | `shoulder_tip_to_waist_b_1in_offset` | mechanical (fixed 1" offset spec) |
| K06 | `neck_back_to_waist_side` | mechanical |
| K07 | `neck_side_to_waist_side_b` | mechanical |
| K08 | `neck_side_to_armfold_f` | mechanical |
| K09 | `neck_side_to_armpit_f` | mechanical |
| K10 | `neck_side_to_bust_side_f` | mechanical |
| K11 | `neck_side_to_armfold_b` | mechanical |
| K12 | `neck_side_to_armpit_b` | mechanical |
| K13 | `neck_side_to_bust_side_b` | mechanical |

### Group L — Arm (22)

Bent-arm entries (L01-L04) assume the `bent_arm_aldrich` or
`bent_arm_sleeve_dpm` pose is captured. Straight-arm entries (L05-L09)
use the `measurement_default` pose.

| Code | Name | Class |
|------|------|-------|
| L01 | `arm_shoulder_tip_to_wrist_bent` | mechanical (already mapped twice) |
| L02 | `arm_shoulder_tip_to_elbow_bent` | mechanical (already mapped) |
| L03 | `arm_elbow_to_wrist_bent` | computed |
| L04 | `arm_elbow_circ_bent` | mechanical (already mapped) |
| L05 | `arm_shoulder_tip_to_wrist` | mechanical |
| L06 | `arm_shoulder_tip_to_elbow` | mechanical |
| L07 | `arm_elbow_to_wrist` | computed |
| L08 | `arm_armpit_to_wrist` | mechanical |
| L09 | `arm_armpit_to_elbow` | mechanical |
| L10 | `arm_elbow_to_wrist_inside` | computed |
| L11 | `arm_upper_circ` | mechanical (already mapped) |
| L12 | `arm_above_elbow_circ` | mechanical |
| L13 | `arm_elbow_circ` | mechanical |
| L14 | `arm_lower_circ` | mechanical |
| L15 | `arm_wrist_circ` | mechanical (already mapped) |
| L16 | `arm_shoulder_tip_to_armfold_line` | mechanical |
| L17 | `arm_neck_side_to_wrist` | computed |
| L18 | `arm_neck_side_to_finger_tip` | computed |
| L19 | `armscye_circ` | mechanical |
| L20 | `armscye_length` | mechanical (already mapped: `aldrich_armscye_depth` — but Seamly L20 is body-measured here vs Aldrich's chart standard) |
| L21 | `armscye_width` | mechanical |
| L22 | `arm_neck_side_to_outer_elbow` | computed |

### Group M — Leg (14)

| Code | Name | Class |
|------|------|-------|
| M01 | `leg_crotch_to_floor` | mechanical |
| M02 | `leg_waist_side_to_floor` | mechanical |
| M03 | `leg_thigh_upper_circ` | mechanical (already mapped) |
| M04 | `leg_thigh_mid_circ` | mechanical (already mapped: `dpm_pants_lower_thigh`) |
| M05 | `leg_knee_circ` | mechanical |
| M06 | `leg_knee_small_circ` | mechanical (below kneecap) |
| M07 | `leg_calf_circ` | mechanical |
| M08 | `leg_ankle_high_circ` | mechanical (already mapped) |
| M09 | `leg_ankle_circ` | mechanical (already mapped) |
| M10 | `leg_knee_circ_bent` | mechanical (requires bent-knee pose if used) |
| M11 | `leg_ankle_diag_circ` | mechanical (diagonal across ankle bone) |
| M12 | `leg_crotch_to_ankle` | computed |
| M13 | `leg_waist_side_to_ankle` | computed |
| M14 | `leg_waist_side_to_knee` | computed |

### Group N — Crotch & Rise (8)

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| N01 | `crotch_length` | mechanical | full crotch geodesic, front waist → back waist via crotch |
| N02 | `crotch_length_b` | mechanical | back portion of the geodesic, split at crotch lateral midpoint |
| N03 | `crotch_length_f` | computed | |
| N04 | `rise_length_side_sitting` | judgment | requires seated pose; standing scan provides only an approximation (see `aldrich_body_rise` notes) |
| N05 | `rise_length_diag` | judgment | seated diagonal rise; same pose issue |
| N06 | `rise_length_b` | computed | |
| N07 | `rise_length_f` | computed | |
| N08 | `rise_length_side` | mechanical | standing side rise (waist side to crotch lateral) |

### Group O — Natural Waist & Arm Extensions (14)

The "natural waist" geometric rule is still an SPEC §16 open question
(Aldrich = "comfortable round the waist"; dpm = "smallest part of the
torso"). Until resolved, O02-O07 are judgment.

| Code | Name | Class | Reason if judgment |
|------|------|-------|---------------------|
| O01 | `neck_back_to_waist_front` | mechanical | geodesic through the side, full path |
| O02 | `waist_to_waist_halter` | judgment | halter line is a drafting convention, not a body landmark |
| O03 | `waist_natural_circ` | judgment | natural-waist definition open in SPEC §16 |
| O04 | `waist_natural_arc_f` | judgment | same |
| O05 | `waist_natural_arc_b` | computed | |
| O06 | `waist_to_natural_waist_f` | judgment | same |
| O07 | `waist_to_natural_waist_b` | judgment | same |
| O08 | `arm_neck_back_to_elbow_bent` | mechanical | geodesic in bent-arm pose |
| O09 | `arm_neck_back_to_wrist_bent` | mechanical | |
| O10 | `arm_neck_side_to_elbow_bent` | mechanical | |
| O11 | `arm_neck_side_to_wrist_bent` | mechanical | |
| O12 | `arm_across_back_center_to_elbow_bent` | mechanical | |
| O13 | `arm_across_back_center_to_wrist_bent` | mechanical | |
| O14 | `arm_armscye_back_center_to_wrist_bent` | mechanical | |

### Group P — Complex Torso Paths (12)

All 12 are multi-waypoint geodesic paths across the torso. Mechanical
given landmarks and waypoint conventions — the paths themselves are
explicitly described in the Seamly diagrams (Pp1-Pp12), so no judgment
is needed.

| Code | Name | Class |
|------|------|-------|
| P01 | `neck_back_to_bust_front` | mechanical |
| P02 | `neck_back_to_armfold_front` | mechanical |
| P03 | `neck_back_to_armfold_front_to_waist_side` | mechanical |
| P04 | `highbust_back_over_shoulder_to_armfold_front` | mechanical |
| P05 | `highbust_back_over_shoulder_to_waist_front` | mechanical |
| P06 | `neck_back_to_armfold_front_to_neck_back` | mechanical |
| P07 | `across_back_center_to_armfold_front_to_across_back_center` | mechanical |
| P08 | `neck_back_to_armfold_front_to_highbust_back` | mechanical |
| P09 | `armfold_to_armfold_bust` | mechanical |
| P10 | `armfold_to_bust_front` | mechanical |
| P11 | `highbust_b_over_shoulder_to_highbust_f` | mechanical |
| P12 | `armscye_arc` | mechanical |

### Group Q — Dart Widths (3)

Standard values from the size chart, not body-measured.

| Code | Name | Class |
|------|------|-------|
| Q01 | `dart_width_shoulder` | standard |
| Q02 | `dart_width_bust` | standard (already in `aldrich_size_chart_p13.yaml`) |
| Q03 | `dart_width_waist` | standard |

## Landmarks needed beyond the current `merged.yaml` glossary

The current glossary at the top of `merged.yaml` covers roughly 30
symbolic landmarks. The mechanical extractor needs additional landmarks
to cover all 154 mechanical entries. The new requirements, grouped:

- **Vertical-distance landmarks** for A-group heights and H-group
  vertical distances: `bra_side_seam` (already present),
  `lowbust_level`, `rib_level`, `armpit_level` (already present as
  `upper_bust_level`), `highbust_level` (same), `mid_neck_level`,
  `calf_level_widest`, `mid_knee_level` (already present).
- **Front/back-arc clip landmarks** for G-group arcs:
  `armscye_front` (already present), `armscye_back` (already present),
  `side_seam_at_waist` (left and right side at the waist plane).
  All G arcs split at these.
- **Bustpoint-target landmarks** for J-group: `bust_apex_left/right`
  (already present), plus `lowbust_apex`, `front_neck_point` (present),
  `front_shoulder_centre_*` (present), `shoulder_neck_*` (present),
  `shoulder_tip_*` (alias for acromion, present).
- **Armhole landmarks** for I/L/P groups: `armfold_front_*`,
  `armfold_back_*` (front/back ends of the armhole curve where it
  meets the side seam — distinct from `armscye_*` which is the
  internal armhole). `armpit_*` (already present as `underarm_*`).
- **Crotch geodesic landmarks** for N-group: `crotch_midpoint`,
  `crotch_lateral` (already present), and the waist plane endpoints
  already covered.

Total new symbolic landmarks: roughly 12-15 beyond the current set.
Each requires Phase 5 Blender vertex-ID verification per GUARDRAILS §3.

## Implementation sketch

The Phase 6 generic extractor reads a single Python dictionary that maps
Seamly catalog code → extraction recipe. Recipe types:

- `Height(landmark)` → vertical distance from floor to the landmark's
  z-coordinate.
- `PlanarGirth(plane)` → convex-hull perimeter of the mesh slice at the
  named horizontal plane.
- `PlanarArc(plane, clip_start, clip_end)` → chord-clipped front or
  back arc.
- `LateralChord(plane)` → widest lateral chord at the plane.
- `LandmarkChord(a, b)` → straight-line distance.
- `Geodesic(waypoints)` → surface-path geodesic through ordered
  waypoints.
- `Formula(other_codes, expr)` → arithmetic on already-computed
  entries.

The extractor iterates the dictionary, runs the appropriate primitive,
and produces a `{seamly_code: value_cm}` map. The export script writes
that map into a `.smis` template (per drafting system or
`all_measurements_template`).

`merged.yaml` continues to be the authoritative source for the subset
of measurements that Aldrich, dpm, or other documented systems actually
use, with full textual citations. The Phase 6 generic extractor uses
the catalog recipes; the `merged.yaml` entries cite primary sources and
add interpretation notes where the system's definition diverges from
Seamly's (e.g. Aldrich's bent-arm `arm_upper_circ` vs Seamly's
straight-arm default).

## Status

This audit is a planning artifact. No code or `merged.yaml` changes
follow from it directly. Re-visit when Phase 5 (landmark verification
in Blender) is in progress, and use it to drive Phase 6 extractor
scoping.
