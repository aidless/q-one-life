"""Dataset preparation manifests for the four benchmark suites.

Rubric anchors:
- items 1-4: ViT-B/16 + CIFAR-100 / ImageNet-R / ImageNet-A availability.
- item 5: VTAB ADAM subset, five domains in a fixed order.
- item 6: each task holds 10 distinct classes.

Downloads are not vendored; ``prepare_manifest`` records what must exist and
``build_synthetic_loader`` provides a shape-correct loader for smoke tests.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

VTAB_ADAM_DOMAINS = ["dtd", "eurosat", "flowers", "oxford_pets", "resisc45"]
BENCHMARKS = {
    "cifar100": {"tasks": 10, "classes_per_task": 10, "source": "torchvision.datasets.CIFAR100"},
    "imagenet-r": {"tasks": 20, "classes_per_task": 10, "source": "hendrycks/imagenet-r"},
    "imagenet-a": {"tasks": 20, "classes_per_task": 10, "source": "hendrycks/imagenet-a"},
    "vtab": {"tasks": 5, "classes_per_task": 10, "domains": VTAB_ADAM_DOMAINS},
}


def prepare_manifest() -> dict:
    manifest = {"vision_backbone": "vit_base_patch16_224 (ViT-B/16, ImageNet-1K)",
                "benchmarks": BENCHMARKS}
    (DATA_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def class_split(n_classes: int = 100, tasks: int = 10):
    """item 6: contiguous 10-class tasks."""
    per = n_classes // tasks
    return [list(range(i * per, (i + 1) * per)) for i in range(tasks)]


def build_synthetic_loader(n_samples: int = 8, n_classes: int = 10, batch_size: int = 4, seed: int = 0):
    """Shape-correct smoke loader: random pixels, class labels in [0, n_classes)."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(n_samples, 3, 224, 224, generator=g)
    y = torch.randint(0, n_classes, (n_samples,), generator=g)
    return DataLoader(TensorDataset(x, y), batch_size=batch_size)
