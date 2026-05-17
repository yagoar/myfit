# Aldrich pages 178-179 — measurement source notes

## Edition cross-reference

| What | 5th edition (PDF in repo) | 6th edition (user's book) |
|------|--------------------------|---------------------------|
| Size chart | p.13 (PDF p.16) | **p.11** |
| Measurement table | p.178 (PDF p.181) | **p.214** |
| Measurement diagram | p.179 (PDF p.182) | **p.215** |
| Low waist offset | 6cm below natural waist | **5cm** below natural waist |
| Size codes | 6–26 (bust 76–122, 11 sizes) | **6–24** (bust 80–122, 10 sizes) |
| Hip adjustment xref | p.188 | **p.222** |

The **6th edition is canonical** for this project. The user owns the
physical book; three photos are in `references/aldrich/`:

- `IMG_9598.jpg` — p.11 size chart
- `IMG_9599.jpg` — p.214 measurement table + taking-measurements items 1–4
- `IMG_9600.jpg` — p.215 taking-measurements items 5–20 + diagram

Measurement instruction text is identical between editions except item 2a
Low waist (5cm replaces 6cm). Size chart values for corresponding bust
sizes are the same except the largest 1–2 sizes which have retuned hips
and top-arm rows, and the 5th edition's smallest size (size 6, bust 76)
is dropped entirely in the 6th edition.

Source: 6th edition photos in `references/aldrich/IMG_*.jpg` (the 5th-edition
`references/aldrich_full.pdf` was removed after the 6th-edition photos
became the canonical source; book page numbering kept since it matches
both editions).
Book pages **178-179** = PDF pages **181-182** (front-matter offset of +3)
in the now-removed 5th-edition PDF; 6th edition uses the same page numbers.
The Aldrich pages cited by SPEC.md section 5 are these two; the size-chart
page (book p.13) referenced for "standard measurements" is captured in a
separate pass.

These notes are the human-readable trail behind every entry under
`src/tailor_twin/measure/definitions/merged.yaml` that has a
`references/aldrich_full.pdf p.178` or `p.179` citation (the path is
retained as historical provenance even though the PDF is gone). Per GUARDRAILS
section 1.3, Aldrich measurement definitions are FORBIDDEN-from-AI-memory
territory: the entries in `merged.yaml` are transcribed from this source
and verified by the user before being trusted downstream.

## Page 178 — text content

### Heading: "Drafting blocks for individual figures"

A short introduction stating that an individual block draft uses the same
formulas as the standard blocks (Chapter 1) but substitutes personal
measurements for the standard size-chart values. The bust measurement
determines the drafting size — example given: bust 104 cm → size 20. A
note flags that very large busts and "dowager hump" backs require an
adjustment described on book p.186.

### Table: "Personal measurements / Standard measurements / Comments on figure"

Three-column table with twenty numbered rows plus row 2a. Columns:

* **Personal measurements** — example individual figure (illustrative; bold
  type marks values that came from the individual, the others are pulled
  from the standard size chart).
* **Standard measurements** — values for the size determined by the bust
  measurement (size 20 in the example, bust 103.5 cm → 104).
* **Comments on figure** — informal observations on how the individual
  differs from the standard (e.g. "wider shoulders", "slimmer arm").

The twenty measurements (with row numbers preserved verbatim):

| # | Name | Example personal | Standard (size 20) |
|---|---|---|---|
| 1 | Bust | 103.5 | 104 |
| 2 | Waist | 90 | 88 |
| 2a | Low waist | 100 | 98 |
| 3 | Hips | 114 | 112 |
| 4 | Back width | 38.4 | 38.4 |
| 5 | Chest | 37.2 | 37.2 |
| 6 | Shoulder | 13.6 | 13.25 |
| 7 | Neck size | 41 | 41 |
| 8 | Dart | 9.4 | 9.4 |
| 9 | Top arm | 32.2 | 33.2 |
| 10 | Wrist | 17.5 | 18 |
| 11 | Ankle | 25.9 | 26 |
| 12 | High ankle | 22.9 | 23 |
| 13 | Nape to waist | 43.5 | 42.6 |
| 14 | Front shoulder to waist | 46 | 44.1 |
| 15 | Armscye depth | 23.5 | 22.6 |
| 16 | Skirt length | 71 | — (user-set) |
| 17 | Waist to hip | 21.8 | 21.8 |
| 18 | Waist to floor | 110 | 108 |
| 19 | Body rise | 32.5 | 30.8 |
| 20 | Sleeve length | 61.5 | 60.25 |

Footnote: "Extra measurements (garments): these are standard measurements
(see page 13)." — i.e. ease and garment-specific allowances live on the
size-chart page.

### Heading: "Taking measurements" — items 1-4

* **1 Bust** — "Measure the figure at the fullest point of the bust, do
  not allow the tape to fall at the back."
* **2 Waist** — "Take this measurement round the waist, make sure it is
  comfortable." Followed by a procedural instruction to tie a string
  firmly round the waist after the measurement is taken, because that
  string then defines the reference horizon for the vertical measurements
  (items 13, 14, 16, 18).
* **2a Low waist** — "Take the low waist measurement 5 cm (6th edition; was 6 cm in 5th edition) below the
  natural waistline."
* **3 Hips** — "Measure the widest part of the hips approx. 21 cm from
  the waistline." If the hips are more than 5 cm larger than the bust
  (the standard chart's ratio), the book cross-refers to p.188 for the
  dress-block correction.
* **4 Back width** — "Measure the back width 15 cm down from the neck
  bone at the centre back. Measure from armscye to armscye."

## Page 179 — text content

### Heading continued: "Taking measurements" — items 5-20

* **5 Chest** — "Measure the chest 7 cm down from the neck point at the
  centre front (armscye to armscye)."
* **6 Shoulder** — "Measure from neck to the shoulder bone."
* **7 Neck size** — "Measure the base of neck touching front collar bone."
* **8 Dart** — "Standard measurement."
* **9 Top arm** — "The arm must be bent, measure the biceps."
* **10 Wrist** — "Take the wrist measurement with slight ease."
* **11 Ankle** — "Measure around the ankle over ankle bone."
* **12 High ankle** — "Measure around leg just above the ankle." (No
  specific offset stated — see open question in SPEC section 16.)
* **13 Nape to waist** — "Measure from the neck bone at the centre back
  to the string tied around the waist."
* **14 Front shoulder to waist** — "Measure from the centre of the front
  shoulder over the bust point to waist."
* **15 Armscye depth** — "Standard measurement."
* **16 Skirt length** — "Measure the skirt length from the string at the
  waist down to the required hem length." Plus a check note: "Measure
  from the waist to floor at the back and front to check that the
  balance of the figure is even."
* **17 Waist to hip** — "Standard measurement."
* **18 Waist to floor** — "Measure from waist to floor at the centre
  back."
* **19 Body rise** — "The subject should sit on a hard chair. Take the
  measurement at the side from the waist to the chair."
* **20 Sleeve length** — "Place the hand on hip so that the arm is bent.
  Measure from the shoulder bone over the elbow to the wristbone above
  the little finger."

Closing paragraph cross-references the size chart (the individual
measurement list should be compared against the standard list and any
figure faults addressed via the alteration section on the following
pages).

### Diagram on page 179

The diagram occupies the right two-thirds of page 179. It shows **three
figures**: a large standing figure in front view, an equally sized
standing figure in back view, and a small inset figure seated on a
chair in side view (for item 19 Body rise).

**Left figure — front view.** A standing female figure facing the
viewer. The right arm (the viewer's left side) hangs straight down at
the side of the body. The left arm (viewer's right side) is bent at the
elbow with the hand placed on the hip — this is the pose required for
items **9 Top arm** and **20 Sleeve length**. Numbered annotations with
dashed lines indicate:

* **6** along the front shoulder seam from neck-shoulder corner out to
  the acromion (shoulder length, geodesic).
* **7** as a small loop encircling the base of the neck (neck size,
  contoured closed loop).
* **5** as a horizontal line crossing the upper chest (armscye to
  armscye), at 7 cm below the front neck point (chest width segment).
* **1** as a horizontal across the chest at the fullest point of the
  bust, passing through both bust apexes (bust circumference).
* **14** as a slanted/contoured line starting at the centre of the front
  shoulder, descending over the bust apex, and ending at the waist
  string at centre front (front shoulder to waist; surface path).
* **2** as a horizontal at the narrow waist (waist circumference; the
  string sits at this level once tied).
* **17** as a short vertical segment between waist line and hip line at
  the front (waist to hip; standard measurement, shown for reference).
* **3** as a horizontal at the widest hips (hip circumference).
* **16** as a vertical from waist down to skirt hem on the side of the
  figure (skirt length; user-defined).
* **20** following the bent left arm: from shoulder bone (acromion) over
  the outside of the elbow down to the wristbone (sleeve length;
  surface path along bent arm).
* **9** at the biceps level on the bent left arm (top arm
  circumference; bent-arm pose).
* **10** at the wrist (wrist circumference).
* **12** just above the ankle bone (high ankle circumference).
* **11** at the ankle bone level (ankle circumference).

**Right figure — back view.** A standing female figure with her back to
the viewer, both arms hanging straight at the sides. Annotations:

* **7** at the neck base (neck size loop, same as front figure).
* **4** horizontal across the upper back, 15 cm below the neck bone
  (C7), spanning armscye to armscye (back width segment).
* **15** as a vertical from the side of the neck base down to the level
  of the underarm/armscye base on the back (armscye depth; standard
  measurement, shown for reference).
* **13** vertical from the neck bone (C7) down the centre back to the
  waist string (nape to waist; surface path).
* **2** waist horizontal (same as front).
* **3** hip horizontal (same as front).
* **9** biceps annotation matching the front figure.
* **10** wrist annotation matching the front figure.
* **18** full vertical from the waist string at centre back all the way
  to the floor (waist to floor; surface path).

**Seated inset figure (bottom right).** A small side-view figure shown
seated on a chair. A single annotation **19** is drawn between the
waist line at the side of the body and the chair seat directly below
(body rise; seated measurement). The orientation makes clear that the
measurement is taken vertically at the side, not at the back.

## Implications for the SMPL-X pipeline (cross-reference for `merged.yaml`)

* **Items 1, 2, 2a, 3, 10, 11, 12** are horizontal circumferences. They
  map cleanly to `planar_slice` primitives whose plane normal is the
  vertical body axis after un-posing.
* **Items 4 and 5** are width segments, *not* circumferences. They map to
  `planar_segment` — a horizontal slice clipped to a region on the
  back (item 4) or front (item 5).
* **Item 6 Shoulder** is a surface path from the neck-shoulder corner to
  the acromion (`geodesic_path`).
* **Item 7 Neck size** is a closed surface loop around the neck base
  passing through the front-collarbone landmark (`contoured_path`).
* **Item 8 Dart** comes from the standard size chart on book p.13;
  the entry is a `table_lookup` indexed by bust size.
* **Items 9 Top arm and 20 Sleeve length** require the arm to be **bent**
  (hand-on-hip pose). On an A-pose scan the SMPL-X model is re-posed
  virtually to the bent-arm pose before measurement. See SPEC section
  9.1 and the new pose open-question in SPEC section 16.
* **Items 13, 14, 18, 20** are surface paths (`geodesic_path`), with
  item 14 forced through an apex waypoint and item 20 forced through
  the elbow waypoint.
* **Item 15 Armscye depth and item 17 Waist to hip** come from the
  standard size chart (`table_lookup`); the body-derived values can be
  computed for comparison but the canonical value is from the chart.
* **Item 16 Skirt length** is user-supplied (`user_input`), not a body
  measurement.
* **Item 19 Body rise** is a seated measurement. The standing-scan
  derivation (waist height at the side minus crotch-area height) is an
  approximation; expect a 1-2 cm offset versus a real tape and
  calibrate (SPEC section 13 risks). The entry is classified as
  `derived` with a documented approximation.

## Cross-reference: the "natural" measurement pose

Aldrich's figure shows the body standing upright with one arm at the side
and one arm bent for the arm-circumference and sleeve-length
measurements. The figure is not a T-pose — it is the natural standing
pose with a localised bent arm only when the measurement requires it.
This matches the canonical-pose discussion now logged in SPEC section 16.
