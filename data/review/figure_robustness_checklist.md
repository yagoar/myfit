# Figure-robustness checklist

Empirical drift verified against two real fits (yaiza 160 cm, carmen 174 cm).
Drift % = `(carmen/yaiza) / (height_ratio) − 1`. ±5 % is noise. Anything
larger is a body-shape robustness signal.

Source of the numbers: re-extracted both CSVs with current code (the
checked-in `carmen_measurements.csv` was pre-rename and used a stale schema).
See `data/review/figure_robustness_audit.md` for the per-constant audit
the checklist refines.

Status legend: `[ ]` pending — `[~]` in progress — `[x]` done.

---

## 1. Ankle high level — dynamic min-girth search ✅

- [x] Replace `ankle_high_level` `offset_y` compound (+0.03 m above
      `ankle_bone_lateral_left`) with dynamic search: narrowest leg
      girth between `ankle_bone_lateral_left` and `knee_back_left`
      (`left_leg` region).
- [x] Add `min_girth_y` search type to `DYNAMIC_SEARCHES` in
      `landmarks.py`. Re-uses `slice_mesh` / `_build_loops` /
      `_convex_hull_perimeter` from `mesh_ops`.
- [x] Regenerate `yaiza_measurements.baseline.csv`.

**Result:** Lands ~4.2 cm above the malleolus on yaiza, ~4.4 cm on
carmen — a true min-girth point, body-specific. Prior fixed 0.03 m
offset was anatomically arbitrary. M08 leg_ankle_high_circ drift
−4.4 % (was within noise — landmark is now correctly anchored even
if the headline magnitude shift was small).

**Residual:** A11 (`height_ankle`) and M09 (`leg_ankle_circ`)
still drift +38 % / −11 %. Those use `ankle_bone_lateral_left` /
`ankle_level` directly — anatomical foot-height variation, not a
measurement bug. Re-evaluate once tape calibration is available.

## 2. Low hip + high hip — Seamly is the canonical definition

### Reference survey

**Seamly `all_measurements_with_descriptions.pdf` (canonical for our
schema).** Both planes are anatomical, not waist-offset:

- **A12 height_highhip** (old_name `high_hip_height`): "Vertical
  distance from the Highhip level, where **front abdomen is most
  prominent**, to the floor."
- **A06 height_hip** (old_name `hip_height`): "Vertical distance from
  the Hip level to the floor." — A06 defers to the plane chosen by G09.
- **G08 highhip_circ** (old_name `high_hip_girth`): "Circumference
  around Highhip, where **Abdomen protrusion is greatest**, parallel
  to floor."
- **G09 hip_circ** (old_name `hips_excluding_protruding_abdomen`):
  "Circumference around Hip where **Hip protrusion is greatest**,
  parallel to floor." The old_name is the key: hip plane is the
  *lateral* hip widest point, explicitly excluding the abdomen
  (which is covered by G08).

So Seamly cleanly separates the two:
- **highhip plane Y** = arg-max of front (Z+) abdomen protrusion below
  the waist.
- **hip plane Y** = arg-max of lateral hip width (|X|) below the
  highhip, above the crotch.

Both are per-body anatomical searches. No offset rule, no chart
constant.

