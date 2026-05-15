"""Blender verification helper for proposed SMPL-X landmark vertices.

Paste this entire script into Blender's Scripting tab and run it.
It will select the vertex for CURRENT_LANDMARK so you can see where it sits.

Change CURRENT_LANDMARK to the name you want to check, then Run Script.
"""

import bpy

# ── Change this to the landmark you want to verify ──────────────────────────
CURRENT_LANDMARK = "top_of_head"

# ── Proposed vertex IDs (from scripts/propose_smplx_landmarks.py) ───────────
PROPOSALS = {
    "top_of_head":                9011,
    "front_neck_point":           8344,
    "front_collar_bone":          5528,
    "c7":                         3832,
    "waist_cf":                   3856,
    "waist_cb":                   5489,
    "crotch_midpoint":            6300,
    "shoulder_neck_left":         3221,
    "shoulder_neck_right":        5984,
    "acromion_left":              5471,
    "acromion_right":             6882,
    "front_shoulder_centre_left": 4426,
    "front_shoulder_centre_right":7162,
    "underarm_left":              5480,
    "underarm_right":             8214,
    "armscye_front_left":         3234,
    "armscye_back_left":          5610,
    "armfold_front_left":         3834,
    "armfold_back_left":          5481,
    "armscye_front_right":        5997,
    "armscye_back_right":         8314,
    "armfold_front_right":        6912,
    "armfold_back_right":         8214,
    "bust_apex_left":             3315,
    "bust_apex_right":            6078,
    "lowbust_apex":               3855,
    "bra_side_seam_left":         5565,
    "bra_side_seam_right":        8277,
    "waist_side_left":            3273,
    "waist_side_right":           6036,
    "elbow_back_left":            4234,
    "elbow_back_right":           6978,
    "wrist_ulnar_left":           4697,
    "wrist_ulnar_right":          7433,
    "bicep_max_right":            8334,
    "thigh_at_crotch_left":       3866,
    "thigh_at_crotch_right":      6617,
    "crotch_lateral_left":        5704,
    "crotch_lateral_right":       6706,
    "knee_back_left":             3816,
    "knee_back_right":            6573,
    "ankle_bone_lateral_left":    5903,
    "ankle_bone_lateral_right":   8597,
    "rib_front":                  5534,
    "mid_neck_front":             8812,
}

# ── Select the vertex ────────────────────────────────────────────────────────
obj = bpy.context.active_object
if obj is None or obj.type != "MESH":
    print("ERROR: select the SMPL-X mesh object first (click on it in Object Mode)")
else:
    vid = PROPOSALS.get(CURRENT_LANDMARK)
    if vid is None:
        print(f"ERROR: '{CURRENT_LANDMARK}' not in PROPOSALS dict")
    else:
        # Switch to Object Mode to manipulate vertex select flags
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        # Deselect all vertices, then select the target
        for v in obj.data.vertices:
            v.select = False
        obj.data.vertices[vid].select = True

        # Back to Edit Mode so the selection is visible
        bpy.ops.object.mode_set(mode="EDIT")

        v = obj.data.vertices[vid]
        co = obj.matrix_world @ v.co   # world-space coords
        print(f"\n{'='*50}")
        print(f"  Landmark : {CURRENT_LANDMARK}")
        print(f"  Vertex   : {vid}")
        print(f"  Coord    : ({co.x:+.4f}, {co.y:+.4f}, {co.z:+.4f})")
        print(f"  --> check the highlighted vertex in the viewport")
        print(f"      If WRONG: click the correct vertex, then run:")
        print(f"      [v.index for v in bpy.context.active_object.data.vertices if v.select]")
        print(f"{'='*50}")
