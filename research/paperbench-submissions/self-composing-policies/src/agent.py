"""A CompoNet actor plus the shared critic, wired as an agent (Section 4.1).

- One encoder per module; a new module's encoder is initialised from the
  previous module's encoder weights.
- The encoder output h_s feeds both CompoNet (actor) and the single-layer
  value function (critic).
- At task k, modules 1..k-1 are evaluated on the current state to build Phi;
  only module k is trainable, all earlier modules are frozen.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from .componet import CompoNetModule
from .encoder import ALEEncoder


class CompoNetAgent(nn.Module):
    def __init__(self, d_enc: int = 512, d_model: int = 64, n_actions: int = 6,
                 continuous: bool = False, use_cnn: bool = True):
        super().__init__()
        self.d_enc = d_enc
        self.d_model = d_model
        self.n_actions = n_actions
        self.continuous = continuous
        self.use_cnn = use_cnn

        self.encoders = nn.ModuleList()
        self.policy_modules = nn.ModuleList()
        self.critic = nn.Linear(d_enc, 1)  # critic is re-created per task in training

    # ---- module lifecycle -------------------------------------------------
    def add_module(self, init_from_previous: bool = True) -> int:
        encoder = ALEEncoder() if self.use_cnn else nn.Identity()
        if init_from_previous and len(self.encoders) > 0 and isinstance(encoder, ALEEncoder):
            encoder = self.encoders[-1].clone_with_init()
        self.encoders.append(encoder)
        self.policy_modules.append(CompoNetModule(self.d_enc, self.d_model, self.n_actions,
                                           continuous=self.continuous))
        return len(self.policy_modules) - 1

    def freeze_all_but_last(self) -> None:
        for p in self.parameters():
            p.requires_grad = False
        for p in self.policy_modules[-1].parameters():
            p.requires_grad = True
        for p in self.encoders[-1].parameters():
            p.requires_grad = True

    # ---- inference --------------------------------------------------------
    def encode(self, state: torch.Tensor) -> torch.Tensor:
        return self.encoders[-1](state)

    def forward(self, state: torch.Tensor, upto: int | None = None):
        """Returns (out, phi, h_s) for the module at index ``upto`` (default: last)."""
        if upto is None:
            upto = len(self.policy_modules) - 1
        h_s_list = [self.encoders[j](state) for j in range(upto + 1)]
        phi_list = []
        for j in range(upto):
            mod = self.policy_modules[j]
            prev = torch.stack(phi_list, dim=1) if phi_list else torch.zeros(
                state.shape[0], 0, self.n_actions, device=state.device)
            out_j, _ = mod(h_s_list[j], prev)
            phi_list.append(out_j)
        phi = torch.stack(phi_list, dim=1) if phi_list else torch.zeros(
            state.shape[0], 0, self.n_actions, device=state.device)
        out, v = self.policy_modules[upto](h_s_list[upto], phi)
        return out, phi, h_s_list[upto]

    def parameter_accounting(self) -> dict:
        # Materialise lazy layers first so every parameter has a known shape.
        if len(self.policy_modules) > 0:
            with torch.no_grad():
                self(torch.zeros(1, 4, 210, 160))
        per_module = [sum(p.numel() for p in m.parameters()) for m in self.policy_modules]
        return {
            "n_modules": len(self.policy_modules),
            "per_module_params": per_module,
            "total_module_params": sum(per_module),
            "total_params": sum(p.numel() for p in self.parameters()),
        }
