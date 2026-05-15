# SeamlyME Measurement Reference

Extracted from [Seamly2D](https://github.com/fashionfreedom/seamly2d) codebase (`develop` branch, commit `8b6bc512a9`).

## Directory Structure

```
references/seamly/
├── schema/
│   ├── individual_measurements_v0.3.4.xsd   # .smis file schema (latest)
│   └── multisize_measurements_v0.4.5.xsd    # .smms file schema (latest)
├── diagrams/                                 # 107 SVG body measurement diagrams
│   ├── measurement-body-diagram.svg          # Full body overview (all measurements)
│   ├── measurement-body-points.svg           # Body landmark points
│   ├── Ap1.svg .. Qp3.svg                    # Per-group measurement diagrams
│   └── custom.svg                            # Custom measurement placeholder
├── samples/
│   ├── all_measurements_template.smis        # All 262 measurements with formulas
│   ├── aldrich_women_template.smis           # Aldrich system template
│   ├── trousers.smis                         # Example: trousers
│   └── male_shirt.smis                       # Example: male shirt
└── docs/
    └── all_measurements_with_descriptions.pdf  # Visual guide with descriptions
```

## SMIS File Format (Individual Measurements)

XML file, root element `<smis>`, validated by `individual_measurements_v0.3.4.xsd`.

### Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<smis>
    <version>0.3.4</version>
    <read-only>false</read-only>
    <notes/>                              <!-- optional -->
    <unit>cm</unit>                       <!-- mm | cm | inch -->
    <pm_system>998</pm_system>            <!-- 0-54 or 998 (none) -->
    <personal>
        <family-name/>
        <given-name/>
        <birth-date>1800-01-01</birth-date>
        <gender>unknown</gender>          <!-- unknown | male | female -->
        <email/>
    </personal>
    <body-measurements>
        <m name="height" value="170"/>
        <m name="bust_circ" value="92.5"/>
        <m name="arm_elbow_to_wrist" value="(arm_shoulder_tip_to_wrist - arm_shoulder_tip_to_elbow)"/>
        <!-- value can be a number or a formula referencing other measurements -->
    </body-measurements>
</smis>
```

### Measurement `<m>` Attributes

| Attribute     | Required | Description |
|---------------|----------|-------------|
| `name`        | yes      | Unique identifier (snake_case, no spaces/operators) |
| `value`       | yes      | Numeric value or formula string |
| `full_name`   | no       | Display name |
| `description` | no       | Description text |

### Name Validation Regex

```
([^\p{Nd}\p{Zs}*/&|!<>^\-()–+−=?:;'\\"]){1,1}([^\p{Zs}*/&|!<>^\-()–+−=?:;\\"]){0,}
```

First character: no digits, no spaces, no operators. Subsequent: digits allowed, still no spaces/operators.

## SMMS File Format (Multisize Measurements)

Root element `<smms>`. Same structure as SMIS but adds grading:

- `<size base="44"/>` — base size (22–72 in cm, 220–720 in mm)
- `<height base="170"/>` — base height (50–200 in cm, 500–2000 in mm)
- Each `<m>` has `base`, `height_increase`, `size_increase` (doubles) instead of `value`

## Complete Measurement Catalog (262 measurements, 17 groups)

### Group A — Heights (23 measurements → Ap1, Ap2)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| A01 | `height` | Ap1 | no |
| A02 | `height_neck_back` | Ap1 | no |
| A03 | `height_scapula` | Ap1 | no |
| A04 | `height_armpit` | Ap1 | no |
| A05 | `height_waist_side` | Ap1 | no |
| A06 | `height_hip` | Ap1 | no |
| A07 | `height_gluteal_fold` | Ap1 | no |
| A08 | `height_knee` | Ap1 | no |
| A09 | `height_calf` | Ap1 | no |
| A10 | `height_ankle_high` | Ap1 | no |
| A11 | `height_ankle` | Ap1 | no |
| A12 | `height_highhip` | Ap1 | no |
| A13 | `height_waist_front` | Ap1 | no |
| A14 | `height_bustpoint` | Ap1 | no |
| A15 | `height_shoulder_tip` | Ap1 | no |
| A16 | `height_neck_front` | Ap1 | no |
| A17 | `height_neck_side` | Ap1 | no |
| A18 | `height_neck_back_to_knee` | Ap2 | yes: `height_neck_back - height_knee` |
| A19 | `height_waist_side_to_knee` | Ap2 | yes: `height_waist_side - height_knee` |
| A20 | `height_waist_side_to_hip` | Ap2 | yes: `height_waist_side - height_hip` |
| A21 | `height_knee_to_ankle` | Ap2 | yes: `height_knee - height_ankle` |
| A22 | `height_neck_back_to_waist_side` | Ap2 | yes: `height_neck_back - height_waist_side` |
| A23 | `height_waist_back` | Ap2 | yes: `height_waist_front - leg_crotch_to_floor` |

### Group B — Widths (5 measurements → Bp1, Bp2)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| B01 | `width_shoulder` | Bp1 | no |
| B02 | `width_bust` | Bp1 | no |
| B03 | `width_waist` | Bp1 | no |
| B04 | `width_hip` | Bp1 | no |
| B05 | `width_abdomen_to_hip` | Bp2 | no |

### Group C — Indents (3 measurements → Cp1, Cp2)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| C01 | `indent_neck_back` | Cp1 | no |
| C02 | `indent_waist_back` | Cp2 | no |
| C03 | `indent_ankle_high` | Cp2 | no |

### Group D — Hand (5 measurements → Dp1, Dp2, Dp3)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| D01 | `hand_palm_length` | Dp1 | no |
| D02 | `hand_length` | Dp1 | no |
| D03 | `hand_palm_width` | Dp1 | no |
| D04 | `hand_palm_circ` | Dp2 | no |
| D05 | `hand_circ` | Dp3 | no |

### Group E — Foot (4 measurements → Ep1, Ep2)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| E01 | `foot_width` | Ep1 | no |
| E02 | `foot_length` | Ep2 | no |
| E03 | `foot_circ` | Ep2 | no |
| E04 | `foot_instep_circ` | Ep2 | no |

### Group F — Head (6 measurements → Fp1, Fp2, Fp3)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| F01 | `head_circ` | Fp1 | no |
| F02 | `head_length` | Fp1 | no |
| F03 | `head_depth` | Fp1 | no |
| F04 | `head_width` | Fp2 | no |
| F05 | `head_crown_to_neck_back` | Fp3 | yes: `height - height_neck_back` |
| F06 | `head_chin_to_neck_back` | Fp3 | yes: `height - height_neck_back - head_length` |

### Group G — Circumferences & Arcs (46 measurements → Gp1–Gp9)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| G01 | `neck_mid_circ` | Gp1 | no |
| G02 | `neck_circ` | Gp1 | no |
| G03 | `highbust_circ` | Gp1 | no |
| G04 | `bust_circ` | Gp1 | no |
| G05 | `lowbust_circ` | Gp1 | no |
| G06 | `rib_circ` | Gp1 | no |
| G07 | `waist_circ` | Gp1 | no |
| G08 | `highhip_circ` | Gp1 | no |
| G09 | `hip_circ` | Gp1 | no |
| G10 | `neck_arc_f` | Gp2 | no |
| G11 | `highbust_arc_f` | Gp2 | no |
| G12 | `bust_arc_f` | Gp2 | no |
| G13 | `lowbust_arc_f` | Gp2 | no |
| G14 | `rib_arc_f` | Gp2 | no |
| G15 | `waist_arc_f` | Gp2 | no |
| G16 | `highhip_arc_f` | Gp2 | no |
| G17 | `hip_arc_f` | Gp2 | no |
| G18 | `neck_arc_half_f` | Gp3 | yes: `neck_arc_f/2` |
| G19 | `highbust_arc_half_f` | Gp3 | yes: `highbust_arc_f/2` |
| G20 | `bust_arc_half_f` | Gp3 | yes: `bust_arc_f/2` |
| G21 | `lowbust_arc_half_f` | Gp3 | yes: `lowbust_arc_f/2` |
| G22 | `rib_arc_half_f` | Gp3 | yes: `rib_arc_f/2` |
| G23 | `waist_arc_half_f` | Gp3 | yes: `waist_arc_f/2` |
| G24 | `highhip_arc_half_f` | Gp3 | yes: `highhip_arc_f/2` |
| G25 | `hip_arc_half_f` | Gp3 | yes: `hip_arc_f/2` |
| G26 | `neck_arc_b` | Gp4 | yes: `neck_circ - neck_arc_f` |
| G27 | `highbust_arc_b` | Gp4 | yes: `highbust_circ - highbust_arc_f` |
| G28 | `bust_arc_b` | Gp4 | yes: `bust_circ - bust_arc_f` |
| G29 | `lowbust_arc_b` | Gp4 | yes: `lowbust_circ - lowbust_arc_f` |
| G30 | `rib_arc_b` | Gp4 | yes: `rib_circ - rib_arc_f` |
| G31 | `waist_arc_b` | Gp4 | yes: `waist_circ - waist_arc_f` |
| G32 | `highhip_arc_b` | Gp4 | yes: `highhip_circ - highhip_arc_f` |
| G33 | `hip_arc_b` | Gp4 | yes: `hip_circ - hip_arc_f` |
| G34 | `neck_arc_half_b` | Gp5 | yes: `neck_arc_b/2` |
| G35 | `highbust_arc_half_b` | Gp5 | yes: `highbust_arc_b/2` |
| G36 | `bust_arc_half_b` | Gp5 | yes: `bust_arc_b/2` |
| G37 | `lowbust_arc_half_b` | Gp5 | yes: `lowbust_arc_b/2` |
| G38 | `rib_arc_half_b` | Gp5 | yes: `rib_arc_b/2` |
| G39 | `waist_arc_half_b` | Gp5 | yes: `waist_arc_b/2` |
| G40 | `highhip_arc_half_b` | Gp5 | yes: `highhip_arc_b/2` |
| G41 | `hip_arc_half_b` | Gp5 | yes: `hip_arc_b/2` |
| G42 | `hip_with_abdomen_arc_f` | Gp6 | no |
| G43 | `body_armfold_circ` | Gp7 | no |
| G44 | `body_bust_circ` | Gp7 | no |
| G45 | `body_torso_circ` | Gp8 | no |
| G46 | `hip_circ_with_abdomen` | Gp9 | yes: `hip_arc_b + hip_with_abdomen_arc_f` |

### Group H — Vertical Distances Front & Back (42 measurements → Hp1–Hp13)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| H01 | `neck_front_to_waist_f` | Hp1 | no |
| H02 | `neck_front_to_waist_flat_f` | Hp2 | no |
| H03 | `armpit_to_waist_side` | Hp3 | no |
| H04 | `shoulder_tip_to_waist_side_f` | Hp3 | no |
| H05 | `neck_side_to_waist_f` | Hp3 | no |
| H06 | `neck_side_to_waist_bustpoint_f` | Hp3 | no |
| H07 | `neck_front_to_highbust_f` | Hp4 | no |
| H08 | `highbust_to_waist_f` | Hp4 | yes: `neck_front_to_waist_f - neck_front_to_highbust_f` |
| H09 | `neck_front_to_bust_f` | Hp4 | no |
| H10 | `bust_to_waist_f` | Hp4 | yes: `neck_front_to_waist_f - neck_front_to_bust_f` |
| H11 | `lowbust_to_waist_f` | Hp4 | no |
| H12 | `rib_to_waist_side` | Hp4 | no |
| H13 | `shoulder_tip_to_armfold_f` | Hp5 | no |
| H14 | `neck_side_to_bust_f` | Hp5 | no |
| H15 | `neck_side_to_highbust_f` | Hp5 | no |
| H16 | `shoulder_center_to_highbust_f` | Hp5 | no |
| H17 | `shoulder_tip_to_waist_side_b` | Hp6 | no |
| H18 | `neck_side_to_waist_b` | Hp6 | no |
| H19 | `neck_back_to_waist_b` | Hp6 | no |
| H20 | `neck_side_to_waist_scapula_b` | Hp6 | no |
| H21 | `neck_back_to_highbust_b` | Hp7 | no |
| H22 | `highbust_to_waist_b` | Hp7 | yes: `neck_back_to_waist_b - neck_back_to_highbust_b` |
| H23 | `neck_back_to_bust_b` | Hp7 | no |
| H24 | `bust_to_waist_b` | Hp7 | yes: `neck_back_to_waist_b - neck_back_to_bust_b` |
| H25 | `lowbust_to_waist_b` | Hp7 | no |
| H26 | `shoulder_tip_to_armfold_b` | Hp8 | no |
| H27 | `neck_side_to_bust_b` | Hp8 | no |
| H28 | `neck_side_to_highbust_b` | Hp8 | no |
| H29 | `shoulder_center_to_highbust_b` | Hp8 | no |
| H30 | `waist_to_highhip_f` | Hp9 | no |
| H31 | `waist_to_hip_f` | Hp9 | no |
| H32 | `waist_to_highhip_side` | Hp9 | no |
| H33 | `waist_to_highhip_b` | Hp10 | no |
| H34 | `waist_to_hip_b` | Hp10 | no |
| H35 | `waist_to_hip_side` | Hp10 | no |
| H36 | `shoulder_slope_neck_side_angle` | Hp11 | no |
| H37 | `shoulder_slope_neck_side_length` | Hp11 | no |
| H38 | `shoulder_slope_neck_back_angle` | Hp11 | no |
| H39 | `shoulder_slope_neck_back_height` | Hp11 | no |
| H40 | `shoulder_slope_shoulder_tip_angle` | Hp12 | no |
| H41 | `neck_back_to_across_back` | Hp13 | no |
| H42 | `across_back_to_waist_b` | Hp13 | yes: `neck_back_to_waist_b - neck_back_to_across_back` |

### Group I — Shoulder & Across (14 measurements → Ip1–Ip7)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| I01 | `shoulder_length` | Ip1 | no |
| I02 | `shoulder_tip_to_shoulder_tip_f` | Ip1 | no |
| I03 | `across_chest_f` | Ip1 | no |
| I04 | `armfold_to_armfold_f` | Ip1 | no |
| I05 | `shoulder_tip_to_shoulder_tip_half_f` | Ip2 | yes: `shoulder_tip_to_shoulder_tip_f/2` |
| I06 | `across_chest_half_f` | Ip2 | yes: `across_chest_f/2` |
| I07 | `shoulder_tip_to_shoulder_tip_b` | Ip3 | no |
| I08 | `across_back_b` | Ip3 | no |
| I09 | `armfold_to_armfold_b` | Ip3 | no |
| I10 | `shoulder_tip_to_shoulder_tip_half_b` | Ip4 | yes: `shoulder_tip_to_shoulder_tip_b/2` |
| I11 | `across_back_half_b` | Ip4 | yes: `across_back_b/2` |
| I12 | `neck_front_to_shoulder_tip_f` | Ip5 | no |
| I13 | `neck_back_to_shoulder_tip_b` | Ip6 | no |
| I14 | `neck_width` | Ip7 | no |

### Group J — Bustpoint (11 measurements → Jp1–Jp6)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| J01 | `bustpoint_to_bustpoint` | Jp1 | no |
| J02 | `bustpoint_to_neck_side` | Jp1 | no |
| J03 | `bustpoint_to_lowbust` | Jp1 | no |
| J04 | `bustpoint_to_waist` | Jp1 | no |
| J05 | `bustpoint_to_bustpoint_half` | Jp2 | yes: `bustpoint_to_bustpoint/2` |
| J06 | `bustpoint_neck_side_to_waist` | Jp3 | yes: `bustpoint_to_neck_side + bustpoint_to_waist` |
| J07 | `bustpoint_to_shoulder_tip` | Jp4 | no |
| J08 | `bustpoint_to_waist_front` | Jp4 | no |
| J09 | `bustpoint_to_bustpoint_halter` | Jp5 | no |
| J10 | `bustpoint_to_shoulder_center` | Jp6 | no |
| J11 | `bustpoint_to_neck_front` | Jp6 | no |

### Group K — Shoulder-to-Waist & Neck-to-Side Paths (13 measurements → Kp1–Kp11)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| K01 | `shoulder_tip_to_waist_front` | Kp1 | no |
| K02 | `neck_front_to_waist_side` | Kp2 | no |
| K03 | `neck_side_to_waist_side_f` | Kp2 | no |
| K04 | `shoulder_tip_to_waist_back` | Kp3 | no |
| K05 | `shoulder_tip_to_waist_b_1in_offset` | Kp4 | no |
| K06 | `neck_back_to_waist_side` | Kp5 | no |
| K07 | `neck_side_to_waist_side_b` | Kp5 | no |
| K08 | `neck_side_to_armfold_f` | Kp6 | no |
| K09 | `neck_side_to_armpit_f` | Kp7 | no |
| K10 | `neck_side_to_bust_side_f` | Kp8 | no |
| K11 | `neck_side_to_armfold_b` | Kp9 | no |
| K12 | `neck_side_to_armpit_b` | Kp10 | no |
| K13 | `neck_side_to_bust_side_b` | Kp11 | no |

### Group L — Arm (22 measurements → Lp1–Lp10)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| L01 | `arm_shoulder_tip_to_wrist_bent` | Lp1 | no |
| L02 | `arm_shoulder_tip_to_elbow_bent` | Lp1 | no |
| L03 | `arm_elbow_to_wrist_bent` | Lp1 | yes: `arm_shoulder_tip_to_wrist_bent - arm_shoulder_tip_to_elbow_bent` |
| L04 | `arm_elbow_circ_bent` | Lp1 | no |
| L05 | `arm_shoulder_tip_to_wrist` | Lp2 | no |
| L06 | `arm_shoulder_tip_to_elbow` | Lp2 | no |
| L07 | `arm_elbow_to_wrist` | Lp2 | yes: `arm_shoulder_tip_to_wrist - arm_shoulder_tip_to_elbow` |
| L08 | `arm_armpit_to_wrist` | Lp3 | no |
| L09 | `arm_armpit_to_elbow` | Lp3 | no |
| L10 | `arm_elbow_to_wrist_inside` | Lp3 | yes: `arm_armpit_to_wrist - arm_armpit_to_elbow` |
| L11 | `arm_upper_circ` | Lp4 | no |
| L12 | `arm_above_elbow_circ` | Lp4 | no |
| L13 | `arm_elbow_circ` | Lp4 | no |
| L14 | `arm_lower_circ` | Lp4 | no |
| L15 | `arm_wrist_circ` | Lp4 | no |
| L16 | `arm_shoulder_tip_to_armfold_line` | Lp5 | no |
| L17 | `arm_neck_side_to_wrist` | Lp6 | yes: `shoulder_length + arm_shoulder_tip_to_wrist` |
| L18 | `arm_neck_side_to_finger_tip` | Lp7 | yes: `shoulder_length + arm_shoulder_tip_to_wrist + hand_length` |
| L19 | `armscye_circ` | Lp8 | no |
| L20 | `armscye_length` | Lp8 | no |
| L21 | `armscye_width` | Lp9 | no |
| L22 | `arm_neck_side_to_outer_elbow` | Lp10 | yes: `shoulder_length + arm_shoulder_tip_to_elbow` |

### Group M — Leg (14 measurements → Mp1–Mp3)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| M01 | `leg_crotch_to_floor` | Mp1 | no |
| M02 | `leg_waist_side_to_floor` | Mp1 | no |
| M03 | `leg_thigh_upper_circ` | Mp2 | no |
| M04 | `leg_thigh_mid_circ` | Mp2 | no |
| M05 | `leg_knee_circ` | Mp2 | no |
| M06 | `leg_knee_small_circ` | Mp2 | no |
| M07 | `leg_calf_circ` | Mp2 | no |
| M08 | `leg_ankle_high_circ` | Mp2 | no |
| M09 | `leg_ankle_circ` | Mp2 | no |
| M10 | `leg_knee_circ_bent` | Mp2 | no |
| M11 | `leg_ankle_diag_circ` | Mp2 | no |
| M12 | `leg_crotch_to_ankle` | Mp3 | yes: `leg_crotch_to_floor - height_ankle` |
| M13 | `leg_waist_side_to_ankle` | Mp3 | yes: `leg_waist_side_to_floor - height_ankle` |
| M14 | `leg_waist_side_to_knee` | Mp3 | yes: `leg_waist_side_to_floor - height_knee` |

### Group N — Crotch & Rise (8 measurements → Np1–Np5)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| N01 | `crotch_length` | Np1 | no |
| N02 | `crotch_length_b` | Np2 | no |
| N03 | `crotch_length_f` | Np2 | yes: `crotch_length - crotch_length_b` |
| N04 | `rise_length_side_sitting` | Np3 | no |
| N05 | `rise_length_diag` | Np3 | no |
| N06 | `rise_length_b` | Np4 | yes: `height_waist_back - leg_crotch_to_floor` |
| N07 | `rise_length_f` | Np4 | yes: `height_waist_front - leg_crotch_to_floor` |
| N08 | `rise_length_side` | Np5 | no |

### Group O — Natural Waist & Arm Extensions (14 measurements → Op1–Op11)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| O01 | `neck_back_to_waist_front` | Op1 | no |
| O02 | `waist_to_waist_halter` | Op2 | no |
| O03 | `waist_natural_circ` | Op3 | no |
| O04 | `waist_natural_arc_f` | Op4 | no |
| O05 | `waist_natural_arc_b` | Op5 | yes: `waist_natural_circ - waist_natural_arc_f` |
| O06 | `waist_to_natural_waist_f` | Op6 | no |
| O07 | `waist_to_natural_waist_b` | Op7 | no |
| O08 | `arm_neck_back_to_elbow_bent` | Op8 | no |
| O09 | `arm_neck_back_to_wrist_bent` | Op8 | no |
| O10 | `arm_neck_side_to_elbow_bent` | Op9 | no |
| O11 | `arm_neck_side_to_wrist_bent` | Op9 | no |
| O12 | `arm_across_back_center_to_elbow_bent` | Op10 | no |
| O13 | `arm_across_back_center_to_wrist_bent` | Op10 | no |
| O14 | `arm_armscye_back_center_to_wrist_bent` | Op11 | no |

### Group P — Complex Torso Paths (12 measurements → Pp1–Pp12)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| P01 | `neck_back_to_bust_front` | Pp1 | no |
| P02 | `neck_back_to_armfold_front` | Pp2 | no |
| P03 | `neck_back_to_armfold_front_to_waist_side` | Pp3 | no |
| P04 | `highbust_back_over_shoulder_to_armfold_front` | Pp4 | no |
| P05 | `highbust_back_over_shoulder_to_waist_front` | Pp5 | no |
| P06 | `neck_back_to_armfold_front_to_neck_back` | Pp6 | no |
| P07 | `across_back_center_to_armfold_front_to_across_back_center` | Pp7 | no |
| P08 | `neck_back_to_armfold_front_to_highbust_back` | Pp8 | no |
| P09 | `armfold_to_armfold_bust` | Pp9 | no |
| P10 | `armfold_to_bust_front` | Pp10 | no |
| P11 | `highbust_b_over_shoulder_to_highbust_f` | Pp11 | no |
| P12 | `armscye_arc` | Pp12 | no |

### Group Q — Dart Widths (3 measurements → Qp1–Qp3)

| Code | SMIS Name | Diagram | Computed |
|------|-----------|---------|----------|
| Q01 | `dart_width_shoulder` | Qp1 | no |
| Q02 | `dart_width_bust` | Qp2 | no |
| Q03 | `dart_width_waist` | Qp3 | no |

## Source Files in Seamly2D

| What | Path |
|------|------|
| Individual XSD (all versions) | `src/libs/ifc/schema/individual_size_measurements/` |
| Multisize XSD (all versions) | `src/libs/ifc/schema/multi_size_measurements/` |
| Diagram SVGs | `src/libs/vmisc/share/resources/diagrams/` |
| Body overview SVGs | `share/img/measurement-body-*.svg` |
| Measurement definitions | `src/libs/vpatterndb/measurements_def.h` / `.cpp` |
| Diagram mapping function | `src/libs/vpatterndb/measurements_def.cpp:710` (`MapDiagrams()`) |
| Sample templates | `src/app/share/samples/measurements/` |
| PDF guide | `share/all_measurements_with_descriptions.pdf` |

## Notes

- G12 (`bust_arc_f`) has synonym `size` in Seamly2D source code
- `pm_system` values 0–54 correspond to predefined pattern-making systems; 998 = none
- Multisize heights support both cm (50–200) and mm (500–2000) ranges
- Multisize sizes support both cm (22–72) and mm (220–720) ranges
- Formula-computed measurements can reference any other measurement by its SMIS name
