"""Streamlined SMPL-X landmark verifier for Blender 5.x.

Paste into Blender Scripting tab and Run Script.
A panel appears in the 3D viewport (press N to open the N-panel, find "Landmarks" tab).

Controls:
  [Confirm]  → mark current proposal as VERIFIED, advance to next
  [Wrong – use selected]  → record the currently selected vertex instead, advance
  [Skip]  → leave as unverified, advance
  [Prev] / [Next]  → navigate without recording

Results saved to:  /tmp/landmark_review.json
"""

import bpy
import json
from pathlib import Path

# ── Proposals ────────────────────────────────────────────────────────────────
PROPOSALS = {
    "top_of_head":                 9011,
    "front_neck_point":            8344,
    "front_collar_bone":           5528,
    "c7":                          3832,
    "waist_cf":                    3856,
    "waist_cb":                    5489,
    "crotch_midpoint":             6300,
    "shoulder_neck_left":          3221,
    "shoulder_neck_right":         5984,
    "acromion_left":               5471,
    "acromion_right":              6882,
    "front_shoulder_centre_left":  4426,
    "front_shoulder_centre_right": 7162,
    "underarm_left":               5480,
    "underarm_right":              8214,
    "armscye_front_left":          3234,
    "armscye_back_left":           5610,
    "armfold_front_left":          3834,
    "armfold_back_left":           5481,
    "armscye_front_right":         5997,
    "armscye_back_right":          8314,
    "armfold_front_right":         6912,
    "armfold_back_right":          8214,
    "bust_apex_left":              3315,
    "bust_apex_right":             6078,
    "lowbust_apex":                3855,
    "bra_side_seam_left":          5565,
    "bra_side_seam_right":         8277,
    "waist_side_left":             3273,
    "waist_side_right":            6036,
    "elbow_back_left":             4234,
    "elbow_back_right":            6978,
    "wrist_ulnar_left":            4697,
    "wrist_ulnar_right":           7433,
    "bicep_max_right":             8334,
    "thigh_at_crotch_left":        3866,
    "thigh_at_crotch_right":       6617,
    "crotch_lateral_left":         5704,
    "crotch_lateral_right":        6706,
    "knee_back_left":              3816,
    "knee_back_right":             6573,
    "ankle_bone_lateral_left":     5903,
    "ankle_bone_lateral_right":    8597,
    "rib_front":                   5534,
    "mid_neck_front":              8812,
}

# ── Left/right pairs — verify left only, mirror the right automatically ─────
MIRROR_PAIRS = {
    "shoulder_neck_left":         "shoulder_neck_right",
    "acromion_left":              "acromion_right",
    "front_shoulder_centre_left": "front_shoulder_centre_right",
    "underarm_left":              "underarm_right",
    "armscye_front_left":         "armscye_front_right",
    "armscye_back_left":          "armscye_back_right",
    "armfold_front_left":         "armfold_front_right",
    "armfold_back_left":          "armfold_back_right",
    "bust_apex_left":             "bust_apex_right",
    "bra_side_seam_left":         "bra_side_seam_right",
    "waist_side_left":            "waist_side_right",
    "elbow_back_left":            "elbow_back_right",
    "wrist_ulnar_left":           "wrist_ulnar_right",
    "thigh_at_crotch_left":       "thigh_at_crotch_right",
    "crotch_lateral_left":        "crotch_lateral_right",
    "knee_back_left":             "knee_back_right",
    "ankle_bone_lateral_left":    "ankle_bone_lateral_right",
}
RIGHT_NAMES = set(MIRROR_PAIRS.values())

# Iterate only over left + unpaired (skip right-side; mirror handles them)
NAMES   = [n for n in PROPOSALS.keys() if n not in RIGHT_NAMES]
OUT     = Path("/tmp/landmark_review.json")


def find_mirror_vid(obj, vid):
    """Return the index of the vertex closest to (-x, y, z) of vid."""
    verts = obj.data.vertices
    src = verts[vid].co
    tx, ty, tz = -src.x, src.y, src.z
    best, best_d = -1, float("inf")
    for i, v in enumerate(verts):
        d = (v.co.x - tx) ** 2 + (v.co.y - ty) ** 2 + (v.co.z - tz) ** 2
        if d < best_d:
            best_d, best = d, i
    return best

# ── State (stored on the scene to survive re-runs) ───────────────────────────
if "lm_index" not in bpy.context.scene:
    bpy.context.scene["lm_index"]   = 0
if "lm_results" not in bpy.context.scene:
    bpy.context.scene["lm_results"] = {}


def current_name():
    return NAMES[bpy.context.scene["lm_index"]]


def select_vertex(vid):
    obj = bpy.context.active_object
    if not obj or obj.type != "MESH":
        return
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in obj.data.vertices:
        v.select = False
    obj.data.vertices[vid].select = True
    bpy.ops.object.mode_set(mode="EDIT")
    # Press Numpad . in the viewport to frame the selected vertex


def save_results():
    raw = bpy.context.scene["lm_results"]
    results = {k: {"vertex_id": int(v["vertex_id"]), "status": str(v["status"])}
               for k, v in raw.items()}
    OUT.write_text(json.dumps(results, indent=2))