**Aldrich (6th ed., p.178–179 + size chart p.11).** ONE hip
measurement only (item #3): "widest part of the hips approx. 21 cm
from the waistline". No high_hip concept. Item #17 `Waist to hip` is
a size-chart constant (21.8 cm in the example), not per-body.
Aldrich's "low waist" (item #2a, 5 cm below natural waist) is an
alternative anchor for the *waist itself*, not for the hip — used
for low-rise garments. So Aldrich gives us one rule:
**low_hip = max-girth slice below the waist**. Compatible with
Seamly's G09 because the lateral hip widest also happens to be the
girth max on most figures — Aldrich just isn't picky about which
extremum.

**dpm (Maria's `pants_1` + `pants_2` transcripts).** Two planes:

- `high_hip` = 4–5 in below waist, "depending on your height"
  (pants_2 §31). Pure Y-offset rule, scales with height.
- `low_hip` = widest girth below waist + above legs (pants_1 §103,
  §167). Algorithmic max-girth.
- **Exception** (pants_1 §169–179): if widest is at high_hip or
  crotch, set `low_hip = crotch + 2.75 in`. Protects apple-shape /
  crotch-widest figures.

dpm's algorithmic flavour is the most prescriptive, but its
high_hip is a heuristic (offset) rather than an anatomical
landmark. Seamly's is the anatomical one (abdomen protrusion max).

### Aldrich's low_waist — does it factor in here?

No. Low_waist is an alternative anchor for the waist horizon (5 cm
below the natural waistline) used when drafting low-rise garments.
It shifts everything below the waist down by 5 cm in the *drafted
block*, but the body's hip planes themselves are still defined off
the natural waist. Keep low_waist as a separate concept, don't
tangle it with the hip definitions.

### Recommendation: follow Seamly

Seamly is canonical for our schema (we export G08/G09/A06/A12/Hp9/Hp10
into the SMIS), and Seamly's definitions are the most anatomically
grounded — independent of figure height, no offset heuristic to tune.

- **highhip_level** = arg-max of front abdomen protrusion (max Z) in
  Y band [waist − 0.25 m, waist − 0.02 m], `torso` region. Tight X
  band around centre-front (to ignore side bulges).
- **low_hip_level** = arg-max of lateral hip width (max |X| of the
  torso slice's convex-hull extents) in Y band [highhip − 0.02 m,
  crotch + 0.02 m], `torso` region. The old_name
  `hips_excluding_protruding_abdomen` makes this unambiguous: it's
  the *side-prominent* point, not the *front-prominent* point.

This gives Aldrich users a defensible G09 (Aldrich's "widest hip"
overlaps Seamly's lateral max for non-apple figures), and dpm users
get a `low_hip` that matches dpm's algorithm for standard figures.
For apple-shape figures Seamly's hip plane stays under the abdomen
plane by construction (different extrema, separate Y bands), which
implicitly handles dpm's exception clause without a special case.

### Implementation — done

- [x] Added `max_front_z_y` dynamic search: per-Y slice, picks the Y
      whose front protrusion (max Z) is greatest among centre-line
      vertices (`±x_midline_band` = 5 cm around `waist_cf` X). Lands
      cleanly on the abdomen, not on hip flares.
- [x] `high_hip_level` → `max_front_z_y` search in window
      `[crotch_midpoint + 0.02, waist_string − 0.04]`, `torso` region.
- [x] `hip_level` → midpoint of SMPL-X `L_Hip` and `R_Hip` joint Y
      (`lerp_joint`). The joints are femur-head rotation centres
      regressed across CAESAR scans — anatomically the greater
      trochanter, shape- and pose-invariant. Beats every offset rule
      tested: G09 hip_circ = 92.95 cm vs 92.13 cm truth tape on yaiza
      (+0.9 %), vs crotch+7 cm (90.14, −2.2 %) and the prior fixed
      waist−20 cm offset (90.68, −1.6 %). Tried before settling: a
      `max_lateral_x_y` dynamic search (kept registered but unused —
      profile is monotone on SMPL-X so it degenerates) and a
      `max_front_z_y` highhip search restricted to the body midline.
- [x] `max_lateral_x_y` handler registered but unused (kept for future
      anatomical searches; remove if it doesn't earn its keep).
- [x] Regenerated `yaiza_measurements.baseline.csv`.
- [x] All 43 tests pass.

### Result — drift collapse on carmen vs yaiza (height-normalised)

| code | name | before | after |
|------|------|--------|-------|
| A06 | height_hip | n/a | −0.3 % |
| A12 | height_highhip | n/a | +0.6 % |
| B04 | width_hip | n/a | −0.5 % |
| G08 | highhip_circ | (−6.6 % via G24) | +1.5 % |
| G09 | hip_circ | n/a | −0.8 % |
| G16 | highhip_arc_f | +6.6 % | +5.7 % |
| G17 | hip_arc_f | n/a | +1.1 % |
| G24 | highhip_arc_half_f | +6.6 % | +5.7 % |
| G32 | highhip_arc_b | −11.1 % | −2.9 % |
| G40 | highhip_arc_half_b | −11.1 % | −2.9 % |
| H30 | waist_to_highhip_f | n/a | +1.0 % |
| H32 | waist_to_highhip_side | −12.7 % | +3.1 % |
| H33 | waist_to_highhip_b | −17.4 % | −0.6 % |
| H34 | waist_to_hip_b | −9.7 % | −0.2 % |
| H35 | waist_to_hip_side | −13.8 % | −0.4 % |
| G09 | hip_circ — yaiza truth match | n/a | **+0.9 %** vs 92.13 cm tape |

All hip-anchored codes now drift ≤ ±7 %, most ≤ ±3 %. The biggest
remaining is H34 waist_to_hip_b (−6.6 %) — surface plumb on the back,
sensitive to the curvature of the buttock cap on different figures.
Acceptable.

### Visual review (recommended)

- [ ] Open `/measure/review_viewer` against
      `data/results/carmen_smplx_fit.npz` and
      `data/results/yaiza_smplx_fit.npz`. Confirm:
      - `high_hip_level` plane sits on the abdomen forward
        protrusion (belly button area).
      - `hip_level` plane sits on the buttock crease / seat.

### Evidence

H35 waist_to_hip_side −14 %, H32 waist_to_highhip_side −13 %, H33
waist_to_highhip_b −17 %, G40 highhip_arc_half_b −11 %, G32
highhip_arc_b −11 %, G16/G24 highhip_arc_f +6.6 %. Comment in
`landmarks.py:198` already flags the fixed 0.20 m offset as a
placeholder.

## 3. High hip level — folded into #2

(See #2 implementation plan: height-ratio-scaled offset off the waist.)
Kept as a separate row in the original audit; merged here because the
decision is coupled to the low_hip definition.

## 4. Underbust crease — bust-depth aware drop_fraction

- [ ] Change `underbust_crease_left.drop_fraction` from constant 0.5 to
      a function of `bust_depth` (apex_z − chest_wall_z). Smaller bust
      → smaller fraction.
- [ ] Test on carmen first (smaller drift, easier signal).

**Evidence:** H25 lowbust_to_waist_b +7 %, G13 lowbust_arc_f −7.6 %,
G21 lowbust_arc_half_f −7.6 %, H11 lowbust_to_waist_f +6.5 %.
Medium-priority — already in audit section F.

## 5. Bust apex lerp — defer

- [ ] No action. Verified low real-world drift on carmen (J03 −8 %, H23
      out of top-30). Keep audit section A note for future calibration.

## 6. Acromion / shoulder-slope landmarks — investigate

- [ ] Check whether H39 / H37 / L16 drift comes from fit pose (raised
      shoulders) or vertex-ID instability across betas.
- [ ] If pose: tighten arm-rest pose constraint in fit. If vid: add a
      `body_at_xy` style dynamic landmark for `acromion_left` searching
      max-Z on the shoulder cap region.
- [ ] Defer until a tape vs. extracted calibration tells us which side
      is right.

**Evidence:** H39 shoulder_slope_neck_back_height +28 %, H37 +13 %,
L16 arm_shoulder_tip_to_armfold_line −17 %. Not in original audit.

## 7. Cross-figure regression test harness

- [ ] Once #1–#4 land, add `tests/test_cross_figure_robustness.py`:
      asserts every measurement code's drift between yaiza and carmen
      stays under a per-code budget (10 % default, 15 % for
      acromion-anchored codes until #6 lands).
- [ ] Wire into CI so a future fit doesn't silently undo the work.

---

## How to redo the drift analysis

```bash
source .venv/bin/activate
python -m tailor_twin.measure.cli data/results/yaiza_smplx_fit.npz \
    --seamly --save-csv /tmp/yaiza_now.csv --no-bent-arm
python -m tailor_twin.measure.cli data/results/carmen_smplx_fit.npz \
    --seamly --save-csv /tmp/carmen_now.csv --no-bent-arm
python -c "
import csv
y = {r['code']: (r['seamly_name'], float(r['value_cm']))
     for r in csv.DictReader(open('/tmp/yaiza_now.csv'))}
c = {r['code']: (r['seamly_name'], float(r['value_cm']))
     for r in csv.DictReader(open('/tmp/carmen_now.csv'))}
hr = c['A01'][1] / y['A01'][1]
rows = []
for k in sorted(set(y) & set(c)):
    yv, cv = y[k][1], c[k][1]
    if yv < 0.5: continue
    drift = (cv/yv / hr - 1) * 100
    rows.append((abs(drift), drift, k, y[k][0], yv, cv))
rows.sort(reverse=True)
for _, d, k, nm, yv, cv in rows[:30]:
    print(f'{k:<5} {nm[:46]:<46} {yv:7.2f} {cv:7.2f} {d:+8.1f}')
"
```
