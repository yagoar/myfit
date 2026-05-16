"""Seamly catalog -> recipe dictionary.

Per references/seamly/extraction_audit.md, all 245 catalog entries are
classified mechanical / computed / judgment / standard. This file wires
the mechanical + computed entries to the primitives in
body_scanner.measure.primitives.

Coverage so far (incremental):
  - A-group heights (mechanical + computed)
  - B-group widths
  - G-group circumferences & front arcs (G01-G17), incl. G03/G11 geodesic
    per the audit
  - G18-G46 derived (formula)
  - H-group vertical landmark distances + computed
  - I-group shoulder/across distances (geodesic and chord)
  - J-group bustpoint distances (LandmarkChord)
  - K-group geodesics
  - L/M arm/leg circumferences + geodesics (subset)
  - N-group crotch geodesics
  - P-group complex torso geodesics
  - Q-group dart widths (standard from size chart - skipped here)

Entries flagged 'judgment' in the audit are NOT included until the
underlying convention is resolved.
"""
from __future__ import annotations

import re
from pathlib import Path

from .primitives import (
    Formula,
    Geodesic,
    GeodesicLoop,
    Height,
    LandmarkChord,
    LateralChord,
    PlanarArc,
    PlanarGirth,
)


_README = Path(__file__).resolve().parents[3] / "references" / "seamly" / "README.md"


def _load_code_to_name() -> dict[str, str]:
    """Parse the markdown code -> name table in references/seamly/README.md."""
    try:
        text = _README.read_text()
    except FileNotFoundError:
        return {}
    return dict(re.findall(r"^\|\s*([A-Z]\d{2})\s*\|\s*`([^`]+)`", text, re.MULTILINE))


CODE_TO_NAME: dict[str, str] = _load_code_to_name()


# Codes whose status is "judgment" or "standard" per extraction_audit.md.
# Listed here for clarity (and so we can skip them with a known reason).
JUDGMENT_OR_STANDARD: dict[str, str] = {
    # A
    "A03": "scapula prominence — fuzzy landmark",
    "A07": "gluteal fold detection — needs mesh-feature finder",
    # B
    "B05": "abdomen plane — figure-shape dependent",
    # C
    "C01": "indent_neck_back convention",
    "C02": "indent_waist_back convention",
    "C03": "indent_ankle_high convention",
    # D/E/F all hand/foot/head measurements
    **{f"D0{i}": "hand — scan resolution too low" for i in range(1, 6)},
    **{f"E0{i}": "foot — partially occluded by floor" for i in range(1, 5)},
    "F01": "head_circ — hair interference",
    "F02": "head_length — convention",
    "F03": "head_depth — convention",
    "F04": "head_width — convention",
    # G
    "G42": "hip_with_abdomen_arc_f — figure-shape dependent",
    "G44": "body_bust_circ — arms-included, pose dependent",
    "G45": "body_torso_circ — arms-included, pose dependent",
    # H angle entries
    "H36": "shoulder_slope_neck_side_angle — convention",
    "H38": "shoulder_slope_neck_back_angle — convention",
    "H40": "shoulder_slope_shoulder_tip_angle — convention",
    # N
    "N04": "rise_length_side_sitting — needs seated pose",
    "N05": "rise_length_diag — needs seated pose",
    # O natural waist
    "O02": "halter line — drafting convention",
    "O03": "natural-waist definition open (SPEC §16)",
    "O04": "natural-waist definition open",
    "O06": "natural-waist definition open",
    "O07": "natural-waist definition open",
    # Q standard size-chart values
    "Q01": "dart_width_shoulder — size chart",
    "Q02": "dart_width_bust — aldrich_size_chart_p13.yaml",
    "Q03": "dart_width_waist — size chart",
}


