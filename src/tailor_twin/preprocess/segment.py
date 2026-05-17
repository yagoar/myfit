"""Body-segmentation alpha masks for Stray Scanner frames.

Per-frame RGB → soft alpha (H×W float32 in [0, 1]). Returned masks are
applied to the depth map (resampled to depth resolution) so TSDF
fusion only integrates the subject's body, not the wall behind / the
floor / the helper's hand.

Backends (pluggable):
  - ``rembg``   — U2Net body matting via the ``rembg`` package. Works
    image-by-image, no recurrent state. Easiest install, decent edges.
    Default when ``rembg`` is importable.
  - ``rvm``     — Robust Video Matting (PeterL1n/RobustVideoMatting).
    Recurrent over the frame sequence — cleanest hair edges, best for
    a 25-30 s capture loop. Requires torch.hub network on first run
    to download MobileNetV3 weights.
  - ``depth_threshold`` — fallback that uses depth alone. No RGB. Picks
    pixels within a depth window and the largest depth-connected
    component (= the subject if standing alone in a clear ~2 m area).
    Always available. Lower quality at edges but zero new deps.

The CLI selects via ``--seg-backend``. Code that prefers a specific
backend can call ``Segmenter(backend="rvm")`` directly.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Iterable, Iterator

import cv2
import numpy as np


# Backend registry — each entry is (label, importable module name).
_BACKENDS = {
    "rembg":           "rembg",
    "rvm":             "torch",          # torch.hub.load fetches RVM
    "depth_threshold": None,              # no extra dep
}


def available_backends() -> list[str]:
    """Backends that can run on this machine right now (deps importable)."""
    avail = ["depth_threshold"]
    for name, mod in _BACKENDS.items():
        if mod is None or name in avail:
            continue
        try:
            importlib.import_module(mod)
            avail.append(name)
        except ImportError:
            pass
    return avail


# ---------------------------------------------------------------------------
# Depth-only fallback.
# ---------------------------------------------------------------------------


def _connected_component_mask(
    depth_mm: np.ndarray, min_pixels: int = 200,
) -> np.ndarray:
    """Largest connected component of non-zero depth pixels."""
    binary = (depth_mm > 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if n < 2:
        return binary.astype(bool)
    sizes = stats[1:, cv2.CC_STAT_AREA]
    best = 1 + int(np.argmax(sizes))
    if sizes[best - 1] < min_pixels:
        return binary.astype(bool)
    return labels == best


def _segment_depth_threshold(depth_mm: np.ndarray) -> np.ndarray:
    """Alpha = 1 inside the largest connected non-zero-depth blob, else 0.

    Assumes ``depth_mm`` has already been filtered (min/max range +
    confidence) — this function only enforces the largest-blob rule on
    whatever survives.
    """
    mask = _connected_component_mask(depth_mm)
    return mask.astype(np.float32)


# ---------------------------------------------------------------------------
# rembg backend (image-at-a-time).
# ---------------------------------------------------------------------------


class _RembgSegmenter:
    def __init__(self):
        from rembg import new_session
        # u2net_human_seg is tuned for full-body people.
        self.session = new_session(model_name="u2net_human_seg")

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        from rembg import remove
        rgba = remove(rgb, session=self.session,
                      only_mask=False, force_return_bytes=False)
        # rembg returns RGBA uint8; take the alpha channel and normalise.
        if rgba.ndim == 3 and rgba.shape[-1] == 4:
            alpha = rgba[..., 3]
        else:
            alpha = rgba
        return alpha.astype(np.float32) / 255.0


# ---------------------------------------------------------------------------
# RVM backend (recurrent over the sequence).
# ---------------------------------------------------------------------------


class _RVMSegmenter:
    def __init__(self):
        import torch
        self.torch = torch
        # MobileNetV3 variant — small, CPU-friendly.
        self.model = torch.hub.load(
            "PeterL1n/RobustVideoMatting",
            "mobilenetv3",
            trust_repo=True,
        )
        self.model.eval()
        self.rec = [None] * 4  # recurrent state — RVM expects 4 tensors

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        torch = self.torch
        src = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        src = src.unsqueeze(0)  # (1, 3, H, W)
        with torch.no_grad():
            fgr, pha, *rec = self.model(src, *self.rec, downsample_ratio=0.4)
        self.rec = rec
        alpha = pha.detach()[0, 0].cpu().numpy()
        return alpha.astype(np.float32)


# ---------------------------------------------------------------------------
# Public surface.
# ---------------------------------------------------------------------------


@dataclass
class SegResult:
    """Alpha + meta for one frame."""
    alpha_rgb: np.ndarray | None       # H_rgb × W_rgb float32 in [0, 1]
    alpha_depth: np.ndarray            # H_depth × W_depth float32 in [0, 1]


class Segmenter:
    """Pluggable per-frame body segmenter.

    Construct once, call frame-by-frame. Maintains RVM recurrent state
    across calls when the backend supports it.
    """

    def __init__(self, backend: str = "rembg"):
        if backend not in _BACKENDS:
            raise ValueError(
                f"unknown segmentation backend {backend!r}; "
                f"available: {sorted(_BACKENDS)}")
        self.backend = backend
        if backend == "rembg":
            self.impl = _RembgSegmenter()
        elif backend == "rvm":
            self.impl = _RVMSegmenter()
        elif backend == "depth_threshold":
            self.impl = None
        else:
            raise AssertionError("unreachable")

    def segment(
        self,
        rgb: np.ndarray | None,
        depth_mm: np.ndarray,
    ) -> SegResult:
        """Compute alpha at both RGB and depth resolutions.

        ``rgb`` is required for rembg / rvm; ignored by depth_threshold.
        ``depth_mm`` is required for depth_threshold and for resizing
        the RGB alpha down to depth resolution.
        """
        if self.backend == "depth_threshold":
            alpha_d = _segment_depth_threshold(depth_mm)
            return SegResult(alpha_rgb=None, alpha_depth=alpha_d)
        if rgb is None:
            raise ValueError(
                f"backend {self.backend!r} needs an RGB frame")
        alpha_rgb = self.impl(rgb)
        # Resize to depth resolution. INTER_AREA is right for downsampling.
        h, w = depth_mm.shape
        alpha_d = cv2.resize(alpha_rgb, (w, h),
                              interpolation=cv2.INTER_AREA)
        return SegResult(alpha_rgb=alpha_rgb, alpha_depth=alpha_d)


def segment_stream(
    frames: Iterable, *, backend: str = "rembg",
) -> Iterator[tuple[object, SegResult]]:
    """Lazy iterator: yield ``(frame, SegResult)`` for each input frame.

    Lets pipeline code thread through one frame at a time without
    holding the whole sequence in memory.
    """
    seg = Segmenter(backend=backend)
    for f in frames:
        yield f, seg.segment(f.rgb, f.depth_mm)
