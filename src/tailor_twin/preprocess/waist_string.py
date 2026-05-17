"""Detect a coloured elastic / string tied around the natural waist.

Why this exists: SMPL-X's anatomical "waist" is the CAESAR-trained
shape-space waist, not the Y where YOU tie the string. Every
waist-anchored measurement (Aldrich #2, dpm waist circ, H05/J04, the
balance-line F-codes) inherits that ~1-3 cm shape-space bias unless
the actual tied Y is plumbed back into the LandmarkSet.

Approach:
  1. Per RGB frame: HSV-threshold the string colour → 2D mask.
  2. Resize mask to depth resolution, intersect with valid-depth.
  3. Re-project each masked pixel into the world frame using the
     frame's intrinsics + camera→world pose.
  4. Aggregate the world-space string points across the whole capture
     and take the median Y (robust to occlusions / spurious matches).

The result is one world-frame Y value; X/Z of the waist landmarks
stay at their verified-vid columns (the body's geometry at the
waist is roughly cylindrical over a 1-3 cm Y window, so X/Z don't
shift meaningfully).

Detected Y is saved as JSON next to the fit; the measurement CLI
reads it and overrides ``waist_y`` in the LandmarkSet.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


# Preset HSV ranges (OpenCV: H ∈ [0,179], S/V ∈ [0,255]). Red wraps
# around 0/180, so it needs two ranges.
COLOR_PRESETS: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "red":     [((  0, 100,  60), ( 10, 255, 255)),
                ((170, 100,  60), (179, 255, 255))],
    "cyan":    [(( 85, 100,  60), (100, 255, 255))],
    "green":   [(( 40,  80,  50), ( 80, 255, 255))],
    "magenta": [((140, 100,  60), (170, 255, 255))],
    "yellow":  [(( 20, 100,  80), ( 35, 255, 255))],
    "blue":    [((100, 100,  60), (130, 255, 255))],
    "orange":  [(( 10, 130,  80), ( 22, 255, 255))],
}


# Pipeline params — exposed as kwargs but defaults are sane for a
# 1-3 cm wide elastic at ~1.2 m distance.
DEFAULT_MORPH_KERNEL = 3        # erosion/dilation kernel side (px)
DEFAULT_MIN_PIXELS = 30          # frames with fewer matches are skipped
DEFAULT_DEPTH_SCALE = 1000.0    # Stray depth_mm → m
DEFAULT_DEPTH_MIN_MM = 400
DEFAULT_DEPTH_MAX_MM = 2500


@dataclass
class WaistStringDetection:
    """Output of `detect_waist_y` — written to JSON next to the fit."""
    y_m: float                  # world-frame Y of the waist string
    n_frames_used: int          # frames that contributed ≥1 point
    n_points: int               # total reprojected string points
    median_y_m: float           # = y_m; named for clarity in JSON
    p10_y_m: float              # 10th-percentile Y (spread indicator)
    p90_y_m: float              # 90th-percentile Y
    inlier_ratio: float         # fraction within ±20 mm of median
    color: str                  # preset / "custom"
    hsv_low: tuple[int, int, int] | None
    hsv_high: tuple[int, int, int] | None

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def from_json(cls, path: Path) -> "WaistStringDetection":
        data = json.loads(Path(path).read_text())
        # Tuple round-trip — JSON gives lists.
        if data.get("hsv_low") is not None:
            data["hsv_low"] = tuple(data["hsv_low"])
        if data.get("hsv_high") is not None:
            data["hsv_high"] = tuple(data["hsv_high"])
        return cls(**data)


def _color_ranges(
    color: str,
    hsv_low: tuple[int, int, int] | None,
    hsv_high: tuple[int, int, int] | None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Resolve a colour preset or custom HSV bounds into a list of (lo, hi)
    numpy arrays. Custom bounds always supersede the preset."""
    if hsv_low is not None and hsv_high is not None:
        return [(np.array(hsv_low, dtype=np.uint8),
                 np.array(hsv_high, dtype=np.uint8))]
    if color not in COLOR_PRESETS:
        raise ValueError(
            f"unknown waist-string colour {color!r}; "
            f"presets: {sorted(COLOR_PRESETS)}")
    return [(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))
            for lo, hi in COLOR_PRESETS[color]]


