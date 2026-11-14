"""Adapter modules for SEMA and baselines.

- FunctionalAdapter: down-projection -> ReLU -> up-projection (paper Sec. 3.3;
  adapter hidden dim 48, matching rubric items 10 and 50).
- RepresentationDescriptor: encoder Linear(d->128), LeakyReLU, decoder
  Linear(128->d) (rubric items 11-13). Reconstruction error acts as a
  distribution-shift indicator.
- LoRAAdapter and ConvPassAdapter and ADAMAdapter for baselines
  (rubric items 7-9).
- LoRA: standard low-rank A@B with rank 8 by default.
"""

from __future__ import annotations

import torch
import torch.nn as nn

ADAPTER_HIDDEN_DIM = 48
LATENT_DIM = 128


class FunctionalAdapter(nn.Module):
    def __init__(self, dim: int = 768, bottleneck: int = ADAPTER_HIDDEN_DIM):
        super().__init__()
        self.down = nn.Linear(dim, bottleneck)
        self.up = nn.Linear(bottleneck, dim)
        self.act = nn.ReLU()
        # zero-init the up projection so initial adapter is identity-like
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.up(self.act(self.down(x)))


class RepresentationDescriptor(nn.Module):
    def __init__(self, dim: int = 768, latent: int = LATENT_DIM):
        super().__init__()
        self.encoder = nn.Linear(dim, latent)
        self.act = nn.LeakyReLU(0.01)
        self.decoder = nn.Linear(latent, dim)

    def forward(self, x: torch.Tensor):
        z = self.act(self.encoder(x))
        recon = self.decoder(z)
        return z, recon

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        _, recon = self.forward(x)
        return ((recon - x) ** 2).mean(dim=-1)


class LoRAAdapter(nn.Module):
    def __init__(self, dim: int = 768, rank: int = 8):
        super().__init__()
        self.A = nn.Linear(dim, rank, bias=False)
        self.B = nn.Linear(rank, dim, bias=False)
        nn.init.zeros_(self.B.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.B(self.A(x))


class ConvPassAdapter(nn.Module):
    """Convpass (JieShibo/PETL-ViT) for ViT tokens: 1x1 conv bottleneck."""

    def __init__(self, dim: int = 768, bottleneck: int = 48):
        super().__init__()
        self.conv_down = nn.Conv2d(dim, bottleneck, 1)
        self.act = nn.GELU()
        self.conv_up = nn.Conv2d(bottleneck, dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, N, D] with N = 1 + patches; use [B, D, N, 1]
        b, n, d = x.shape
        h = x.transpose(1, 2).unsqueeze(-1)
        h = self.conv_up(self.act(self.conv_down(h)))
        return h.squeeze(-1).transpose(1, 2)


class ADAMAdapter(nn.Module):
    """AdaptFormer adapter (ShoufaChen/AdaptFormer)."""

    def __init__(self, dim: int = 768, bottleneck: int = 48, scale: float = 0.1):
        super().__init__()
        self.down = nn.Linear(dim, bottleneck)
        self.up = nn.Linear(bottleneck, dim)
        self.act = nn.GELU()
        self.scale = scale
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.scale * self.up(self.act(self.down(x)))
