"""CompoNet self-composing policy module (Section 4.2).

Shapes follow the paper literally; E_out / E_in are positional encodings with
the same shape as the matrix they are added to (rows x |A|), built from a
cosine schedule over flattened positions.

Output attention head (learnable: W_out^Q, W_out^K)
    q = h_s W_out^Q           W_out^Q : d_enc x d_model
    K = (Phi + E_out) W_out^K W_out^K : |A| x d_model
    V = Phi
    v = softmax(q K^T / sqrt(d_model)) V

Input attention head (learnable: W_in^Q, W_in^K, W_in^V)
    P = row-concat(v, Phi)    rows = k
    q = h_s W_in^Q
    K = (P + E_in) W_in^K
    V = P W_in^V
    u = softmax(q K^T / sqrt(d_model)) V

Internal policy
    out = v + MLP([h_s ; u])  (normalised for continuous action spaces)
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


def cosine_positional_matrix(n_rows: int, n_cols: int) -> torch.Tensor:
    """Cosine positional encoding with the same shape as the target matrix."""
    if n_rows <= 0:
        return torch.zeros(0, n_cols)
    pos = torch.arange(n_rows * n_cols, dtype=torch.float32).reshape(n_rows, n_cols)
    # Normalise positions into [0, 1) then map through a cosine schedule, as in
    # the sinusoidal encoding used by Vaswani et al. (2017).
    normalised = pos / float(max(n_rows * n_cols - 1, 1))
    return torch.cos(normalised * math.pi)


class CompoNetModule(nn.Module):
    def __init__(self, d_enc: int, d_model: int, n_actions: int,
                 continuous: bool = False, hidden: int = 64):
        super().__init__()
        self.d_enc = d_enc
        self.d_model = d_model
        self.n_actions = n_actions
        self.continuous = continuous

        self.W_out_Q = nn.Linear(d_enc, d_model, bias=False)
        self.W_out_K = nn.Linear(n_actions, d_model, bias=False)

        self.W_in_Q = nn.Linear(d_enc, d_model, bias=False)
        self.W_in_K = nn.Linear(n_actions, d_model, bias=False)
        self.W_in_V = nn.Linear(n_actions, n_actions, bias=False)

        self.mlp = nn.Sequential(
            nn.Linear(d_enc + n_actions, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, n_actions),
        )

    @staticmethod
    def _pos(n_rows: int, n_cols: int, like: torch.Tensor) -> torch.Tensor:
        return cosine_positional_matrix(n_rows, n_cols).to(like.dtype).to(like.device)

    def forward(self, h_s: torch.Tensor, phi: torch.Tensor):
        """Returns (out, v). h_s: [B,d_enc]; phi: [B,k-1,|A|] (k-1 may be 0)."""
        B = h_s.shape[0]
        k_prev = phi.shape[1]

        if k_prev > 0:
            q = self.W_out_Q(h_s).unsqueeze(1)                       # [B,1,d_model]
            keys_in = phi + self._pos(k_prev, self.n_actions, phi)    # [B,k-1,|A|]
            K = self.W_out_K(keys_in).transpose(1, 2)                 # [B,d_model,k-1]
            att = torch.softmax(q @ K / math.sqrt(self.d_model), dim=-1)
            v = (att @ phi).squeeze(1)                               # [B,|A|]
            P = torch.cat([v.unsqueeze(1), phi], dim=1)              # [B,k,|A|]
        else:
            v = torch.zeros(B, self.n_actions, device=h_s.device, dtype=h_s.dtype)
            P = v.unsqueeze(1)

        rows = P.shape[1]
        q_in = self.W_in_Q(h_s).unsqueeze(1)
        keys_in = P + self._pos(rows, self.n_actions, P)
        K_in = self.W_in_K(keys_in).transpose(1, 2)
        V_in = self.W_in_V(P)
        att_in = torch.softmax(q_in @ K_in / math.sqrt(self.d_model), dim=-1)
        u = (att_in @ V_in).squeeze(1)

        out = v + self.mlp(torch.cat([h_s, u], dim=-1))
        if self.continuous:
            out = F.normalize(out, dim=-1)
        return out, v

    def core_parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())