def get_selected_vertex():
    obj = bpy.context.active_object
    bpy.ops.object.mode_set(mode="OBJECT")
    sel = [v.index for v in obj.data.vertices if v.select]
    bpy.ops.object.mode_set(mode="EDIT")
    return sel[0] if len(sel) == 1 else None


def jump_to(idx):
    bpy.context.scene["lm_index"] = max(0, min(idx, len(NAMES) - 1))
    name = current_name()
    results = bpy.context.scene["lm_results"]
    if name in results:
        vid = int(results[name]["vertex_id"])
        src = results[name]["status"]
    else:
        vid = PROPOSALS[name]
        src = "proposed"
    select_vertex(vid)
    print(f"[{bpy.context.scene['lm_index']+1}/{len(NAMES)}] {name}  →  v{vid} ({src})")


# ── Operators ─────────────────────────────────────────────────────────────────
class LM_OT_Jump(bpy.types.Operator):
    bl_idname = "lm.jump"
    bl_label  = "Start / Jump to current"
    def execute(self, _ctx):
        jump_to(bpy.context.scene["lm_index"])
        return {"FINISHED"}


def record_with_mirror(name, vid, status):
    """Save a landmark + auto-mirror to its right-side pair if applicable."""
    obj = bpy.context.active_object
    results = bpy.context.scene["lm_results"]
    results[name] = {"vertex_id": vid, "status": status}
    if name in MIRROR_PAIRS:
        mvid = find_mirror_vid(obj, vid)
        results[MIRROR_PAIRS[name]] = {"vertex_id": mvid, "status": f"mirrored_from_{name}"}
    save_results()


class LM_OT_Confirm(bpy.types.Operator):
    bl_idname = "lm.confirm"
    bl_label  = "Confirm"
    def execute(self, _ctx):
        name = current_name()
        results = bpy.context.scene["lm_results"]
        if name in results:
            vid = int(results[name]["vertex_id"])
            status = results[name]["status"]
        else:
            vid = PROPOSALS[name]
            status = "confirmed"
        record_with_mirror(name, vid, status)
        jump_to(bpy.context.scene["lm_index"] + 1)
        return {"FINISHED"}


class LM_OT_UseSelected(bpy.types.Operator):
    bl_idname = "lm.use_selected"
    bl_label  = "Wrong – use selected vertex"
    def execute(self, _ctx):
        vid = get_selected_vertex()
        if vid is None:
            self.report({"WARNING"}, "Select exactly one vertex first")
            return {"CANCELLED"}
        name = current_name()
        record_with_mirror(name, vid, "corrected")
        jump_to(bpy.context.scene["lm_index"] + 1)
        return {"FINISHED"}


class LM_OT_Skip(bpy.types.Operator):
    bl_idname = "lm.skip"
    bl_label  = "Skip"
    def execute(self, _ctx):
        jump_to(bpy.context.scene["lm_index"] + 1)
        return {"FINISHED"}


class LM_OT_Prev(bpy.types.Operator):
    bl_idname = "lm.prev"
    bl_label  = "< Prev"
    def execute(self, _ctx):
        jump_to(bpy.context.scene["lm_index"] - 1)
        return {"FINISHED"}


class LM_OT_Next(bpy.types.Operator):
    bl_idname = "lm.next"
    bl_label  = "Next >"
    def execute(self, _ctx):
        jump_to(bpy.context.scene["lm_index"] + 1)
        return {"FINISHED"}


# ── Panel ─────────────────────────────────────────────────────────────────────
class LM_PT_Panel(bpy.types.Panel):
    bl_label       = "Landmarks"
    bl_idname      = "LM_PT_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Landmarks"

    def draw(self, ctx):
        layout  = self.layout
        scene   = ctx.scene
        idx     = scene["lm_index"]
        results = scene["lm_results"]
        name    = NAMES[idx] if idx < len(NAMES) else "DONE"
        done    = sum(1 for v in results.values() if v["status"] in ("confirmed","corrected"))

        layout.label(text=f"{idx+1} / {len(NAMES)}  ({done} done)", icon="CHECKMARK")
        layout.separator()

        box = layout.box()
        box.label(text=name, icon="OBJECT_DATAMODE")
        if name in results:
            st = results[name]["status"]
            box.label(text=f"Status: {st}  v{results[name]['vertex_id']}", icon="INFO")

        layout.operator("lm.jump",         icon="CURSOR")
        layout.separator()
        layout.operator("lm.confirm",      icon="CHECKMARK")
        layout.operator("lm.use_selected", icon="CURSOR")
        layout.operator("lm.skip",         icon="FORWARD")
        layout.separator()
        row = layout.row()
        row.operator("lm.prev")
        row.operator("lm.next")
        layout.separator()
        layout.label(text=f"Saved to: {OUT}")


# ── Register ──────────────────────────────────────────────────────────────────
classes = [LM_OT_Jump, LM_OT_Confirm, LM_OT_UseSelected, LM_OT_Skip,
           LM_OT_Prev, LM_OT_Next, LM_PT_Panel]

for cls in classes:
    try:
        bpy.utils.unregister_class(cls)
    except Exception:
        pass
    bpy.utils.register_class(cls)

print("Landmark review ready. Open N-panel (press N in viewport) → 'Landmarks' tab. Click 'Start / Jump' to begin.")
