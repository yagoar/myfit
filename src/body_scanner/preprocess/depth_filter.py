"""Depth + confidence filtering for Stray Scanner frames.

Drops pixels that are too far, too close, or low-confidence. Optional
bilateral smooth preserves edges while reducing the LiDAR's per-pixel
noise floor (~5 mm at 1 m).

Stray's confidence map values per the format doc:
  0 — unreliable (often missing returns)
  1 — medium (works but noisy)
  2 — highest (preferred)

We default to ``min_confidence=2`` to keep only the cleanest depth.
Bumps the per-frame "valid pixel" count down but TSDF fusion over a
25-30 s loop accumulates plenty of redundancy.
"""
from __future__ import annotations

import cv2
import numpy as np


# Stray Scanner depth is 16-bit PNG in millimetres. These are the body-
# scanner working ranges expressed in millimetres so the filter doesn't
# need to convert depth_mm → m before thresholding.
DEFAULT_MIN_DEPTH_MM = 400    # closer than this is the helper's hand etc.
DEFAULT_MAX_DEPTH_MM = 2500   # wall / floor / clutter beyond the subject
DEFAULT_MIN_CONFIDENCE = 2    # Stray's "highest" tier only


def confidence_histogram(confidence: np.ndarray) -> dict[int, int]:
    """Count pixels per Stray confidence tier (0, 1, 2)."""
    if confidence is None:
        return {}
    return {int(k): int(v)
            for k, v in zip(*np.unique(confidence, return_counts=True))}


def filter_depth(
    depth_mm: np.ndarray,
    confidence: np.ndarray | None = None,
    *,
    min_depth_mm: int = DEFAULT_MIN_DEPTH_MM,
    max_depth_mm: int = DEFAULT_MAX_DEPTH_MM,
    min_confidence: int = DEFAULT_MIN_CONFIDENCE,
    bilateral: bool = True,
) -> np.ndarray:
    """Return a copy of ``depth_mm`` with rejected pixels set to 0.

    ``depth_mm``    uint16, raw Stray depth (PNG values in mm).
    ``confidence``  uint8 in {0, 1, 2}; None disables the confidence test.
    ``bilateral``   apply a 5×5 cross-bilateral smooth to the kept depth
                    pixels. Reduces per-pixel jitter without crossing
                    silhouette edges.
    """
    out = depth_mm.copy()
    mask = (out >= min_depth_mm) & (out <= max_depth_mm)
    if confidence is not None:
        mask &= confidence >= min_confidence
    out[~mask] = 0
    if bilateral and mask.any():
        # cv2.bilateralFilter wants float32 / uint8; convert and back.
        f = out.astype(np.float32)
        # 5-px diameter, sigmaColor in depth units, sigmaSpace in pixels.
        sm = cv2.bilateralFilter(f, d=5, sigmaColor=30.0, sigmaSpace=2.0)
        sm[~mask] = 0
        out = sm.astype(np.uint16)
    return out


def apply_alpha_mask(
    depth_mm: np.ndarray, alpha: np.ndarray, *, threshold: float = 0.5,
) -> np.ndarray:
    """Zero out depth pixels where the alpha mask < threshold.

    ``alpha``  same H×W as ``depth_mm``, float in [0, 1] (resampled from
    the RGB resolution if needed by the caller). Used to drop background
    pixels identified by a segmentation pass.
    """
    if alpha.shape != depth_mm.shape:
        raise ValueError(
            f"alpha shape {alpha.shape} != depth shape {depth_mm.shape}")
    out = depth_mm.copy()
    out[alpha < threshold] = 0
    return out