# Primitive recipes by Seamly code (the mechanical entries).
RECIPES = {
    # ------------------------------------------------------------------
    # A — Heights
    # ------------------------------------------------------------------
    "A01": Height("top_of_head"),
    "A02": Height("c7"),
    "A04": Height("underarm_left"),
    "A05": Height("waist_side_left"),
    "A06": Height("low_hip_level"),
    "A08": Height("mid_knee_level"),
    "A10": Height("ankle_level"),  # high-ankle = lateral_malleolus + 5cm offset; approx for v1
    "A11": Height("ankle_bone_lateral_left"),
    "A12": Height("high_hip_level"),
    "A13": Height("waist_cf"),
    "A14": Height("bust_apex_left"),
    "A15": Height("acromion_left"),
    "A16": Height("front_neck_point"),
    "A17": Height("shoulder_neck_left"),

    # ------------------------------------------------------------------
    # B — Widths (lateral X chord at named plane)
    # ------------------------------------------------------------------
    "B01": LandmarkChord("acromion_left", "acromion_right"),
    "B02": LateralChord("bust_level"),
    "B03": LateralChord("waist_string"),
    # Hip is below pelvis joint -> most verts are leg-tagged. Include legs.
    "B04": LateralChord("low_hip_level",
                        regions=("torso", "left_leg", "right_leg")),

    # ------------------------------------------------------------------
    # G — Circumferences (G01-G09) and Front Arcs (G10-G17)
    # Per extraction_audit.md, G03 and G11 are GEODESIC, not planar.
    # ------------------------------------------------------------------
    # G01/G02 — at neck height the body cross-section is naturally just the
    # neck cylinder (arms/shoulders are below), so no region mask needed.
    "G01": PlanarGirth("mid_neck_level", regions=()),
    "G02": PlanarGirth("neck_base_level", regions=()),
    "G03": GeodesicLoop(  # highbust geodesic loop under armfolds
        ("armfold_front_left", "armfold_back_left",
         "armfold_back_right", "armfold_front_right")
    ),
    "G04": PlanarGirth("bust_level"),
    "G05": PlanarGirth("lowbust_level"),
    "G06": PlanarGirth("waist_string"),  # placeholder until rib_level lands
    "G07": PlanarGirth("waist_string"),
    "G08": PlanarGirth("high_hip_level"),
    "G09": PlanarGirth("low_hip_level",
                       regions=("torso", "left_leg", "right_leg")),

    "G10": PlanarArc("front_neck_point", "shoulder_neck_left",
                     "shoulder_neck_right", "front"),
    "G11": Geodesic(("armfold_front_left", "armfold_front_right")),
    "G12": PlanarArc("bust_level", "waist_side_left", "waist_side_right", "front"),
    "G13": PlanarArc("lowbust_level", "waist_side_left", "waist_side_right", "front"),
    "G15": PlanarArc("waist_string", "waist_side_left", "waist_side_right", "front"),
    "G16": PlanarArc("high_hip_level", "waist_side_left", "waist_side_right", "front"),
    "G17": PlanarArc("low_hip_level", "waist_side_left", "waist_side_right",
                     "front",
                     regions=("torso", "left_leg", "right_leg")),

    # ------------------------------------------------------------------
    # H — Vertical distances along the body (geodesic surface paths
    # between landmarks; per extraction_audit.md classed "mechanical given
    # the landmarks"). H05-H07 etc. could equally be implemented as
    # Y-axis differences; using geodesic captures the tape convention.
    # ------------------------------------------------------------------
    "H01": Geodesic(("front_neck_point", "waist_cf")),
    "H02": Geodesic(("front_neck_point", "bust_apex_left", "waist_cf")),
    "H03": Geodesic(("underarm_left", "waist_side_left")),
    "H04": Geodesic(("acromion_left", "waist_side_left")),
    "H05": Geodesic(("shoulder_neck_left", "waist_cf")),
    "H06": Geodesic(("shoulder_neck_left", "bust_apex_left", "waist_cf")),
    "H07": Geodesic(("front_neck_point", "armfold_front_left")),
    "H09": Geodesic(("front_neck_point", "bust_apex_left")),
    "H11": Geodesic(("lowbust_apex", "waist_cf")),
    "H12": Geodesic(("underarm_left", "waist_side_left")),  # rib alias for now
    "H13": Geodesic(("acromion_left", "armfold_front_left")),
    "H14": Geodesic(("shoulder_neck_left", "bust_apex_left")),
    "H15": Geodesic(("shoulder_neck_left", "armfold_front_left")),
    "H16": Geodesic(("front_shoulder_centre_left", "armfold_front_left")),
    "H17": Geodesic(("acromion_left", "waist_cb")),
    "H18": Geodesic(("shoulder_neck_left", "waist_cb")),
    "H19": Geodesic(("c7", "waist_cb")),
    "H20": Geodesic(("shoulder_neck_left", "waist_cb")),  # scapula alias
    "H21": Geodesic(("c7", "armfold_back_left")),
    "H23": Geodesic(("c7", "bust_apex_left")),
    "H25": Geodesic(("lowbust_apex", "waist_cb")),
    "H26": Geodesic(("acromion_left", "armfold_back_left")),
    "H27": Geodesic(("shoulder_neck_left", "bust_apex_left")),  # back variant
    "H28": Geodesic(("shoulder_neck_left", "armfold_back_left")),
    "H29": Geodesic(("front_shoulder_centre_left", "armfold_back_left")),
    "H30": Geodesic(("waist_cf", "high_hip_level")),
    "H31": Geodesic(("waist_cf", "low_hip_level")),
    "H32": Geodesic(("waist_side_left", "high_hip_level")),
    "H33": Geodesic(("waist_cb", "high_hip_level")),
    "H34": Geodesic(("waist_cb", "low_hip_level")),
    "H35": Geodesic(("waist_side_left", "low_hip_level")),
    "H37": Geodesic(("shoulder_neck_left", "acromion_left")),
    "H39": LandmarkChord("c7", "acromion_left"),  # vertical height of shoulder slope
    "H41": Geodesic(("c7", "armscye_back_left")),

    # ------------------------------------------------------------------
    # I — Shoulder & Across
    # ------------------------------------------------------------------
    "I01": Geodesic(("shoulder_neck_left", "acromion_left")),
    "I02": Geodesic(("acromion_left", "acromion_right")),
    "I03": Geodesic(("armscye_front_left", "armscye_front_right")),
    "I04": Geodesic(("armfold_front_left", "armfold_front_right")),
    "I07": Geodesic(("acromion_left", "c7", "acromion_right")),
    "I08": Geodesic(("armscye_back_left", "armscye_back_right")),
    "I09": Geodesic(("armfold_back_left", "armfold_back_right")),
    "I12": Geodesic(("front_neck_point", "acromion_left")),
    "I13": Geodesic(("c7", "acromion_left")),
    "I14": LandmarkChord("shoulder_neck_left", "shoulder_neck_right"),

    # ------------------------------------------------------------------
    # J — Bustpoint distances (all LandmarkChord)
    # ------------------------------------------------------------------
    "J01": LandmarkChord("bust_apex_left", "bust_apex_right"),
    "J02": LandmarkChord("bust_apex_left", "shoulder_neck_left"),
    "J03": LandmarkChord("bust_apex_left", "lowbust_apex"),
    "J04": LandmarkChord("bust_apex_left", "waist_string"),
    "J07": LandmarkChord("bust_apex_left", "acromion_left"),
    "J08": LandmarkChord("bust_apex_left", "waist_cf"),
    "J10": LandmarkChord("bust_apex_left", "front_shoulder_centre_left"),
    "J11": LandmarkChord("bust_apex_left", "front_neck_point"),

    # ------------------------------------------------------------------
    # K — Shoulder/neck geodesic paths
    # ------------------------------------------------------------------
    "K01": Geodesic(("acromion_left", "waist_cf")),
    "K02": Geodesic(("front_neck_point", "waist_side_left")),
    "K03": Geodesic(("shoulder_neck_left", "waist_side_left")),
    "K04": Geodesic(("acromion_left", "waist_cb")),
    "K06": Geodesic(("c7", "waist_side_left")),
    "K08": Geodesic(("shoulder_neck_left", "armfold_front_left")),
    "K09": Geodesic(("shoulder_neck_left", "underarm_left")),
    "K10": Geodesic(("shoulder_neck_left", "bust_apex_left")),
    "K11": Geodesic(("shoulder_neck_left", "armfold_back_left")),
    "K13": Geodesic(("shoulder_neck_left", "armfold_back_left", "bust_apex_left")),

    # ------------------------------------------------------------------
    # L — Arm
    #
    # Note: PlanarGirth for arm circumferences (L11/L12/L13/L14/L15) gives
    # WRONG results in A-pose because a horizontal slice at e.g. wrist Y
    # cuts through torso + both arms. Proper extraction needs an arm-axis
    # perpendicular slice with body-part vertex masking. Tracked as a
    # follow-up; values here are placeholders flagged in tests.
    # ------------------------------------------------------------------
    "L05": Geodesic(("acromion_left", "wrist_ulnar_left")),
    "L06": Geodesic(("acromion_left", "elbow_back_left")),
    "L08": Geodesic(("underarm_left", "wrist_ulnar_left")),
    "L09": Geodesic(("underarm_left", "elbow_back_left")),
    "L11": PlanarGirth("bicep_max_right", regions=("right_arm",)),
    "L13": PlanarGirth("elbow_back_left", regions=("left_arm",)),
    "L15": PlanarGirth("wrist_ulnar_left", regions=("left_arm",)),
    "L16": Geodesic(("acromion_left", "armfold_front_left")),
    "L19": GeodesicLoop(("acromion_left", "armscye_front_left",
                         "underarm_left", "armscye_back_left")),
    "L21": LandmarkChord("armscye_front_left", "armscye_back_left"),

    # ------------------------------------------------------------------
    # M — Leg
    #
    # Same caveat as L: PlanarGirth on leg landmarks in standing pose is
    # roughly correct when the legs are vertical (slice at knee/ankle Y
    # captures one leg), but at thigh-touching levels (M03) the slice
    # may include both legs joined. Region masking is a follow-up.
    # ------------------------------------------------------------------
    "M01": Height("crotch_midpoint"),
    "M02": Height("waist_side_left"),
    # Thigh at crotch sits exactly at leg/torso boundary; include torso so
    # the boundary triangles survive the mask.
    "M03": PlanarGirth("thigh_at_crotch_left",
                       regions=("left_leg", "torso")),
    "M05": PlanarGirth("mid_knee_level", regions=("left_leg",)),
    "M07": PlanarGirth("ankle_bone_lateral_left", regions=("left_leg",)),  # calf placeholder
    "M08": Height("ankle_bone_lateral_left"),
    "M09": PlanarGirth("ankle_bone_lateral_left", regions=("left_leg",)),

    # ------------------------------------------------------------------
    # N — Crotch (front-waist over crotch to back-waist)
    # ------------------------------------------------------------------
    "N01": Geodesic(("waist_cf", "crotch_midpoint", "waist_cb")),
    "N02": Geodesic(("crotch_midpoint", "waist_cb")),
    "N08": Geodesic(("waist_side_left", "crotch_lateral_left")),

    # ------------------------------------------------------------------
    # O — Geodesics through neck-back to waist-front (mechanical entries)
    # ------------------------------------------------------------------
    "O01": Geodesic(("c7", "waist_side_left", "waist_cf")),

    # ------------------------------------------------------------------
    # P — Complex torso paths
    # ------------------------------------------------------------------
    "P01": Geodesic(("c7", "bust_apex_left")),
    "P02": Geodesic(("c7", "armfold_front_left")),
    "P03": Geodesic(("c7", "armfold_front_left", "waist_side_left")),
    "P09": Geodesic(("armfold_front_left", "bust_apex_left",
                     "bust_apex_right", "armfold_front_right")),
    "P10": Geodesic(("armfold_front_left", "bust_apex_left")),
    "P12": Geodesic(("armscye_front_left", "acromion_left", "armscye_back_left")),
}


