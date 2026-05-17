"""Visualisation helpers for SMPL-X fit results.

GUARDRAILS §4: distance heatmap inspection is mandatory before trusting a
fit for measurement extraction.
"""
from __future__ import annotations

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree


def per_vertex_distance(
    smplx_verts: np.ndarray, scan_verts: np.ndarray
) -> np.ndarray:
    """Nearest-neighbour distance from each SMPL-X vertex to the scan."""
    tree = cKDTree(scan_verts)
    d, _ = tree.query(smplx_verts)
    return d


def heatmap_colors(
    distances: np.ndarray, vmax: float | None = None
) -> np.ndarray:
    """Map distances in [0, vmax] to RGB. Blue=close, red=far."""
    vmax = vmax if vmax is not None else float(np.percentile(distances, 95))
    vmax = max(vmax, 1e-6)
    t = np.clip(distances / vmax, 0.0, 1.0)
    # Blue (0,0,1) -> green (0,1,0) -> red (1,0,0)
    r = np.clip(2.0 * t - 1.0, 0.0, 1.0)
    g = np.clip(2.0 * np.minimum(t, 1.0 - t), 0.0, 1.0)
    b = np.clip(1.0 - 2.0 * t, 0.0, 1.0)
    return np.stack([r, g, b], axis=1)


def visualize_fit(
    scan_verts: np.ndarray,
    scan_faces: np.ndarray,
    fitted_smplx_verts: np.ndarray,
    smplx_faces: np.ndarray,
    *,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Open an interactive viewer with the scan (grey, semi-transparent) and
    the fitted SMPL-X mesh coloured by per-vertex distance to scan."""
    d = per_vertex_distance(fitted_smplx_verts, scan_verts)
    colors = heatmap_colors(d, vmax=0.05)  # cap at 5cm for readability

    smplx_mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(fitted_smplx_verts),
        o3d.utility.Vector3iVector(smplx_faces),
    )
    smplx_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    smplx_mesh.compute_vertex_normals()

    scan_mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(scan_verts),
        o3d.utility.Vector3iVector(scan_faces),
    )
    scan_mesh.paint_uniform_color([0.7, 0.7, 0.7])
    scan_mesh.compute_vertex_normals()

    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=0.2, origin=[0, 0, 0]
    )

    print(
        f"distance stats — mean={d.mean()*1000:.1f}mm  "
        f"median={np.median(d)*1000:.1f}mm  "
        f"p95={np.percentile(d, 95)*1000:.1f}mm  "
        f"max={d.max()*1000:.1f}mm"
    )

    if show:
        o3d.visualization.draw_geometries(
            [smplx_mesh, scan_mesh, axes],
            window_name="SMPL-X fit — heatmap on fitted mesh (blue=close, red=far)",
            width=1100,
            height=1100,
            mesh_show_back_face=True,
        )
    if save_path is not None:
        o3d.io.write_triangle_mesh(save_path, smplx_mesh)
