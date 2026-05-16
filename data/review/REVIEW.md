# Measurement Review

## Batch 2 fixes (from user review notes)

Removed: **G06, H12, H20, H29** (user dropped from spec).
Moved to FORMULAS: **N08** (= A05 − M01).

New primitives:
- `VerticalDrop(landmark, target_y_landmark)` — straight plumb-line from a landmark to the Y plane of another. Use for "straight down to X" rules.
- `PolylineChord(landmarks…)` — sum of straight 3D chords through N landmarks. Use for yardstick path touching multiple anatomical points.

| Code | Before → After | New cm | Note |
|------|----------------|-------:|------|
| G02 | PlanarGirth → GeodesicLoop(c7, SN_L, FNP, SN_R) | 37.05 | Smooth neckline touching the 4 anchor points |
| H01 | Geodesic → PolylineChord(FNP, bust_apex, waist_cf) | 36.12 | Yardstick touching bust apex |
| H02 | LandmarkChord → Geodesic via lowbust_apex | 32.15 | Tape between the breasts |
| H05 | Geodesic → VerticalDrop(SN, waist_cf) | 33.27 | Plumb-line |
| H06 | LandmarkChord → PolylineChord(SN, bust_apex, waist_cf) | 40.11 | Yardstick |
| H07 | Geodesic → VerticalDrop(FNP, armfold_front_L) | 12.43 | |
| H09 | Geodesic → VerticalDrop(FNP, bust_level) | 16.22 | |
| H14 | Geodesic → VerticalDrop(SN, bust_level) | 19.85 | |
| H15 | Geodesic → VerticalDrop(SN, armfold_front_L) | 16.06 | |
| H18 | Geodesic → VerticalDrop(SN, waist_cb) | 32.99 | |
| H21 | Geodesic → VerticalDrop(c7, armfold_back_L) | 16.02 | Truth 15.44 (was 11.04) |
| H23 | Geodesic → VerticalDrop(c7, bust_level) | 18.80 | |
| H27 | Geodesic → VerticalDrop(SN, bust_level) | 19.85 | |
| H28 | Geodesic → VerticalDrop(SN, armfold_back_L) | 17.08 | |
| H33 | Geodesic → VerticalDrop(waist_cb, high_hip) | 11.28 | |
| H34 | Geodesic → VerticalDrop(waist_cb, low_hip) | 20.28 | |
| H41 | Geodesic → VerticalDrop(c7, armfold_back_L) | 16.02 | |
| I09 | Geodesic → LandmarkChord(armfold_back_L, _R) | 27.21 | |
| I13 | Geodesic → LandmarkChord(c7, acromion_L) | 17.64 | |
| K01 | Geodesic → LandmarkChord(acromion, waist_cf) | 35.01 | |
| K02 | Geodesic → LandmarkChord(FNP, waist_side) | 32.38 | |
| K03 | Geodesic → LandmarkChord(SN, waist_side) | 34.14 | |
| J03 | LandmarkChord → Geodesic(bust_apex, lowbust_apex) | 10.18 | Curve molds to bust |
| J04 | LandmarkChord → VerticalDrop(bust_apex, waist_string) | 13.53 | |
| O01 | rerouted via SN+FNP (was through waist_side) | 47.53 | Goes around neck not under arm |

