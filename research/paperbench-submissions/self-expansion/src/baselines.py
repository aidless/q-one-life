"""Baseline adapters for the SEMA comparison.

- items 32-34: Finetune Adapter — one SEMA adapter in every layer, backbone
  frozen, adapters updated continuously across the whole stream.
- items 7-9: LoRA / Convpass / ADAM-Adapter are provided in ``adapters.py`` and
  are selectable here.
"""

from __future__ import annotations

import torch.nn as nn

from .adapters import FunctionalAdapter


class FinetuneAdapterModel(nn.Module):
    """Frozen ViT with one trainable functional adapter per block."""

    def __init__(self, base, dim: int = 768):
        super().__init__()
        self.base = base
        self.adapters = nn.ModuleList([FunctionalAdapter(dim) for _ in range(base.num_blocks)])
        self.head = nn.Linear(dim, base.num_classes)
        for p in self.base.vit.parameters():
            p.requires_grad = False

    def forward(self, x, return_features=False):
        feats = self.base._forward_features_with_adapters(x, self.adapters)
        logits = self.head(feats[:, 0])
        if return_features:
            return logits, feats[:, 0]
        return logits


def make_finetune_model(base):
    for li in base.expandable_layers:
        base.vit.blocks[li].add_module_pair()
    for li in base.expandable_layers:
        base.vit.blocks[li].set_trainable("all")
    for p in base.head.parameters():
        p.requires_grad = True
    return base


def adapter_spec(kind: str) -> dict:
    return {
        "lora": {"rank": 8},          # item 7
        "convpass": {"bottleneck": 48},  # item 8
        "adam": {"bottleneck": 48},    # item 9
        "functional": {"bottleneck": 48},  # item 10/50
    }[kind]