def _color_mask(rgb: np.ndarray, ranges) -> np.ndarray:
    """Combined HSV mask across all (lo, hi) ranges, with morphology."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        mask |= cv2.inRange(hsv, lo, hi)
    kernel = np.ones((DEFAULT_MORPH_KERNEL, DEFAULT_MORPH_KERNEL),
                      dtype=np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask > 0


def _rescale_intrinsics(
    K: np.ndarray, native_size: tuple[int, int] | None,
    depth_size: tuple[int, int],
) -> np.ndarray:
    if native_size is None or native_size == depth_size:
        return K
    nw, nh = native_size
    dw, dh = depth_size
    sx, sy = dw / nw, dh / nh
    Kp = K.copy().astype(np.float64)
    Kp[0, 0] *= sx
    Kp[1, 1] *= sy
    Kp[0, 2] *= sx
    Kp[1, 2] *= sy
    return Kp


def _reproject_pixels_to_world(
    pixel_uv: np.ndarray,        # (N, 2) int, in DEPTH grid
    depths_m: np.ndarray,        # (N,) float, metres
    K_depth_grid: np.ndarray,    # 3×3 intrinsics already in the depth grid
    pose_c2w: np.ndarray,        # 4×4 camera→world
) -> np.ndarray:
    """Lift (u, v, depth) → world-frame (X, Y, Z)."""
    fx = K_depth_grid[0, 0]
    fy = K_depth_grid[1, 1]
    cx = K_depth_grid[0, 2]
    cy = K_depth_grid[1, 2]
    u = pixel_uv[:, 0].astype(np.float64)
    v = pixel_uv[:, 1].astype(np.float64)
    # Stray follows ARKit: +Y up, camera looks down -Z. Standard pinhole:
    # X = (u - cx) * Z / fx ; Y = (v - cy) * Z / fy ; flip Z for ARKit.
    Xc = (u - cx) * depths_m / fx
    Yc = -(v - cy) * depths_m / fy
    Zc = -depths_m
    pts_cam = np.stack([Xc, Yc, Zc, np.ones_like(Xc)], axis=1)  # (N, 4)
    pts_world = (pose_c2w @ pts_cam.T).T  # (N, 4)
    return pts_world[:, :3]


def detect_waist_y(
    frames: Iterable,
    *,
    color: str = "red",
    hsv_low: tuple[int, int, int] | None = None,
    hsv_high: tuple[int, int, int] | None = None,
    intrinsics_native_size: tuple[int, int] | None = None,
    min_pixels_per_frame: int = DEFAULT_MIN_PIXELS,
    depth_scale: float = DEFAULT_DEPTH_SCALE,
    depth_min_mm: int = DEFAULT_DEPTH_MIN_MM,
    depth_max_mm: int = DEFAULT_DEPTH_MAX_MM,
    verbose: bool = True,
) -> WaistStringDetection:
    """Scan ``frames`` (Stray loader output), aggregate string points,
    return a world-frame waist Y.

    Raises:
      RuntimeError — if no frame contributes any matched pixel.
    """
    ranges = _color_ranges(color, hsv_low, hsv_high)
    all_ys: list[float] = []
    n_frames_used = 0
    for f in frames:
        if f.rgb is None or f.depth_mm is None:
            continue
        mask_rgb = _color_mask(f.rgb, ranges)
        # Resize RGB mask → depth grid. Use nearest for boolean masks.
        h_d, w_d = f.depth_mm.shape
        if mask_rgb.shape != (h_d, w_d):
            mask_d = cv2.resize(
                mask_rgb.astype(np.uint8), (w_d, h_d),
                interpolation=cv2.INTER_NEAREST,
            ) > 0
        else:
            mask_d = mask_rgb
        depth_valid = (f.depth_mm >= depth_min_mm) & (f.depth_mm <= depth_max_mm)
        keep = mask_d & depth_valid
        if int(keep.sum()) < min_pixels_per_frame:
            continue
        vs, us = np.where(keep)
        depths_m = f.depth_mm[keep].astype(np.float64) / depth_scale
        K = _rescale_intrinsics(
            f.intrinsics, intrinsics_native_size, (w_d, h_d))
        pts = _reproject_pixels_to_world(
            np.stack([us, vs], axis=1), depths_m, K, f.pose_cam_to_world,
        )
        all_ys.extend(pts[:, 1].tolist())
        n_frames_used += 1

    if not all_ys:
        raise RuntimeError(
            f"detect_waist_y: no pixels matched colour {color!r} "
            "across the capture (wrong hue range, or string not visible)")

    ys = np.asarray(all_ys, dtype=np.float64)
    median = float(np.median(ys))
    p10 = float(np.percentile(ys, 10))
    p90 = float(np.percentile(ys, 90))
    inliers = float(np.mean(np.abs(ys - median) < 0.02))

    if verbose:
        print(
            f"  waist string: {n_frames_used} frames, {len(ys)} pts, "
            f"median Y={median:.3f} m, p10={p10:.3f}, p90={p90:.3f}, "
            f"inlier ratio (±20 mm) = {inliers:.2f}")

    return WaistStringDetection(
        y_m=median,
        n_frames_used=n_frames_used,
        n_points=int(len(ys)),
        median_y_m=median,
        p10_y_m=p10,
        p90_y_m=p90,
        inlier_ratio=inliers,
        color=color if (hsv_low is None and hsv_high is None) else "custom",
        hsv_low=hsv_low,
        hsv_high=hsv_high,
    )
