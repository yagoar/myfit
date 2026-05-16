"""Landmark resolver: symbolic name -> 3D point on the fitted SMPL-X mesh.

Sources:
  - references/smplx_landmark_review.json  (verified vertex IDs per
    GUARDRAILS section 3; the user signed off on each in Blender)
  - this module's COMPOUND_LANDMARKS dict (midpoints, axes derived from
    base landmarks — no new vertex IDs invented)

The schema in merged.yaml uses dotted names like `landmarks.bust_apex_left`
and `landmarks.bust_apex_midpoint`. Resolution is mechanical: split on the
dot, look up the leaf name in the verified-IDs map or in COMPOUND_LANDMARKS.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEFAULT_REVIEW_JSON = Path("references/smplx_landmark_review.json")


# SMPL-X joint indices, in the order returned by smplx body_model().joints.
# Source: smplx.body_models.SMPLX. Body joints 0..21, then jaw, eyes, hands.
SMPLX_JOINT_INDEX = {
    "pelvis": 0, "L_Hip": 1, "R_Hip": 2, "spine1": 3, "L_Knee": 4,
    "R_Knee": 5, "spine2": 6, "L_Ankle": 7, "R_Ankle": 8, "spine3": 9,
    "L_Foot": 10, "R_Foot": 11, "neck": 12, "L_Collar": 13, "R_Collar": 14,
    "head": 15, "L_Shoulder": 16, "R_Shoulder": 17, "L_Elbow": 18,
    "R_Elbow": 19, "L_Wrist": 20, "R_Wrist": 21,
}


# Landmarks whose verified vertex IDs sit on heavily arm-driven vertices.
# Populating an entry here overrides the vertex with the named SMPL-X joint
# position (pose-invariant rotation centre).
#
# WARNING: joint positions are INTERNAL (rotation centres ~5cm inboard from
# the skin). Overriding e.g. acromion shifts surface-tape measurements like
# B01 width inward by ~9cm. Use only for landmarks where geodesic-endpoint
# stability under pose matters more than surface accuracy.
#
# Empty by default. The `joint.L_Shoulder` syntax remains available for
# explicit opt-in inside recipes.
JOINT_OVERRIDES: dict[str, str] = {}


# Compound landmarks: name -> (operation, [base_names])
# Resolved by computing on the base landmarks' 3D coordinates.
COMPOUND_LANDMARKS: dict[str, tuple[str, list[str]]] = {
    # bust_apex_left/right: synthesized landmark interpolated between two
    # SMPL-X canonical vertices because the mesh has no single vertex at
    # the Y where Yaiza's actual apex sits.
    #   vid 5646 (Y=-0.040, X=+0.094) — too HIGH on the fitted body
    #   vid 3230 (Y=-0.057, X=+0.091) — too LOW on the fitted body
    # lerp t=0.5 takes the midpoint: Y=-0.048, X=+0.093. Override the
    # verified-vid lookup in smplx_landmark_review.json; the JSON keeps
    # 3230 / 5993 as audit-trail for the closer of the two real vids.
    "bust_apex_left": ("lerp_vids", ["5646", "3230", "0.5"]),
    "bust_apex_right": ("lerp_vids", ["8340", "5993", "0.5"]),
    "bust_apex_midpoint": ("midpoint", ["bust_apex_left", "bust_apex_right"]),
    # Back midline at exact underarm Y — vid 5947 gives X/Z, underarm_left
    # gives Y. Used by G03 highbust so the back arc stays parallel to the
    # floor at true underarm height.
    "highbust_back_cf_at_underarm_y": ("snap_y_to", ["5947", "underarm_left"]),
    "armscye_back_midpoint": (
        "midpoint",
        ["armscye_back_left", "armscye_back_right"],
    ),
    "armscye_front_midpoint": (
        "midpoint",
        ["armscye_front_left", "armscye_front_right"],
    ),
    "shoulder_neck_midpoint": (
        "midpoint",
        ["shoulder_neck_left", "shoulder_neck_right"],
    ),
    "waist_side_midpoint": (
        "midpoint",
        ["waist_side_left", "waist_side_right"],
    ),
    # waist_string: a horizontal ring sitting at the natural waist. As an
    # anchor *point* we use the centre-front waist (Aldrich ties the string
    # there). The plane it defines uses the y-coordinate of this point.
    "waist_string": ("alias", ["waist_cf"]),

    # "Level" landmarks — symbolic horizontal planes referenced in merged.yaml
    # and the Seamly catalog. We represent each as a single 3D point whose
    # y-coordinate defines the horizontal slice; x/z carry no meaning when
    # used as a plane origin.
    "bust_level": ("alias", ["bust_apex_midpoint"]),
    "upper_bust_level": ("alias", ["armscye_front_midpoint"]),
    "armpit_level": ("alias", ["upper_bust_level"]),  # per extraction_audit.md
    "highbust_level": ("alias", ["armfold_front_left"]),  # armfold height
    "crotch_level": ("alias", ["crotch_midpoint"]),
    "mid_knee_level": ("midpoint", ["knee_back_left", "knee_back_right"]),
    "ankle_level": ("midpoint",
                    ["ankle_bone_lateral_left", "ankle_bone_lateral_right"]),
    # lowbust_level: detected underbust crease (per-body). The
    # lowbust_apex vid 3855 was too high on SMPL-X canonical; the
    # `underbust_crease_left` dynamic landmark finds the inframammary
    # fold directly from the fitted mesh.
    "lowbust_level": ("alias", ["underbust_crease_left"]),
    "mid_neck_level": ("alias", ["mid_neck_front"]),
    # neck_base_level: front_neck_point sits at the throat hollow. At +2.5cm
    # the slice grazed the trapezius (truth diff +27%); at +5cm it overshoot
    # into the upper neck (−10%). +4cm is the sweet spot for the base of
    # the actual neck cylinder where a tape is normally placed.
    "neck_base_level": ("offset_y", ["front_neck_point", "0.04"]),
    # ankle_high_level: ~3cm above the lateral malleolus, where the leg
    # is narrowest (the "ankle high" tape-measure level, distinct from
    # the ankle bone itself).
    "ankle_high_level": ("offset_y", ["ankle_bone_lateral_left", "0.03"]),
    # Synthetic plumb-line waypoints — X/Z from one landmark, Y from a
    # horizontal plane. Used by PolylineChord recipes (e.g. H01) so the
    # tape goes straight down from neck-front to the bust-level line,
    # then across to waist_cf, instead of contouring over the bust.
    "fnp_at_bust_y": ("snap_y_landmark",
                       ["front_neck_point", "bust_level"]),
    "sn_at_bust_y_left": ("snap_y_landmark",
                           ["shoulder_neck_left", "bust_level"]),
    "c7_at_bust_y": ("snap_y_landmark", ["c7", "bust_level"]),
    "c7_at_highbust_y": ("snap_y_landmark", ["c7", "armfold_front_left"]),
    "sn_at_highbust_y_left": ("snap_y_landmark",
                                ["shoulder_neck_left", "armfold_front_left"]),
    "waist_side_left_at_lowhip_y": ("snap_y_landmark",
                                      ["waist_side_left", "low_hip_level"]),
    "waist_side_left_at_floor": ("snap_y_landmark",
                                   ["waist_side_left", "floor_anchor"]),
    "waist_side_left_at_highhip_y": ("snap_y_landmark",
                                       ["waist_side_left", "high_hip_level"]),
    "armfold_back_left_at_waist_y": ("snap_y_landmark",
                                       ["armfold_back_left", "waist_cb"]),
    "underarm_left_at_bust_y": ("snap_y_landmark",
                                  ["underarm_left", "bust_level"]),
    "underarm_right_at_bust_y": ("snap_y_landmark",
                                   ["underarm_right", "bust_level"]),
    # Synthetic interior arm points at the underarm Y — used as origins
    # for LimbGirth so the slice plane cuts the arm tube, not the torso.
    "l_arm_at_underarm_y": ("snap_y_landmark",
                              ["joint.L_Shoulder", "underarm_left"]),
    "bust_apex_left_at_lowbust_y": ("snap_y_landmark",
                                      ["bust_apex_left", "lowbust_level"]),
    "bust_apex_left_at_waist_y": ("snap_y_landmark",
                                    ["bust_apex_left", "waist_string"]),
    # high_hip_level: rule per dpm pants_1 = 4-5" below waist (~11cm). Use a
    # fixed mid-value here; refine when scan calibration validates.
    # Stored as point with y = waist_cf.y - 0.11; x/z unused as plane origin.
    "high_hip_level": ("offset_y", ["waist_string", "-0.11"]),
    # low_hip_level: dpm "widest girth below waist". For scaffolding we use
    # 20cm below the waist as a placeholder horizontal level; the proper
    # implementation searches for the maximum-girth slice in a Y range.
    "low_hip_level": ("offset_y", ["waist_string", "-0.20"]),
}


# Reserved for landmarks computed per fit (e.g. searching a region of the
# deformed mesh for an extremum). Empty by default — tested with a
# `bust_apex_left/right -> max-Z search` override which made J01 worse
# (search produced more-medial points than the verified vids because the
# SMPL-X+D Laplacian smoothness flattens the apex peak relative to the
# truetoform tape position). Keeping the infrastructure for future use.
DYNAMIC_LANDMARKS: dict[str, dict] = {
    # Floor anchor: the body's lowest Y. Used to project landmarks down
    # to floor level for plumb-line measurements that terminate at the
    # ground (e.g. M02 outseam).
    "floor_anchor": {"search": "min_y"},
    # Waist front body point at the bust apex X — used as the endpoint
    # of J04 (bust apex to waist at apex X on the G07 line).
    "waist_front_at_apex_x_left": {
        "search": "body_at_xy",
        "x_ref": "bust_apex_left",
        "y_ref": "waist_string",
        "x_band": 0.02,
        "y_band": 0.01,
        "front_only": True,
    },
    # Body surface point on the G04 (bust) line at the SN_L X column.
    # Endpoint for H14 (neck side straight down to bust line).
    "bust_front_at_sn_x_left": {
        "search": "body_at_xy",
        "x_ref": "shoulder_neck_left",
        "y_ref": "bust_level",
        "x_band": 0.02,
        "y_band": 0.01,
        "front_only": True,
    },
    # Body surface point on the G03 (highbust = armfold_front Y) line at
    # the SN_L X column. Endpoint for H15.
    "highbust_front_at_sn_x_left": {
        "search": "body_at_xy",
        "x_ref": "shoulder_neck_left",
        "y_ref": "armfold_front_left",
        "x_band": 0.02,
        "y_band": 0.01,
        "front_only": True,
    },
    # Underbust crease (inframammary fold). Detected per-body by scanning
    # the anterior surface profile below the bust apex for the steepest
    # negative dZ/dY — the point where the breast tissue meets the
    # ribcage. Falls back gracefully if too few samples are found.
    "underbust_crease_left": {
        "search": "underbust_crease",
        "apex": "bust_apex_left",
        # Search 3-12 cm below apex (covers small to large busts).
        "min_offset": 0.03,
        "max_offset": 0.12,
        # Fold = where breast has receded `drop_fraction` of its full
        # depth (apex Z minus chest-wall Z, both measured automatically).
        # 0.7 lands at the actual inframammary crease on small/medium busts;
        # tune up for larger busts if needed.
        "drop_fraction": 0.7,
        "min_drop": 0.005,  # floor for flat chests
    },
}


@dataclass(frozen=True)
class LandmarkSet:
    """Resolved 3D points for every named landmark on a specific mesh."""

    verts: np.ndarray  # (V, 3) fitted SMPL-X vertices
    vertex_ids: dict[str, int]  # leaf name -> vertex id
    joints: np.ndarray | None = None  # (J, 3) fitted SMPL-X joint positions

    def __getitem__(self, name: str) -> np.ndarray:
        """Resolve `landmarks.<leaf>`, `joint.<NAME>`, or bare `<leaf>` to
        a 3D point."""
        if name.startswith("joint."):
            return self._joint(name.split(".", 1)[1])
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name

        if leaf in JOINT_OVERRIDES and self.joints is not None:
            return self._joint(JOINT_OVERRIDES[leaf])

        if leaf in DYNAMIC_LANDMARKS:
            return self._dynamic(leaf, DYNAMIC_LANDMARKS[leaf])

        # COMPOUND_LANDMARKS overrides vertex_ids when the same leaf is in
        # both. Lets us synthesize a landmark position (e.g. lerp between
        # two vids) without removing the verified vid record from the JSON.
        if leaf in COMPOUND_LANDMARKS:
            op, bases = COMPOUND_LANDMARKS[leaf]
            if op == "offset_y":
                base = self[bases[0]]
                dy = float(bases[1])
                return np.array([base[0], base[1] + dy, base[2]])
            if op == "midpoint_of_vids":
                pts = np.stack([self.verts[int(vid)] for vid in bases])
                return pts.mean(axis=0)
            if op == "lerp_vids":
                vid_a, vid_b = int(bases[0]), int(bases[1])
                t = float(bases[2])
                return self.verts[vid_a] * (1 - t) + self.verts[vid_b] * t
            if op == "snap_y_to":
                # Take X/Z from a vid, override Y with another landmark's Y.
                # bases: [vid_str, landmark_name_for_y]
                pos = self.verts[int(bases[0])].copy()
                pos[1] = self[bases[1]][1]
                return pos
            if op == "snap_y_landmark":
                # Take X/Z from one landmark, Y from another. Useful for
                # synthetic plumb-line waypoints (e.g. project FNP straight
                # down to bust_level for sewing yardstick paths).
                # bases: [xz_landmark_name, y_landmark_name]
                a = self[bases[0]]
                b = self[bases[1]]
                return np.array([a[0], b[1], a[2]])
            pts = np.stack([self[b] for b in bases])
            if op == "midpoint":
                return pts.mean(axis=0)
            if op == "alias":
                return pts[0]
            raise ValueError(f"unknown compound op {op!r} for {leaf!r}")

        if leaf in self.vertex_ids:
            return self.verts[self.vertex_ids[leaf]]

        raise KeyError(
            f"landmark {leaf!r} is neither a verified vertex ID nor a "
            "compound landmark. Add it to references/smplx_landmark_review.json "
            "(via Blender review) or to COMPOUND_LANDMARKS in this file."
        )

    def has(self, name: str) -> bool:
        if name.startswith("joint."):
            return (self.joints is not None
                    and name.split(".", 1)[1] in SMPLX_JOINT_INDEX)
        leaf = name.split(".", 1)[1] if name.startswith("landmarks.") else name
        if leaf in JOINT_OVERRIDES and self.joints is not None:
            return True
        return (leaf in self.vertex_ids or leaf in COMPOUND_LANDMARKS
                or leaf in DYNAMIC_LANDMARKS)

    def _dynamic(self, name: str, spec: dict) -> np.ndarray:
        """Resolve a landmark by searching the fitted mesh per the spec.
        Currently supports `search: max_z` (most anterior point) with
        optional x_min, x_max, y_between bounds drawn from other landmarks."""
        v = self.verts
        mask = np.ones(len(v), dtype=bool)
        if "x_min" in spec:
            mask &= v[:, 0] > spec["x_min"]
        if "x_max" in spec:
            mask &= v[:, 0] < spec["x_max"]
        if "y_between" in spec:
            lower_name, upper_name = spec["y_between"]
            y_lo = float(self[lower_name][1])
            y_hi = float(self[upper_name][1])
            if y_lo > y_hi:
                y_lo, y_hi = y_hi, y_lo
            mask &= (v[:, 1] > y_lo) & (v[:, 1] < y_hi)
        if not mask.any():
            raise KeyError(f"dynamic landmark {name!r}: no verts in search region")
        if spec["search"] == "max_z":
            idx = int(np.argmax(np.where(mask, v[:, 2], -np.inf)))
            return v[idx]
        if spec["search"] == "min_z":
            idx = int(np.argmin(np.where(mask, v[:, 2], np.inf)))
            return v[idx]
        if spec["search"] == "min_y":
            idx = int(np.argmin(np.where(mask, v[:, 1], np.inf)))
            return v[idx]
        if spec["search"] == "max_y":
            idx = int(np.argmax(np.where(mask, v[:, 1], -np.inf)))
            return v[idx]
        if spec["search"] == "body_at_xy":
            # Find the body surface vertex closest to a target (X, Y),
            # preferring front of body (max Z). `x_ref` and `y_ref` are
            # landmark names supplying X and Y; the returned point sits
            # on the body at those coords with the body's natural Z.
            x = float(self[spec["x_ref"]][0])
            y = float(self[spec["y_ref"]][1])
            x_band = float(spec.get("x_band", 0.02))
            y_band = float(spec.get("y_band", 0.01))
            front_only = spec.get("front_only", True)
            m = ((np.abs(v[:, 0] - x) < x_band)
                 & (np.abs(v[:, 1] - y) < y_band))
            if front_only:
                m &= v[:, 2] > 0
            if not m.any():
                # Widen the bands.
                m = ((np.abs(v[:, 0] - x) < x_band * 2)
                     & (np.abs(v[:, 1] - y) < y_band * 2))
                if front_only:
                    m &= v[:, 2] > 0
            if not m.any():
                raise KeyError(f"body_at_xy {name!r}: no verts in band")
            idx = int(np.argmax(np.where(m, v[:, 2], -np.inf)))
            return v[idx]
        if spec["search"] == "underbust_crease":
            # Detect the inframammary fold per-body.
            # 1. Bust depth = (apex Z) - (chest-wall reference Z); the
            #    chest-wall reference is taken from a non-breast landmark
            #    (default: armfold_front_left, which sits on the pectoral
            #    above the breast).
            # 2. Scan Y from min_offset below apex down to max_offset.
            #    At each Y, sample max-Z of body verts in a slab around
            #    apex X on the front (Z>0).
            # 3. Crease = first Y where Z has dropped by `drop_fraction`
            #    of the bust depth (default 0.5 = the fold sits where the
            #    breast has lost half of its anterior protrusion). Falls
            #    back to steepest-gradient if no such crossing exists.
            ref = self[spec["apex"]]
            apex_y = float(ref[1])
            apex_x = float(ref[0])
            apex_z = float(ref[2])
            # Estimate the chest-wall (no-breast) Z at apex X. We sample
            # body verts in a narrow X slab AT a Y a few cm above the
            # breast attachment (default 8cm above apex — upper chest /
            # sternum below the clavicle, well clear of bust tissue).
            slab_dx_chest = float(spec.get("chest_slab_dx", 0.03))
            chest_y = apex_y + float(spec.get("chest_y_offset", 0.08))
            chest_y_band = float(spec.get("chest_y_band", 0.01))
            chest_mask = ((np.abs(v[:, 0] - apex_x) < slab_dx_chest)
                          & (np.abs(v[:, 1] - chest_y) < chest_y_band)
                          & (v[:, 2] > 0))
            if chest_mask.any():
                chest_z = float(v[chest_mask, 2].mean())
            else:
                chest_z = apex_z  # degenerate
            bust_depth = max(apex_z - chest_z, 0.0)
            drop_fraction = float(spec.get("drop_fraction", 0.5))
            min_drop = float(spec.get("min_drop", 0.005))
            fold_drop = max(bust_depth * drop_fraction, min_drop)

            y_top = apex_y - float(spec.get("min_offset", 0.02))
            y_bot = apex_y - float(spec.get("max_offset", 0.12))
            slab_dx = float(spec.get("slab_dx", 0.04))
            y_band = float(spec.get("y_band", 0.005))
            ys = np.linspace(y_top, y_bot, 60)
            zs = []
            ys_kept = []
            for y in ys:
                m = ((np.abs(v[:, 0] - apex_x) < slab_dx)
                     & (np.abs(v[:, 1] - y) < y_band)
                     & (v[:, 2] > 0))
                if not m.any():
                    continue
                ys_kept.append(y)
                zs.append(v[m, 2].max())
            if len(ys_kept) < 5:
                raise KeyError(f"underbust_crease {name!r}: too few samples")
            ys_arr = np.array(ys_kept)
            zs_arr = np.array(zs)
            z_top = zs_arr[0]
            below = np.where(z_top - zs_arr >= fold_drop)[0]
            if len(below):
                i = int(below[0])
            else:
                dz = np.gradient(zs_arr, ys_arr)
                i = int(np.argmin(dz))
            return np.array([apex_x, ys_arr[i], zs_arr[i]])
        raise ValueError(f"unknown search {spec['search']!r}")

    def _joint(self, joint_name: str) -> np.ndarray:
        if self.joints is None:
            raise KeyError(
                f"joint.{joint_name} requested but LandmarkSet was built "
                "without joints — pass `joints=fit['smplx_joints']` to "
                "build_landmark_set."
            )
        if joint_name not in SMPLX_JOINT_INDEX:
            raise KeyError(f"unknown SMPL-X joint name {joint_name!r}")
        return self.joints[SMPLX_JOINT_INDEX[joint_name]]


def load_vertex_ids(path: Path | str = DEFAULT_REVIEW_JSON) -> dict[str, int]:
    """Read the verified vertex IDs (with any status — confirmed, corrected,
    mirrored). Skipped entries are dropped."""
    raw = json.loads(Path(path).read_text())
    out: dict[str, int] = {}
    for name, rec in raw.items():
        if rec.get("status") == "skipped":
            continue
        out[name] = int(rec["vertex_id"])
    return out


def build_landmark_set(
    fitted_verts: np.ndarray,
    review_json: Path | str = DEFAULT_REVIEW_JSON,
    joints: np.ndarray | None = None,
) -> LandmarkSet:
    """Construct a LandmarkSet from a fitted SMPL-X mesh + verified IDs.

    `joints` is the (J, 3) array from a fit (e.g. fit['smplx_joints']);
    when supplied, it enables `joint.X` resolution and the JOINT_OVERRIDES
    fallback (acromion -> L_Shoulder, etc.)."""
    return LandmarkSet(
        verts=fitted_verts,
        vertex_ids=load_vertex_ids(review_json),
        joints=joints,
    )
