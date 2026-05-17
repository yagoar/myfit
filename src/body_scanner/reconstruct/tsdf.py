"""TSDF fusion of segmented + filtered Stray Scanner frames into a mesh.

Open3D's ``ScalableTSDFVolume`` integrates per-frame RGB-D + extrinsics.
Body-scale presets:

  voxel_length = 5 mm    # noise vs detail balance for a ~1.8 m subject
  sdf_trunc    = 20 mm   # 4× voxel_length per Open3D best-practice

We integrate world←camera extrinsics (Open3D convention) — Stray gives
camera→world (ARKit / right-handed +Y up), so we invert.

Confidence + depth-range filtering and body segmentation must be
applied to ``depth_mm`` *before* integration. This module does the
fusion only and assumes the inputs are already body-masked.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import open3d as o3d


# Body-scale TSDF presets. Tunable from the CLI.
DEFAULT_VOXEL_M = 0.005           # 5 mm
DEFAULT_SDF_TRUNC_M = 0.020       # 4× voxel
DEFAULT_DEPTH_TRUNC_M = 3.0       # hard ceiling beyond which depth is dropped
DEFAULT_DEPTH_SCALE = 1000.0      # Stray depth_mm → metres


@dataclass
class FusionInput:
    """One frame's contribution to TSDF integration.

    ``depth_mm``    H×W uint16, mm, already segmentation-masked.
    ``intrinsics``  3×3, in the depth-image pixel grid.
    ``pose_c2w``    4×4 camera→world SE(3) (Stray's odometry convention).
    """
    depth_mm: np.ndarray
    intrinsics: np.ndarray
    pose_c2w: np.ndarray


def _intrinsics_to_o3d(K: np.ndarray, width: int, height: int) -> o3d.camera.PinholeCameraIntrinsic:
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    return o3d.camera.PinholeCameraIntrinsic(
        width=width, height=height, fx=fx, fy=fy, cx=cx, cy=cy,
    )


def _maybe_rescale_intrinsics(
    K: np.ndarray, native_size: tuple[int, int] | None,
    depth_size: tuple[int, int],
) -> np.ndarray:
    """Stray's odometry intrinsics may be in the RGB resolution. Open3D
    needs them in the same pixel grid as the depth image. If
    ``native_size`` is given and differs from the depth size, rescale
    fx/fy/cx/cy proportionally.

    Stray docs flag this as an open question (see io/stray_loader.py
    module docstring) — passing the rescale lets the caller resolve it
    once and forward consistent intrinsics here.
    """
    if native_size is None or native_size == depth_size:
        return K
    nw, nh = native_size
    dw, dh = depth_size
    sx = dw / nw
    sy = dh / nh
    Kp = K.copy().astype(np.float64)
    Kp[0, 0] *= sx        # fx
    Kp[1, 1] *= sy        # fy
    Kp[0, 2] *= sx        # cx
    Kp[1, 2] *= sy        # cy
    return Kp


def fuse_frames(
    inputs: Iterable[FusionInput],
    *,
    voxel_length: float = DEFAULT_VOXEL_M,
    sdf_trunc: float = DEFAULT_SDF_TRUNC_M,
    depth_trunc: float = DEFAULT_DEPTH_TRUNC_M,
    depth_scale: float = DEFAULT_DEPTH_SCALE,
    intrinsics_native_size: tuple[int, int] | None = None,
    progress: bool = True,
) -> o3d.geometry.TriangleMesh:
    """Integrate frames into a TSDF volume and return the extracted mesh.

    ``intrinsics_native_size`` (width, height) is the pixel grid in
    which Stray reports fx/fy/cx/cy. If None, the intrinsics are
    assumed to already match the depth resolution.
    """
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_length,
        sdf_trunc=sdf_trunc,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.NoColor,
    )
    count = 0
    for fi in inputs:
        h, w = fi.depth_mm.shape
        K = _maybe_rescale_intrinsics(
            fi.intrinsics, intrinsics_native_size, (w, h))
        intr = _intrinsics_to_o3d(K, width=w, height=h)
        depth_o3d = o3d.geometry.Image(fi.depth_mm.astype(np.uint16))
        # Make a placeholder RGB the same size as depth; Open3D's
        # create_from_color_and_depth requires both even when fusing
        # without colour. Use a black single-channel image.
        rgb_dummy = o3d.geometry.Image(
            np.zeros((h, w, 3), dtype=np.uint8))
        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color=rgb_dummy,
            depth=depth_o3d,
            depth_scale=depth_scale,
            depth_trunc=depth_trunc,
            convert_rgb_to_intensity=False,
        )
        # Open3D wants world→camera extrinsics; Stray gives camera→world.
        extr = np.linalg.inv(fi.pose_c2w)
        volume.integrate(rgbd, intr, extr)
        count += 1
        if progress and count % 50 == 0:
            print(f"  TSDF: integrated {count} frames")
    if count == 0:
        raise RuntimeError("fuse_frames: no inputs supplied")
    if progress:
        print(f"  TSDF: extracting mesh ({count} frames integrated)")
    mesh = volume.extract_triangle_mesh()
    mesh.compute_vertex_normals()
    return mesh


def save_mesh_obj(mesh: o3d.geometry.TriangleMesh, path: Path) -> None:
    """Write the fused mesh as Wavefront OBJ for the SMPL-X fit step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    o3d.io.write_triangle_mesh(str(path), mesh,
                                write_ascii=True, write_vertex_normals=True)
