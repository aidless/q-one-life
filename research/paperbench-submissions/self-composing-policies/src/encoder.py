"""ALE CNN state encoder (Appendix E.1).

conv 32@8 -> conv 64@4 -> conv 64@3 -> dense 512.
A single encoder is created per policy module and initialised from the
previous module's encoder weights (Section 4.1).
"""

from __future__ import annotations

import copy

import torch
import torch.nn as nn


class ALEEncoder(nn.Module):
    D_OUT = 512

    def __init__(self, in_channels: int = 4, dense_dim: int = 512):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 32, kernel_size=8, stride=4)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=4, stride=2)
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1)
        self.act = nn.ReLU()
        self.dense = nn.LazyLinear(dense_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, C, 210, 160]
        h = self.act(self.conv1(x))
        h = self.act(self.conv2(h))
        h = self.act(self.conv3(h))
        return self.act(self.dense(h.flatten(1)))

    def clone_with_init(self) -> "ALEEncoder":
        """New encoder initialised with this encoder's weights (Section 4.1)."""
        new = ALEEncoder()
        with torch.no_grad():
            self(torch.zeros(1, 4, 210, 160))  # materialise the lazy dense layer
            new(torch.zeros(1, 4, 210, 160))
        new.load_state_dict(copy.deepcopy(self.state_dict()))
        return new
