wrote docs/catalog_coverage.md (245 codes, 167 extracted)
_recipe_table.py`. Values are the latest Yaiza extraction (`data/results/yaiza_seamly_catalog.json`).

**Summary:** 245 total — 167 extracted, 0 skipped, 35 judgment/standard, 43 without recipe.

| Code | Seamly name | Recipe | Status | Value (cm) |
|------|-------------|--------|--------|------------|
| A01 | height | Height | extracted | 160.05 |
| A02 | height_neck_back | Height | extracted | 134.75 |
| A03 | height_scapula | — | skipped (scapula prominence — fuzzy landmark) |  |
| A04 | height_armpit | Height | extracted | 118.72 |
| A05 | height_waist_side | Height | extracted | 102.16 |
| A06 | height_hip | Height | extracted | 82.53 |
| A07 | height_gluteal_fold | — | skipped (gluteal fold detection — needs mesh-feature finder) |  |
| A08 | height_knee | Height | extracted | 42.72 |
| A09 | height_calf | — | no recipe |  |
| A10 | height_ankle_high | Height | extracted | 9.90 |
| A11 | height_ankle | Height | extracted | 6.90 |
| A12 | height_highhip | Height | extracted | 91.53 |
| A13 | height_waist_front | Height | extracted | 102.53 |
| A14 | height_bustpoint | Height | extracted | 116.06 |
| A15 | height_shoulder_tip | Height | extracted | 131.57 |
| A16 | height_neck_front | Height | extracted | 132.18 |
| A17 | height_neck_side | Height | extracted | 135.80 |
| A18 | height_neck_back_to_knee | Formula('A02 - A08') | extracted | 92.03 |
| A19 | height_waist_side_to_knee | Formula('A05 - A08') | extracted | 59.44 |
| A20 | height_waist_side_to_hip | Formula('A05 - A06') | extracted | 19.62 |
| A21 | height_knee_to_ankle | Formula('A08 - A11') | extracted | 35.82 |
| A22 | height_neck_back_to_waist_side | Formula('A02 - A05') | extracted | 32.59 |
| A23 | height_waist_back | Formula('A02 - 0') | extracted | 134.75 |
| B01 | width_shoulder | LandmarkChord | extracted | 32.26 |
| B02 | width_bust | LateralChord | extracted | 27.94 |
| B03 | width_waist | LateralChord | extracted | 24.02 |
| B04 | width_hip | LateralChord | extracted | 33.52 |
| B05 | width_abdomen_to_hip | — | skipped (abdomen plane — figure-shape dependent) |  |
| C01 | indent_neck_back | — | skipped (indent_neck_back convention) |  |
| C02 | indent_waist_back | — | skipped (indent_waist_back convention) |  |
| C03 | indent_ankle_high | — | skipped (indent_ankle_high convention) |  |
| D01 | hand_palm_length | — | skipped (hand — scan resolution too low) |  |
| D02 | hand_length | — | skipped (hand — scan resolution too low) |  |
| D03 | hand_palm_width | — | skipped (hand — scan resolution too low) |  |
| D04 | hand_palm_circ | — | skipped (hand — scan resolution too low) |  |
| D05 | hand_circ | — | skipped (hand — scan resolution too low) |  |
| E01 | foot_width | — | skipped (foot — partially occluded by floor) |  |
| E02 | foot_length | — | skipped (foot — partially occluded by floor) |  |
| E03 | foot_circ | — | skipped (foot — partially occluded by floor) |  |
| E04 | foot_instep_circ | — | skipped (foot — partially occluded by floor) |  |
| F01 | head_circ | — | skipped (head_circ — hair interference) |  |
| F02 | head_length | — | skipped (head_length — convention) |  |
| F03 | head_depth | — | skipped (head_depth — convention) |  |
| F04 | head_width | — | skipped (head_width — convention) |  |
| F05 | head_crown_to_neck_back | — | no recipe |  |
| F06 | head_chin_to_neck_back | — | no recipe |  |
| G01 | neck_mid_circ | LimbGirth | extracted | 32.92 |
| G02 | neck_circ | GeodesicLoop | extracted | 37.05 |
| G03 | highbust_circ | TapeLoop | extracted | 84.99 |
| G04 | bust_circ | PlanarGirth | extracted | 85.92 |
| G05 | lowbust_circ | PlanarGirth | extracted | 72.42 |
| G06 | rib_circ | — | no recipe |  |
| G07 | waist_circ | PlanarGirth | extracted | 65.32 |
| G08 | highhip_circ | PlanarGirth | extracted | 79.53 |
| G09 | hip_circ | PlanarGirth | extracted | 90.68 |
| G10 | neck_arc_f | Geodesic | extracted | 19.14 |
| G11 | highbust_arc_f | Geodesic | extracted | 43.51 |
| G12 | bust_arc_f | PlanarArc | extracted | 44.92 |
| G13 | lowbust_arc_f | PlanarArc | extracted | 37.37 |
| G14 | rib_arc_f | — | no recipe |  |
| G15 | waist_arc_f | PlanarArc | extracted | 35.53 |
| G16 | highhip_arc_f | PlanarArc | extracted | 39.10 |
| G17 | hip_arc_f | PlanarArc | extracted | 46.05 |
| G18 | neck_arc_half_f | Formula('G10 / 2') | extracted | 9.57 |
| G19 | highbust_arc_half_f | Formula('G11 / 2') | extracted | 21.76 |
| G20 | bust_arc_half_f | Formula('G12 / 2') | extracted | 22.46 |
| G21 | lowbust_arc_half_f | Formula('G13 / 2') | extracted | 18.69 |
| G22 | rib_arc_half_f | — | no recipe |  |
| G23 | waist_arc_half_f | Formula('G15 / 2') | extracted | 17.76 |
| G24 | highhip_arc_half_f | Formula('G16 / 2') | extracted | 19.55 |
| G25 | hip_arc_half_f | Formula('G17 / 2') | extracted | 23.03 |
| G26 | neck_arc_b | Formula('G02 - G10') | extracted | 17.92 |
| G27 | highbust_arc_b | Formula('G03 - G11') | extracted | 41.47 |
| G28 | bust_arc_b | Formula('G04 - G12') | extracted | 41.00 |
| G29 | lowbust_arc_b | Formula('G05 - G13') | extracted | 35.04 |
| G30 | rib_arc_b | — | no recipe |  |
| G31 | waist_arc_b | Formula('G07 - G15') | extracted | 29.79 |
| G32 | highhip_arc_b | Formula('G08 - G16') | extracted | 40.43 |
| G33 | hip_arc_b | Formula('G09 - G17') | extracted | 44.62 |
| G34 | neck_arc_half_b | Formula('G26 / 2') | extracted | 8.96 |
| G35 | highbust_arc_half_b | Formula('G27 / 2') | extracted | 20.74 |
| G36 | bust_arc_half_b | Formula('G28 / 2') | extracted | 20.50 |
| G37 | lowbust_arc_half_b | Formula('G29 / 2') | extracted | 17.52 |
| G38 | rib_arc_half_b | — | no recipe |  |
| G39 | waist_arc_half_b | Formula('G31 / 2') | extracted | 14.89 |
| G40 | highhip_arc_half_b | Formula('G32 / 2') | extracted | 20.22 |
| G41 | hip_arc_half_b | Formula('G33 / 2') | extracted | 22.31 |
| G42 | hip_with_abdomen_arc_f | — | skipped (hip_with_abdomen_arc_f — figure-shape dependent) |  |
| G43 | body_armfold_circ | — | no recipe |  |
| G44 | body_bust_circ | — | skipped (body_bust_circ — arms-included, pose dependent) |  |
| G45 | body_torso_circ | — | skipped (body_torso_circ — arms-included, pose dependent) |  |
| G46 | hip_circ_with_abdomen | — | no recipe |  |
| H01 | neck_front_to_waist_f | PolylineChord | extracted | 31.89 |
| H02 | neck_front_to_waist_flat_f | Geodesic | extracted | 32.15 |
| H03 | armpit_to_waist_side | Geodesic | extracted | 16.88 |
| H04 | shoulder_tip_to_waist_side_f | Geodesic | extracted | 32.06 |
| H05 | neck_side_to_waist_f | SurfacePlumbThenDrop | extracted | 38.49 |
| H06 | neck_side_to_waist_bustpoint_f | DiagonalSurfacePlumb | extracted | 38.77 |
| H07 | neck_front_to_highbust_f | SurfacePlumb | extracted | 14.55 |
| H08 | highbust_to_waist_f | Formula('H01 - H07') | extracted | -17.33 |
| H09 | neck_front_to_bust_f | SurfacePlumb | extracted | 18.64 |
| H10 | bust_to_waist_f | Formula('H01 - H09') | extracted | -13.24 |
| H11 | lowbust_to_waist_f | Geodesic | extracted | 7.47 |
| H12 | rib_to_waist_side | — | no recipe |  |
| H13 | shoulder_tip_to_armfold_f | Geodesic | extracted | 14.44 |
| H14 | neck_side_to_bust_f | SurfacePlumb | extracted | 24.46 |
| H15 | neck_side_to_highbust_f | SurfacePlumb | extracted | 17.34 |
| H16 | shoulder_center_to_highbust_f | DiagonalSurfacePlumb | extracted | 16.91 |
| H17 | shoulder_tip_to_waist_side_b | PolylineChord | extracted | 30.19 |
| H18 | neck_side_to_waist_b | SurfacePlumb | extracted | 42.85 |
| H19 | neck_back_to_waist_b | Geodesic | extracted | 33.74 |
| H20 | neck_side_to_waist_scapula_b | — | no recipe |  |
| H21 | neck_back_to_highbust_b | SurfacePlumb | extracted | 15.77 |
| H22 | highbust_to_waist_b | Formula('H19 - H21') | extracted | -17.97 |
| H23 | neck_back_to_bust_b | SurfacePlumb | extracted | 18.51 |
| H24 | bust_to_waist_b | Formula('H19 - H23') | extracted | -15.23 |
| H25 | lowbust_to_waist_b | SurfacePlumb | extracted | 17.16 |
| H26 | shoulder_tip_to_armfold_b | Geodesic | extracted | 16.83 |
| H27 | neck_side_to_bust_b | SurfacePlumb | extracted | 28.86 |
| H28 | neck_side_to_highbust_b | SurfacePlumb | extracted | 26.05 |
| H29 | shoulder_center_to_highbust_b | — | no recipe |  |
| H30 | waist_to_highhip_f | Geodesic | extracted | 11.61 |
| H31 | waist_to_hip_f | Geodesic | extracted | 19.57 |
| H32 | waist_to_highhip_side | Geodesic | extracted | 10.84 |
| H33 | waist_to_highhip_b | SurfacePlumb | extracted | 12.62 |
| H34 | waist_to_hip_b | SurfacePlumb | extracted | 21.47 |
| H35 | waist_to_hip_side | Geodesic | extracted | 20.73 |
| H36 | shoulder_slope_neck_side_angle | — | skipped (shoulder_slope_neck_side_angle — convention) |  |
| H37 | shoulder_slope_neck_side_length | VerticalDrop | extracted | 4.23 |
| H38 | shoulder_slope_neck_back_angle | — | skipped (shoulder_slope_neck_back_angle — convention) |  |
| H39 | shoulder_slope_neck_back_height | VerticalDrop | extracted | 3.18 |
| H40 | shoulder_slope_shoulder_tip_angle | — | skipped (shoulder_slope_shoulder_tip_angle — convention) |  |
| H41 | neck_back_to_across_back | SurfacePlumb | extracted | 16.83 |
| H42 | across_back_to_waist_b | Formula('H19 - H41') | extracted | 16.92 |
| I01 | shoulder_length | Geodesic | extracted | 11.04 |
| I02 | shoulder_tip_to_shoulder_tip_f | Geodesic | extracted | 33.52 |
| I03 | across_chest_f | Geodesic | extracted | 27.88 |
| I04 | armfold_to_armfold_f | Geodesic | extracted | 36.82 |
| I05 | shoulder_tip_to_shoulder_tip_half_f | Formula('I02 / 2') | extracted | 16.76 |
| I06 | across_chest_half_f | Formula('I03 / 2') | extracted | 13.94 |
| I07 | shoulder_tip_to_shoulder_tip_b | LandmarkChord | extracted | 32.26 |
| I08 | across_back_b | Geodesic | extracted | 31.54 |
| I09 | armfold_to_armfold_b | Geodesic | extracted | 30.60 |
| I10 | shoulder_tip_to_shoulder_tip_half_b | Formula('I07 / 2') | extracted | 16.13 |
| I11 | across_back_half_b | Formula('I08 / 2') | extracted | 15.77 |
| I12 | neck_front_to_shoulder_tip_f | Geodesic | extracted | 16.73 |
| I13 | neck_back_to_shoulder_tip_b | Geodesic | extracted | 18.13 |
| I14 | neck_width | LandmarkChord | extracted | 12.31 |
| J01 | bustpoint_to_bustpoint | LandmarkChord | extracted | 16.48 |
| J02 | bustpoint_to_neck_side | LandmarkChord | extracted | 23.99 |
| J03 | bustpoint_to_lowbust | Geodesic | extracted | 5.71 |
| J04 | bustpoint_to_waist | LandmarkChord | extracted | 14.30 |
| J05 | bustpoint_to_bustpoint_half | Formula('J01 / 2') | extracted | 8.24 |
| J06 | bustpoint_neck_side_to_waist | — | no recipe |  |
| J07 | bustpoint_to_shoulder_tip | LandmarkChord | extracted | 21.33 |
| J08 | bustpoint_to_waist_front | LandmarkChord | extracted | 16.12 |
| J09 | bustpoint_to_bustpoint_halter | — | no recipe |  |
| J10 | bustpoint_to_shoulder_center | LandmarkChord | extracted | 22.04 |
| J11 | bustpoint_to_neck_front | LandmarkChord | extracted | 20.00 |
| K01 | shoulder_tip_to_waist_front | DiagonalSurfacePlumb | extracted | 37.51 |
| K02 | neck_front_to_waist_side | DiagonalSurfacePlumb | extracted | 38.37 |
| K03 | neck_side_to_waist_side_f | DiagonalSurfacePlumb | extracted | 41.65 |
| K04 | shoulder_tip_to_waist_back | Geodesic | extracted | 37.84 |
| K05 | shoulder_tip_to_waist_b_1in_offset | — | no recipe |  |
| K06 | neck_back_to_waist_side | Geodesic | extracted | 38.76 |
| K07 | neck_side_to_waist_side_b | — | no recipe |  |
| K08 | neck_side_to_armfold_f | Geodesic | extracted | 20.86 |
| K09 | neck_side_to_armpit_f | Geodesic | extracted | 24.04 |
| K10 | neck_side_to_bust_side_f | Geodesic | extracted | 25.82 |
| K11 | neck_side_to_armfold_b | Geodesic | extracted | 23.15 |
| K12 | neck_side_to_armpit_b | — | no recipe |  |
| K13 | neck_side_to_bust_side_b | DiagonalSurfacePlumb | extracted | 30.30 |
| L01 | arm_shoulder_tip_to_wrist_bent | Geodesic | extracted | 57.01 |
| L02 | arm_shoulder_tip_to_elbow_bent | Geodesic | extracted | 32.32 |
| L03 | arm_elbow_to_wrist_bent | Formula('L05 - L06') | extracted | 24.68 |
| L04 | arm_elbow_circ_bent | LimbGirth | extracted | 23.61 |
| L05 | arm_shoulder_tip_to_wrist | Geodesic | extracted | 53.39 |
| L06 | arm_shoulder_tip_to_elbow | Geodesic | extracted | 31.22 |
| L07 | arm_elbow_to_wrist | Formula('L05 - L06') | extracted | 22.17 |
| L08 | arm_armpit_to_wrist | Geodesic | extracted | 44.56 |
| L09 | arm_armpit_to_elbow | Geodesic | extracted | 21.50 |
| L10 | arm_elbow_to_wrist_inside | Formula('L07') | extracted | 22.17 |
| L11 | arm_upper_circ | LimbGirth | extracted | 28.82 |
| L12 | arm_above_elbow_circ | — | no recipe |  |
| L13 | arm_elbow_circ | LimbGirth | extracted | 24.32 |
| L14 | arm_lower_circ | — | no recipe |  |
| L15 | arm_wrist_circ | LimbGirth | extracted | 14.98 |
| L16 | arm_shoulder_tip_to_armfold_line | Geodesic | extracted | 11.61 |
| L17 | arm_neck_side_to_wrist | — | no recipe |  |
| L18 | arm_neck_side_to_finger_tip | — | no recipe |  |
| L19 | armscye_circ | GeodesicLoop | extracted | 39.84 |
| L20 | armscye_length | — | no recipe |  |
| L21 | armscye_width | LandmarkChord | extracted | 12.36 |
| L22 | arm_neck_side_to_outer_elbow | — | no recipe |  |
| M01 | leg_crotch_to_floor | Height | extracted | 76.01 |
| M02 | leg_waist_side_to_floor | GeodesicThenDrop | extracted | 102.88 |
| M03 | leg_thigh_upper_circ | PlanarGirth | extracted | 54.49 |
| M04 | leg_thigh_mid_circ | — | no recipe |  |
| M05 | leg_knee_circ | PlanarGirth | extracted | 34.11 |
| M06 | leg_knee_small_circ | — | no recipe |  |
| M07 | leg_calf_circ | PlanarGirth | extracted | 33.92 |
| M08 | leg_ankle_high_circ | PlanarGirth | extracted | 20.43 |
| M09 | leg_ankle_circ | PlanarGirth | extracted | 24.68 |
| M10 | leg_knee_circ_bent | — | no recipe |  |
| M11 | leg_ankle_diag_circ | — | no recipe |  |
| M12 | leg_crotch_to_ankle | Formula('M01 - M08') | extracted | 55.59 |
| M13 | leg_waist_side_to_ankle | Formula('M02 - M08') | extracted | 82.45 |
| M14 | leg_waist_side_to_knee | — | no recipe |  |
| N01 | crotch_length | Geodesic | extracted | 69.32 |
| N02 | crotch_length_b | Geodesic | extracted | 36.79 |
| N03 | crotch_length_f | Formula('N01 - N02') | extracted | 32.53 |
| N04 | rise_length_side_sitting | — | skipped (rise_length_side_sitting — needs seated pose) |  |
| N05 | rise_length_diag | — | skipped (rise_length_diag — needs seated pose) |  |
| N06 | rise_length_b | Formula('N02') | extracted | 36.79 |
| N07 | rise_length_f | Formula('N03') | extracted | 32.53 |
| N08 | rise_length_side | Formula('A05 - M01') | extracted | 26.14 |
| O01 | neck_back_to_waist_front | Geodesic | extracted | 47.54 |
| O02 | waist_to_waist_halter | — | skipped (halter line — drafting convention) |  |
| O03 | waist_natural_circ | — | skipped (natural-waist definition open (SPEC §16)) |  |
| O04 | waist_natural_arc_f | — | skipped (natural-waist definition open) |  |
| O05 | waist_natural_arc_b | — | no recipe |  |
| O06 | waist_to_natural_waist_f | — | skipped (natural-waist definition open) |  |
| O07 | waist_to_natural_waist_b | — | skipped (natural-waist definition open) |  |
| O08 | arm_neck_back_to_elbow_bent | — | no recipe |  |
| O09 | arm_neck_back_to_wrist_bent | — | no recipe |  |
| O10 | arm_neck_side_to_elbow_bent | — | no recipe |  |
| O11 | arm_neck_side_to_wrist_bent | — | no recipe |  |
| O12 | arm_across_back_center_to_elbow_bent | — | no recipe |  |
| O13 | arm_across_back_center_to_wrist_bent | — | no recipe |  |
| O14 | arm_armscye_back_center_to_wrist_bent | — | no recipe |  |
| P01 | neck_back_to_bust_front | Geodesic | extracted | 34.03 |
| P02 | neck_back_to_armfold_front | Geodesic | extracted | 29.42 |
| P03 | neck_back_to_armfold_front_to_waist_side | Geodesic | extracted | 47.32 |
| P04 | highbust_back_over_shoulder_to_armfold_front | — | no recipe |  |
| P05 | highbust_back_over_shoulder_to_waist_front | — | no recipe |  |
| P06 | neck_back_to_armfold_front_to_neck_back | — | no recipe |  |
| P07 | across_back_center_to_armfold_front_to_across_back_center | — | no recipe |  |
| P08 | neck_back_to_armfold_front_to_highbust_back | — | no recipe |  |
| P09 | armfold_to_armfold_bust | Geodesic | extracted | 38.85 |
| P10 | armfold_to_bust_front | Geodesic | extracted | 13.34 |
| P11 | highbust_b_over_shoulder_to_highbust_f | — | no recipe |  |
| P12 | armscye_arc | Geodesic | extracted | 22.55 |
| Q01 | dart_width_shoulder | — | skipped (dart_width_shoulder — size chart) |  |
| Q02 | dart_width_bust | — | skipped (dart_width_bust — aldrich_size_chart_p13.yaml) |  |
| Q03 | dart_width_waist | — | skipped (dart_width_waist — size chart) |  |