# Computed (formula) entries — evaluated after RECIPES.
FORMULAS = {
    # A-group computed
    "A18": Formula("A02 - A08"),                # neck_back -> knee
    "A19": Formula("A05 - A08"),                # waist_side -> knee
    "A20": Formula("A05 - A06"),                # waist_side -> hip
    "A21": Formula("A08 - A11"),                # knee -> ankle
    "A22": Formula("A02 - A05"),                # neck_back -> waist_side
    "A23": Formula("A02 - 0"),                  # waist_back: needs landmark, placeholder

    # G-group half/back arcs (representative subset; full coverage as
    # primary G-arcs are wired).
    "G18": Formula("G10 / 2"),
    "G19": Formula("G11 / 2"),
    "G20": Formula("G12 / 2"),
    "G21": Formula("G13 / 2"),
    "G23": Formula("G15 / 2"),
    "G24": Formula("G16 / 2"),
    "G25": Formula("G17 / 2"),

    "G26": Formula("G02 - G10"),                # neck back arc = circ - front arc
    "G27": Formula("G03 - G11"),                # highbust back geodesic arc
    "G28": Formula("G04 - G12"),                # bust back arc
    "G29": Formula("G05 - G13"),                # lowbust back arc
    "G31": Formula("G07 - G15"),                # waist back arc
    "G32": Formula("G08 - G16"),                # high_hip back arc
    "G33": Formula("G09 - G17"),                # hip back arc

    "G34": Formula("G26 / 2"),
    "G35": Formula("G27 / 2"),
    "G36": Formula("G28 / 2"),
    "G37": Formula("G29 / 2"),
    "G39": Formula("G31 / 2"),
    "G40": Formula("G32 / 2"),
    "G41": Formula("G33 / 2"),

    # H-group computed entries
    "H08": Formula("H07 - H01"),                  # highbust_to_waist_f = N..H07 - waist
    "H10": Formula("H09 - H01"),                  # bust_to_waist_f
    "H22": Formula("H21 - H19"),                  # highbust_to_waist_b
    "H24": Formula("H23 - H19"),                  # bust_to_waist_b
    "H42": Formula("H19 - H41"),                  # across_back_to_waist_b

    # I-group computed
    "I05": Formula("I02 / 2"),
    "I06": Formula("I03 / 2"),
    "I10": Formula("I07 / 2"),
    "I11": Formula("I08 / 2"),

    # J-group computed
    "J05": Formula("J01 / 2"),

    # L-group computed (subset that depends on wired primitives)
    "L07": Formula("L05 - L06"),                  # elbow_to_wrist
    "L03": Formula("L05 - L06"),                  # bent-arm same when no bent capture
    "L10": Formula("L07"),                        # elbow_to_wrist_inside ≈ outside for now

    # M-group computed
    "M12": Formula("M01 - M08"),                  # crotch_to_ankle
    "M13": Formula("M02 - M08"),                  # waist_side_to_ankle

    # N-group computed
    "N03": Formula("N01 - N02"),                  # crotch front = total - back
    "N06": Formula("N02"),                        # rise back = back portion of crotch
    "N07": Formula("N03"),                        # rise front
}


def all_codes_with_status() -> dict[str, str]:
    """Map every catalog code to a status string for reporting."""
    out: dict[str, str] = {}
    for c in RECIPES:
        out[c] = "mechanical"
    for c in FORMULAS:
        out[c] = "computed"
    for c, reason in JUDGMENT_OR_STANDARD.items():
        out[c] = f"skipped ({reason})"
    return out
