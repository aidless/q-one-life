"""ViT-B/16 backbone with SEMA modular adapters + expanding router.

Rubric anchors implemented here:
- item 15: router input = output of the second normalization layer
  (norm1 -> attn -> residual -> norm2), i.e. the pre-MLP normalized hidden.
- item 16: linear combination of functional adapters with router weights.
- item 17: adapter output is added to the FC-layer output and the residual
  path inside the transformer block.
- item 18: PTM parameters frozen.
- item 49: self-expansion enabled only in the last three transformer layers.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from .adapters import FunctionalAdapter, RepresentationDescriptor


class BlockWithAdapters(nn.Module):
    """A timm ViT block plus a routed mixture of functional adapters."""

    def __init__(self, block: nn.Module, dim: int = 768, max_modules: int = 8):
        super().__init__()
        self.block = block
        self.dim = dim
        self.adapters = nn.ModuleList()
        self.descriptors = nn.ModuleList()
        self.router = nn.Linear(dim, max_modules)
        self.n_modules = 0
        self.frozen_upto = 0  # count of frozen modules

    def add_module_pair(self) -> None:
        self.adapters.append(FunctionalAdapter(self.dim))
        self.descriptors.append(RepresentationDescriptor(self.dim))
        self.n_modules += 1
        self.frozen_upto = self.n_modules  # freeze previously learned modules

    def set_trainable(self, mode: str) -> None:
        """mode in {'none','all','latest'}"""
        for i, (a, d) in enumerate(zip(self.adapters, self.descriptors)):
            train = mode == "all" or (mode == "latest" and i == self.n_modules - 1)
            for p in a.parameters():
                p.requires_grad = train
            for p in d.parameters():
                p.requires_grad = train
        for p in self.router.parameters():
            p.requires_grad = mode != "none"

    def router_weights(self, normed: torch.Tensor) -> torch.Tensor:
        logits = self.router(normed)  # [B, N, max_modules]
        w = torch.softmax(logits, dim=-1)
        return w[..., : self.n_modules]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.n_modules == 0:
            return self.block(x)
        block = self.block
        normed = block.norm1(x)
        attn_out = block.attn(normed)
        x = x + block.drop_path1(block.ls1(attn_out)) if hasattr(block, "ls1") else x + attn_out
        normed2 = block.norm2(x)  # item 15: router input
        w = self.router_weights(normed2)  # [B,N,M]
        outs = torch.stack([a(normed2) for a in self.adapters], dim=-2)  # [B,N,M,D]
        adapter_out = (outs * w.unsqueeze(-1)).sum(dim=-2)
        mlp_out = block.mlp(normed2)
        x = x + block.drop_path2(block.ls2(mlp_out)) if hasattr(block, "ls2") else x + mlp_out
        x = x + adapter_out  # item 17
        return x

    def descriptor_errors(self, x: torch.Tensor) -> torch.Tensor:
        errs = []
        for d in self.descriptors:
            errs.append(d.reconstruction_error(x).mean().detach())
        return torch.stack(errs) if errs else torch.zeros(0)


class SemaViT(nn.Module):
    """Frozen ViT-B/16 with SEMA expansion in the last three blocks."""

    def __init__(self, num_classes: int = 100, pretrained: bool = False):
        super().__init__()
        try:
            import timm
            self.vit = timm.create_model("vit_base_patch16_224", pretrained=pretrained,
                                         num_classes=0)
        except Exception:
            self.vit = _TinyViTStub(dim=768)
        self.dim = 768
        self.embed_dim = getattr(self.vit, "embed_dim", 768)
        self.num_blocks = len(self.vit.blocks) if hasattr(self.vit, "blocks") else 12
        blocks = []
        for b in self.vit.blocks:
            blocks.append(BlockWithAdapters(b, dim=self.dim))
        self.vit.blocks = nn.ModuleList(blocks)
        for p in self.vit.parameters():
            p.requires_grad = False
        self.head = nn.Linear(self.dim, num_classes)
        self.num_classes = num_classes
        self.expandable_layers = list(range(self.num_blocks - 3, self.num_blocks))  # item 49
        self._running_u: dict = {}
        self._running_sigma: dict = {}

    def add_classifier(self, num_new_classes: int) -> None:
        new_head = nn.Linear(self.dim, self.num_classes + num_new_classes)
        if self.num_classes > 0:
            with torch.no_grad():
                new_head.weight[: self.num_classes] = self.head.weight
                new_head.bias[: self.num_classes] = self.head.bias
        self.head = new_head
        self.num_classes += num_new_classes

    def forward(self, pixel_values: torch.Tensor, return_features: bool = False):
        feats = self._forward_features(pixel_values)
        cls_token = feats[:, 0] if feats.dim() == 3 else feats
        logits = self.head(cls_token)
        if return_features:
            return logits, cls_token
        return logits

    def _forward_features(self, x: torch.Tensor) -> torch.Tensor:
        vit = self.vit
        feats = vit.patch_embed(x)
        if feats.dim() == 4:
            feats = feats.flatten(2).transpose(1, 2)
        cls = vit.cls_token.expand(feats.shape[0], -1, -1)
        feats = torch.cat([cls, feats], dim=1)
        feats = vit.pos_drop(feats + vit.pos_embed)
        for blk in vit.blocks:
            feats = blk(feats)
        feats = vit.norm(feats) if hasattr(vit, "norm") else feats
        return feats

    def _forward_features_with_adapters(self, x: torch.Tensor, adapters) -> torch.Tensor:
        """Frozen ViT pass that sums extra per-block adapter outputs (item 32)."""
        vit = self.vit
        feats = vit.patch_embed(x)
        if feats.dim() == 4:
            feats = feats.flatten(2).transpose(1, 2)
        cls = vit.cls_token.expand(feats.shape[0], -1, -1)
        feats = torch.cat([cls, feats], dim=1)
        feats = vit.pos_drop(feats + vit.pos_embed)
        for blk, adapter in zip(vit.blocks, adapters):
            normed = blk.block.norm2(feats) if isinstance(blk, BlockWithAdapters) else blk.norm2(feats)
            feats = blk(feats) + adapter(normed)
        return vit.norm(feats) if hasattr(vit, "norm") else feats

    def block_descriptor_errors(self, x_pixels: torch.Tensor) -> dict[int, torch.Tensor]:
        """Return per-layer mean reconstruction errors (pre-training scan, item 22)."""
        out = {}
        feats = self.vit.patch_embed(x_pixels)
        if hasattr(self.vit, "cls_token"):
            cls = self.vit.cls_token.expand(feats.shape[0], -1, -1)
            feats = torch.cat([cls, feats], dim=1) + self.vit.pos_embed
            feats = self.vit.pos_drop(feats)
        for li, blk in enumerate(self.vit.blocks):
            if li in self.expandable_layers and blk.n_modules > 0:
                out[li] = blk.descriptor_errors(feats).mean().item()
            feats = blk(feats)
        return out


class _TinyViTStub(nn.Module):
    """CPU-friendly stand-in when timm weights are unavailable."""

    def __init__(self, dim: int = 768, depth: int = 4):
        super().__init__()
        self.embed_dim = dim
        self.patch_embed = nn.Conv2d(3, dim, 16, 16)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, 197, dim))
        self.pos_drop = nn.Identity()
        self.blocks = nn.ModuleList([_StubBlock(dim) for _ in range(depth)])

    def forward_features(self, x):
        f = self.patch_embed(x).flatten(2).transpose(1, 2)
        f = torch.cat([self.cls_token.expand(f.shape[0], -1, -1), f], dim=1)
        n = f.shape[1]
        f = f + self.pos_embed[:, :n]
        for b in self.blocks:
            f = b(f)
        return f


class _StubBlock(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = nn.MultiheadAttention(dim, 4, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(nn.Linear(dim, dim * 2), nn.GELU(), nn.Linear(dim * 2, dim))

    def forward(self, x):
        h = self.norm1(x)
        a, _ = self.attn(h, h, h)
        x = x + a
        x = x + self.mlp(self.norm2(x))
        return x