**Truetoform mean diff:** 2.46 → **2.62 cm** (small regression — many H-codes now obey sewing-rule straight chords/drops that differ slightly from truetoform's body-contoured tape methodology).

**Still pending (need new vertex picks or harder work):**
- B01 acromion → outer deltoid
- G12/G13/G16/G17 per-level side landmarks
- H16 diagonal to highbust Y (partial — currently still geodesic)
- H17 needs back-armscye routing
- H25 back-lowbust landmark
- I03/I07/I08 need new chest-armscye/back-armscye plane landmarks
- J02/J10/J11 bust-clearance offset
- K10/K13 endpoints at bust-level side seam
- L11/L13/L15 arm-perpendicular slicing primitive
- L16 curve from shoulder tip down arm to bicep level
- M02 multi-segment waist→hip→floor
- M07 calf-widest vid re-pick
- P01 endpoint at G03 center front
- P09 force route via bust apex midpoint

---

## Session fixes applied (batch 1)

| Code | Before | After | Truth | Fix |
|------|-------:|------:|------:|-----|
| **G02** neck_circ | 44.06 | **35.07** | 35.92 | bumped `neck_base_level` Y-offset 2.5cm → 4cm; was capturing trapezius |
| **G03** highbust | (prev session) | 84.99 | 84.10 | TapeLoop primitive |
| **A10** height_ankle_high | 6.80 | **9.90** | — | new `ankle_high_level` compound (ankle_bone + 3cm) so it's distinct from A11 |
| **M08** ankle_high_circ | 6.90 (Height!) | **20.43** | — | `Height` → `PlanarGirth` on ankle_high_level + left_leg mask |
| **M03** thigh_upper_circ | 54.49 (mask=leg+torso) | 54.49 | 57.05 | strict `left_leg` mask (torso bridged both legs at thigh-crotch Y) |
| **H02** flat_f | 32.17 (= H01) | **30.42** | — | `Geodesic` → `LandmarkChord` (straight chord, not over bust) |
| **H06** flat_f | 38.60 (= H05) | **35.85** | — | `Geodesic` → `LandmarkChord` |
| **H27** neck_side_to_bust_b | 25.18 (= H14) | **42.88** | — | added `armfold_back_left` waypoint so the geodesic routes over the back of the shoulder |
| **I02** shoulder_tip_to_shoulder_tip_f | 33.47 | 33.47 | — | added `front_neck_point` waypoint (no value change — FNP already on natural geodesic) |

**Truetoform comparison:** mean |diff| 2.99 → 2.70 → 2.55 → **2.46 cm**

---



Fit: `data/results/yaiza_smplx_fit.npz` (300 betas + smooth-D)
All A-pose, female model.

Severity legend: ✅ matches diagram, ⚠️ minor deviation, 🔴 trajectory wrong.

---

## Group A — Heights (14 codes)

All A-group are `Height(landmark)` — straight vertical line from landmark
Y down to floor at landmark XZ. Trajectory is correct by construction.
Quality depends on landmark Y selection.

| Code | Name | cm | Landmark | Verdict |
|------|------|----|----------|---------|
| A01 | height | 160.05 | top_of_head | ✅ |
| A02 | height_neck_back | 134.75 | c7 | ✅ |
| A04 | height_armpit | 118.72 | underarm_left | ✅ |
| A05 | height_waist_side | 102.16 | waist_side_left | ✅ |
| A06 | height_hip | 82.53 | low_hip_level | ✅ |
| A08 | height_knee | 42.72 | mid_knee_level | ✅ |
| A10 | height_ankle_high | 6.80 | ankle_level | ⚠️ A10 vs A11 nearly identical (6.80 vs 6.90) — both target the ankle bone. Seamly intent for "ankle_high" is the narrowest part above the ankle bone (~5cm above), not the bone itself. Add `ankle_high_level` compound. |
| A11 | height_ankle | 6.90 | ankle_bone_lateral_left | ✅ |
| A12 | height_highhip | 91.53 | high_hip_level | ✅ |
| A13 | height_waist_front | 102.53 | waist_cf | ✅ |
| A14 | height_bustpoint | 116.06 | bust_apex_left | ✅ |
| A15 | height_shoulder_tip | 131.57 | acromion_left | ✅ |
| A16 | height_neck_front | 132.18 | front_neck_point | ✅ |
| A17 | height_neck_side | 135.80 | shoulder_neck_left | ✅ |

**Group A flags:** A10 needs distinct landmark from A11.

---

## Group B — Widths (4 codes)

| Code | Name | cm | Recipe | Verdict |
|------|------|----|--------|---------|
| B01 | width_shoulder | 32.26 | LandmarkChord(acromion_L, acromion_R) | ⚠️ Diagram shows shoulder width to **outer** edge of shoulder cap (past acromion). Our value 32.26 vs truetoform 43.23 (−25%). Acromion landmarks sit too medial — they're at the shoulder joint, not the deltoid bulge. Add `shoulder_tip_outer` landmark at deltoid widest point. |
| B02 | width_bust | 27.94 | LateralChord(bust_level, torso) | ✅ Horizontal max-X chord at bust Y, torso-only mask. |
| B03 | width_waist | 24.02 | LateralChord(waist_string, torso) | ✅ |
| B04 | width_hip | 33.52 | LateralChord(low_hip_level, torso+legs) | ✅ Includes legs mask so the chord captures the lateral hip cap, not just torso. |

**Group B flags:** B01 needs outer-deltoid landmark, not acromion.

---

## Group G — Circumferences & front arcs (16 codes)

### Circumferences (G01-G09): `PlanarGirth` = horizontal-plane convex hull

| Code | Name | cm | Plane | Verdict |
|------|------|----|-------|---------|
| G01 | neck_mid_circ | 37.77 | mid_neck_level | ✅ Mid-neck horizontal slice. |
| G02 | neck_circ | 44.06 | neck_base_level | 🔴 Truth 35.92 (+27%). `neck_base_level` (front_neck_point + 2.5cm) lands too low — capturing trapezius shoulder slope. Adjust offset to +5cm or pick a higher mid-neck landmark. |
| G03 | highbust_circ | 84.99 | TapeLoop | ✅ Newly built loop (planar back + geodesic front via armfolds). Truth 84.10. |
| G04 | bust_circ | 85.92 | bust_level | ✅ Truth 87.58, −1.9%. |
| G05 | lowbust_circ | 71.05 | lowbust_level | ✅ |
| G06 | rib_circ | 65.32 | waist_string | 🔴 Same plane as G07 → identical value. Needs distinct `rib_level` landmark above waist (~ribcage bottom). |
| G07 | waist_circ | 65.32 | waist_string | ✅ Truth 66.14, +1.9%. |
| G08 | highhip_circ | 79.53 | high_hip_level | ✅ |
| G09 | hip_circ | 90.68 | low_hip_level (torso+legs mask) | ✅ Truth 92.13, +0.7%. Mask includes legs so hull catches the lateral hip cap. |

### Front arcs (G10-G17)

| Code | Name | cm | Recipe | Verdict |
|------|------|----|--------|---------|
| G10 | neck_arc_f | 16.40 | PlanarArc front at FNP between SN_L and SN_R | ✅ |
| G11 | highbust_arc_f | 43.51 | Geodesic underarm→armfold→armfold→underarm | ✅ Just extended; matches G03 front. |
| G12 | bust_arc_f | 44.92 | PlanarArc front at bust between waist_side_L/R | ⚠️ Clip endpoints are waist_side, not bust-level side seams. Length ≈ half circ but with vertical drop into waist. Better clip: bust_level slice at max-X. |
| G13 | lowbust_arc_f | 36.29 | PlanarArc front at lowbust between waist_side_L/R | ⚠️ Same clip-landmark issue as G12. |
| G15 | waist_arc_f | 35.53 | PlanarArc front at waist between waist_side_L/R | ✅ Clip matches plane. |
| G16 | highhip_arc_f | 39.10 | PlanarArc front at highhip between waist_side_L/R | ⚠️ Same clip mismatch — endpoints at waist, plane at highhip. |
| G17 | hip_arc_f | 46.05 | PlanarArc front at lowhip between waist_side_L/R | ⚠️ Same clip mismatch. |

**Group G flags:**
- G02 neck base slice too low (truth diff +27%)
- G06/G07 share same plane (rib_level placeholder)
- G12/G13/G16/G17 use waist_side as clip endpoints but slice at a different Y — arc endpoints drop vertically into the slice plane. Need per-level `<level>_side` landmarks.

---

## Group H — Vertical lengths (34 codes)

All H-group are `Geodesic` between two landmarks (one `LandmarkChord`).
Trajectory = shortest path on body surface. Most look correct as
surface-following paths. Issues are mostly **duplicate recipes** where
two distinct measurements share identical waypoints.

### Duplicate-recipe pairs (need distinct paths)

| Pair | Issue |
|------|-------|
| H01 / H02 | 32.15 vs 32.17 — H02 should be "flat" front (straight chord over bust, not geodesic) but uses same start/end + bust_apex_left waypoint. Bust apex already lies on geodesic so it does nothing. Use `LandmarkChord` for H02, or PlanarArc on sagittal plane. |
| H05 / H06 | 38.60 identical — same fix as H01/H02 for the neck-side → waist-front path. |
| H18 / H20 | 39.29 identical — H20 is supposed to route via scapula. Missing `scapula_left` waypoint. |
| H14 / H27 | 25.18 identical — H14 is _f, H27 is _b. Geodesic neck_side ↔ bust_apex is the same path regardless. H27 should route via the BACK of the shoulder. Needs distinct back-of-body waypoint, e.g. via armfold_back_left. |
| H03 / H12 | 16.88 identical — H03 = armpit_to_waist_side, H12 = rib_to_waist_side. Need distinct "rib" landmark to anchor H12. |

### Per-code

| Code | Name | cm | Verdict |
|------|------|----|---------|
| H01 | neck_front_to_waist_f | 32.15 | ✅ geodesic |
| H02 | …_flat_f | 32.17 | 🔴 dup of H01 — recipe should be straight chord (LandmarkChord) |
| H03 | armpit_to_waist_side | 16.88 | ✅ |
| H04 | shoulder_tip_to_waist_side_f | 32.06 | ✅ |
| H05 | neck_side_to_waist_f | 38.60 | ✅ |
| H06 | …_bustpoint_f | 38.60 | 🔴 dup of H05 |
| H07 | neck_front_to_highbust_f | 21.35 | ✅ FNP→armfold front, short front-of-chest path |
| H09 | neck_front_to_bust_f | 20.94 | ✅ |
| H11 | lowbust_to_waist_f | 7.47 | ✅ |
| H12 | rib_to_waist_side | 16.88 | 🔴 dup of H03 — needs `rib_side_left` landmark |
| H13 | shoulder_tip_to_armfold_f | 14.44 | ✅ |
| H14 | neck_side_to_bust_f | 25.18 | ✅ |
| H15 | neck_side_to_highbust_f | 20.86 | ✅ |
| H16 | shoulder_center_to_highbust_f | 16.91 | ✅ |
| H17 | shoulder_tip_to_waist_side_b | 37.84 | ✅ (back-side geodesic) |
| H18 | neck_side_to_waist_b | 39.29 | ✅ |
| H19 | neck_back_to_waist_b | 33.74 | ⚠️ truth 37.44 (−11%) — c7 vid may sit too low or waist_cb too high. |
| H20 | …_scapula_b | 39.29 | 🔴 dup of H18 — needs scapula waypoint |
| H21 | neck_back_to_highbust_b | 11.04 | ⚠️ truth 15.44 (−17%) — `armscye_back_midpoint` lies higher than expected scapula-level highbust. |
| H23 | neck_back_to_bust_b | 34.08 | ✅ |
| H25 | lowbust_to_waist_b | 33.88 | ⚠️ value seems too long for lowbust→waist; recipe routes from lowbust_apex (front) to waist_cb (back) → path wraps around side. Possibly intended as back-only measurement (back of lowbust to back of waist). |
| H26 | shoulder_tip_to_armfold_b | 16.83 | ✅ |
| H27 | neck_side_to_bust_b | 25.18 | 🔴 dup of H14 — needs back routing |
| H28 | neck_side_to_highbust_b | 23.15 | ✅ |
| H29 | shoulder_center_to_highbust_b | 19.12 | ✅ |
| H30 | waist_to_highhip_f | 11.61 | ✅ |
| H31 | waist_to_hip_f | 19.57 | ✅ |
| H32 | waist_to_highhip_side | 21.29 | ⚠️ goes waist_side → high_hip_level (a Y-plane landmark used as a 3D point at X=0). Endpoint mid-body → geodesic crosses centerline. Should resolve high_hip_level to side-X. |
| H33 | waist_to_highhip_b | 35.91 | ⚠️ same issue — waist_cb to high_hip_level=mid-body point. |
| H34 | waist_to_hip_b | 40.25 | ⚠️ same |
| H35 | waist_to_hip_side | 26.37 | ⚠️ same as H32 |
| H37 | shoulder_slope_neck_side_length | 11.04 | ✅ |
| H39 | shoulder_slope_neck_back_height | 17.64 | ✅ chord (straight line) c7-acromion |
| H41 | neck_back_to_across_back | 18.88 | ✅ |

**Group H flags:**
- 5 duplicate-recipe pairs (H01/02, H03/12, H05/06, H14/27, H18/20)
- H32/H33/H34/H35 use Y-plane landmarks (`high_hip_level`, `low_hip_level`) as 3D endpoints → land at X=0 centerline instead of body surface. Need per-side landmarks (`high_hip_side_left`, etc.) or resolve plane-Y to nearest body vertex at endpoint X.
- H21 truth diff −17% — armscye_back vertex location.

---

## Group I — Shoulder/across (10 codes)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| I01 | shoulder_length | 11.04 | ✅ geodesic SN→acromion |
| I02 | shoulder_tip_to_shoulder_tip_f | 33.47 | ⚠️ geodesic across front torso between acromions — natural path dips into upper chest (no waypoint at jugular notch). Should add `front_neck_point` waypoint to keep path along clavicle plane. |
| I03 | across_chest_f | 36.82 | ✅ |
| I04 | armfold_to_armfold_f | 36.82 | 🔴 dup of I03 — same recipe |
| I07 | shoulder_tip_to_shoulder_tip_b | 36.22 | ✅ uses c7 waypoint, runs over nape |
| I08 | across_back_b | 30.60 | ✅ |
| I09 | armfold_to_armfold_b | 30.60 | 🔴 dup of I08 |
| I12 | neck_front_to_shoulder_tip_f | 16.73 | ✅ |
| I13 | neck_back_to_shoulder_tip_b | 18.13 | ✅ |
| I14 | neck_width | 12.31 | ✅ chord SN↔SN |

**Group I flags:** I04 dup of I03, I09 dup of I08, I02 may dip through chest hollow.

---

## Group J — Bust apex chords (8 codes)

All J-group are `LandmarkChord` (straight 3D line). Trajectory trivially
correct; quality depends on bust_apex_left landmark accuracy.

| Code | Name | cm | Verdict |
|------|------|----|---------|
| J01 | bustpoint_to_bustpoint | 16.48 | ✅ |
| J02 | bustpoint_to_neck_side | 23.99 | ✅ |
| J03 | bustpoint_to_lowbust | 10.57 | ⚠️ chord goes from apex to **midline** lowbust_apex; intent is usually apex → lowbust BELOW the apex on same side. Recipe is between left apex and CF lowbust. |
| J04 | bustpoint_to_waist | 16.12 | ⚠️ same issue — apex to CF waist_string |
| J07 | bustpoint_to_shoulder_tip | 21.33 | ✅ |
| J08 | bustpoint_to_waist_front | 16.12 | 🔴 dup of J04 (waist_string == waist_cf via alias) |
| J10 | bustpoint_to_shoulder_center | 22.04 | ✅ |
| J11 | bustpoint_to_neck_front | 20.00 | ✅ |

**Group J flags:** J04/J08 duplicate. J03/J04 use CF endpoint where intent may be ipsilateral.

---

## Group K — Diagonal lengths (10 codes)

All K-group are `Geodesic`. Likely several duplicates with H group.

| Code | Name | cm | Verdict |
|------|------|----|---------|
| K01 | shoulder_tip_to_waist_front | 38.09 | ✅ |
| K02 | neck_front_to_waist_side | 37.55 | ✅ |
| K03 | neck_side_to_waist_side_f | 38.02 | ✅ |
| K04 | shoulder_tip_to_waist_back | 37.84 | 🔴 dup of H17 (same recipe acromion→waist_cb) |
| K06 | neck_back_to_waist_side | 38.76 | ✅ |
| K08 | neck_side_to_armfold_f | 20.86 | 🔴 dup of H15 |
| K09 | neck_side_to_armpit_f | 24.04 | ✅ |
| K10 | neck_side_to_bust_side_f | 25.18 | 🔴 dup of H14 |
| K11 | neck_side_to_armfold_b | 23.15 | 🔴 dup of H28 |
| K13 | neck_side_to_bust_side_b | 42.88 | ⚠️ routes via armfold_back to bust_apex — path wraps around shoulder. Likely correct as intended (long over-shoulder route). |

**Group K flags:** 4 duplicates with H group (K04, K08, K10, K11).

---

## Group L — Arms (10 codes)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| L05 | arm_shoulder_tip_to_wrist | 53.39 | ✅ |
| L06 | arm_shoulder_tip_to_elbow | 31.22 | ✅ |
| L08 | arm_armpit_to_wrist | 44.56 | ✅ |
| L09 | arm_armpit_to_elbow | 21.50 | ✅ |
| L11 | arm_upper_circ | 26.55 | ✅ planar slice on right_arm |
| L13 | arm_elbow_circ | 25.36 | ✅ |
| L15 | arm_wrist_circ | 15.88 | ✅ |
| L16 | arm_shoulder_tip_to_armfold_line | 14.44 | 🔴 dup of H13 |
| L19 | armscye_circ | 39.84 | ⚠️ GeodesicLoop through 4 waypoints; check that the loop closes around the armscye and not under the arm. Truth value not in compare set. |
| L21 | armscye_width | 12.36 | ✅ chord |

**Group L flags:** L16 dup of H13; L19 needs visual verification.

---

## Group M — Legs (7 codes)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| M01 | leg_crotch_to_floor | 76.01 | ✅ Height from crotch_midpoint (inseam) |
| M02 | leg_waist_side_to_floor | 102.16 | 🔴 dup of A05 (same recipe) |
| M03 | leg_thigh_upper_circ | 54.49 | ⚠️ planar slice at `thigh_at_crotch_left` Y with leg+torso mask; at crotch level the slice straddles both legs — needs strict mask to one leg. |
| M05 | leg_knee_circ | 34.11 | ✅ |
| M07 | leg_calf_circ | 33.90 | ✅ |
| M08 | leg_ankle_high_circ | 6.90 | 🔴 recipe is `Height`, not circumference. Wrong primitive. Should be `PlanarGirth(ankle_high_level, regions=('left_leg',))`. |
| M09 | leg_ankle_circ | 24.68 | ✅ |

**Group M flags:** M02 dup of A05, M03 crotch-Y mask too loose, M08 wrong primitive.

---

## Group N — Crotch (3 codes)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| N01 | crotch_length | 69.28 | ⚠️ truth 63.68 (+8.4%). geodesic via crotch_midpoint can stray inside thigh skin — check side render. |
| N02 | crotch_length_b | 36.79 | ✅ |
| N08 | rise_length_side | 27.89 | ✅ |

---

## Group O — Misc (1 code)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| O01 | neck_back_to_waist_front | 52.90 | ✅ geodesic via waist_side_left |

---

## Group P — Front geodesics (6 codes)

| Code | Name | cm | Verdict |
|------|------|----|---------|
| P01 | neck_back_to_bust_front | 34.08 | 🔴 dup of H23 |
| P02 | neck_back_to_armfold_front | 29.42 | ✅ wraps from c7 over shoulder to armfold front |
| P03 | neck_back_to_armfold_front_to_waist_side | 46.64 | ✅ |
| P09 | armfold_to_armfold_bust | 36.82 | 🔴 dup of I03 — adding bust_apex waypoints doesn't change geodesic since apex lies on path |
| P10 | armfold_to_bust_front | 13.34 | ✅ |
| P12 | armscye_arc | 20.71 | ✅ geodesic front-armscye → acromion → back-armscye |

**Group P flags:** P01, P09 duplicates.

---

## Summary of action items

### Duplicate recipes (15 codes need distinct routing)
- **Front vs flat:** H01/H02, H05/H06
- **Generic vs scapula/rib:** H03/H12, H18/H20
- **Same waypoints across groups:** H14/H27, I03/I04, I08/I09, J04/J08, K04==H17, K08==H15, K10==H14, K11==H28, L16==H13, M02==A05, P01==H23, P09==I03

### Wrong primitive
- M08 ankle_high_circ uses `Height` — should be `PlanarGirth`

### Landmark/region issues
- B01 acromion too medial → needs outer-deltoid landmark
- G02 neck base slice too low (+27% over truth) → bump offset
- G06/G07 share rib/waist plane → need real rib_level
- G12/G13/G16/G17 clip with waist_side at non-waist Y planes
- H32/H33/H34/H35 use Y-plane landmarks as 3D points
- H21 armscye_back vid location off
- M03 thigh upper circ mask too loose
- A10 ankle_high vs A11 ankle: same landmark

### Trajectory issues
- G03: ✅ fixed this session (TapeLoop with geodesic front via armfolds)

### Visual artifacts (rendering only, not measurement)
- Body opacity 0.55 makes back-side anatomy bleed through front renders; lines stay correct.
- Tape/girth polylines show as paired ribbons under transparency — front+back hull edges both rendered.
