"""VPoser v1 loader for SMPL-X fitting.

VPoser is the variational auto-encoder pose prior trained on AMASS
(https://amass.is.tue.mpg.de). Used by SMPLify-X to regularise body_pose
via L2 on a 32D latent embedding rather than L2 on raw axis-angle pose.

This loads VPoser v1.0 (`vposer_v1_0/snapshots/TR00_E096.pt`).

The released v1 code depends on `torchgeometry` whose `matrot2aa` path
is broken under modern PyTorch (`1 - bool_tensor`). We bypass that by
decoding to rotation matrices and converting with `roma.rotmat_to_rotvec`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import roma
import torch


class VPoserWrapper:
    """Differentiable VPoser decoder z (32D) -> body_pose (B, 21, 3) axis-angle."""

    def __init__(self, ckpt_path: Path | str, device: str | torch.device = "cpu"):
        ckpt_path = Path(ckpt_path)
        # The v1 release ships its model definition alongside the checkpoint.
        vposer_pkg_dir = ckpt_path.parent.parent
        if str(vposer_pkg_dir) not in sys.path:
            sys.path.insert(0, str(vposer_pkg_dir))
        from vposer_smpl import VPoser  # noqa: E402

        self.device = torch.device(device)
        self.model = VPoser(num_neurons=512, latentD=32, data_shape=[1, 21, 3])
        state = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(state)
        self.model.eval()
        self.model.to(self.device)
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.latent_dim = 32

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """z: (B, 32) -> body_pose axis-angle (B, 21, 3)."""
        matrot = self.model.decode(z, output_type="matrot").view(-1, 21, 3, 3)
        return roma.rotmat_to_rotvec(matrot)

    @staticmethod
    def default_ckpt() -> Path:
        return Path("data/vposer/vposer_v1_0/snapshots/TR00_E096.pt")
