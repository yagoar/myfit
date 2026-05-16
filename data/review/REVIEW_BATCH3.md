# Review batch 3 — open items

Source: second-round user review notes (`flagged_round2.json`).

Big themes:
1. **Lines cut through body interior** — many LandmarkChord / VerticalDrop / PolylineChord visualisations pass through the chest, bust, neck. User wants the line to **sit on top of the body surface**, not inside it. Likely fix: render polylines snapped to the front body surface at each X/Z (a "tape draped vertically on the front" sampler), separate from the measurement value.
2. **Circumferences perpendicular to limb axis, not the floor.** G01 neck, L11 bicep, L13 elbow, L15 wrist. Need a new primitive that slices perpendicular to the local axis through the landmark.
3. **G02 / G10 smoother neckline**. Current GeodesicLoop dips at FNP (throat hollow). Replace with convex-hulled loop or a planar-arc-style smooth ring.
4. **H06 / H14 / H15 / H16 etc. still cutting through bust**. The endpoint at the bust line needs to be on the body surface front (not midline interior or apex Z).

## Per-code (open)

### "Sit on top of body, not inside" — needs viz on body surface
| Code | Note |
|------|------|
| H05 | should go down on top of the body, not through the inside |
| H23 | sit on top, not inside |
| H27 | sit on top, not inside |
| H28 | sit on top, not inside |
| H41 | sit on top, not inside |
| I09 | on top, not inside |
| I13 | on top, not inside |
| J02 | on top, not inside |
| J10 | on top, not inside |
| K01 | on top, not inside |
| K02 | on top, not inside |
| K03 | on top, not inside |

Probable fix: new render-time helper that snaps the polyline to the front body surface at constant X (or along the chord's axis) so the line drapes on the body. Length unchanged.

### G group neckline + circumference plane
| Code | Note |
|------|------|
| G01 | perpendicular to neck tube, not the floor |
| G02 | smoother — currently V-dips at front and back |
| G10 | curve up to neck sides; like G01 but cut off at SN_L/R |

### Bust-touching points
| Code | Note |
|------|------|
| H06 | first leg (SN→apex) still cuts the bust; second leg from apex should follow same angle down to **G07** (waist), not waist_cf only |
| H14 | should go **straight down from neck** to touch G04 (currently diagonal to apex_left) |
| H15 | straight down to touch G03 |
| H16 | angle toward apex but stop at G03 |
| H25 | start at "lowbust X back" point on G05 (same X as waist_cb), then to waist_cb |

### H series — vertical drops on/along body
| Code | Note |
|------|------|
| H17 | shoulder tip → curve around armscye back → straight down to G07 |
| H32 | down the side (geodesic) waist_side to touch G08 |
| H35 | side seam geodesic to G09 |
| H39 | vertical line from shoulder point up to SN Y (currently chord, length OK; viz wrong) |

### I group
| Code | Note |
|------|------|
| I03 | across-chest line height = 2/3 between FNP and CF point on G03; X = FNP.x for CF |
| I07 | straight chord shoulder_tip → shoulder_tip (no detour via c7) |
| I08 | halfway level between c7 and G03, X axis = c7 (center-back) |

### J / K
| Code | Note |
|------|------|
| J04 | straight from apex toward G07 (waist Y on body surface at apex X), not plumb to floor |
| K10 | touch G04 at side seam (use underarm X as side seam ref) |
| K13 | same on back |

### L / M / N / P
| Code | Note |
|------|------|
| L11 | perpendicular to arm at underarm Y (bicep at underarm level) |
| L13 | perpendicular to arm |
| L15 | perpendicular to arm |
| L16 | shoulder tip down arm to L11 level (curve) |
| L19 | smoother loop |
| M02 | geodesic waist_side → hip_side, then straight to floor (two segments) |
| M07 | calf_widest vid too high — re-pick lower |
| P01 | touch G04 at center-front axis |
| P09 | curve from armfold front to G04 center-front and back |
| P12 | over shoulder tip explicitly |

## Order of attack
1. Build the **surface-snap viz** for VerticalDrop / LandmarkChord paths
2. Add **ArmGirth** primitive (perpendicular slice along arm axis) for L11/L13/L15
3. G02 / G10 smoother neckline (convex-hull or longer loop)
4. Rewire H06 / H14 / H15 / H16 endpoints to body-surface points
5. M02 multi-segment
6. M07 calf vid re-pick
