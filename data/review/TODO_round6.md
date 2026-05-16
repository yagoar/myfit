# Round 6 review TODO

Source: `data/review/round6_notes.json` (`/Users/ygo/Downloads/review_notes (5).json`)

Viewer: http://127.0.0.1:8051/?code=<CODE>

Mark items `[x]` when the user confirms the fix looks good.

| # | code | status | recipe | note from user |
|---|------|--------|--------|----------------|
| 1 | G10 | [x] | Geodesic(SN_L, FNP, SN_R) | arc neck side → FNP → neck side |
| 2 | H06 | [x] | DiagonalSurfacePlumb SN→apex, chord to body waist at SN→apex X column (h06_endpoint_left) | start like H05 at apex angle, continue to waist; line below bust goes IN toward body |
| 3 | H16 | [x] | DiagonalSurfacePlumb SN→h16_endpoint_left (G03 polyline ∩ SN→apex 3D line) | like H15 but point toward apex, end at G03 line |
| 4 | H25 | [x] | SurfacePlumb(waist_cb, lowbust_level, back) | waist_cb up to same X on lowbust |
| 5 | H32 | [x] | Geodesic(waist_side_left, waist_side_left_at_highhip_y) | match H35 |
| 6 | H37 | [x] | VerticalDrop(acromion_left, shoulder_neck_left) | vertical height shoulder tip → neck side Y (4.23 cm — small but correct Y delta) |
| 7 | H39 | [x] | VerticalDrop(acromion_left, c7) | vertical height shoulder tip → neck back Y |
| 8 | I03 | [x] | Geodesic(armscye_front_l/r_at_i03_y) | armscye X, 2/3 Y between FNP and G03 CF |
| 9 | I08 | [x] | Geodesic(armfold_back_l/r_at_i08_y) | armfold_back X, 2/3 between c7 and I09 |
| 10 | J01 | [x] | LandmarkChord straight=True | no contour |
| 11 | J03 | [x] | Geodesic(apex, j03_endpoint_left = G05 ∩ apex↓ line) | endpoint must touch G05 |
| 12 | J08 | [x] | LandmarkChord straight=True | straight chord |
| 13 | L13 | [x] | LimbGirth bicep_max_left vid 3259, left_arm | mirror right → left |
| 14 | M07 | [x] | calf vid 3712 → 3725 (max-girth Y) | lower calf point |
| 15 | P09 | [x] | Geodesic chained via=True, smooth=True via bust_front_cf | curve down to centre of G04 from armfolds |

## Pending follow-ups (carried over)

- M07 originally needed Blender vid re-pick. Used algorithmic max-girth slice → vid 3725. Verify in viewer.
- bicep_max_left mirror was approximate (dist 0.0046 m to mirrored target). Verify L13 slice.
