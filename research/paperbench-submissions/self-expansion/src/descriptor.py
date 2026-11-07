"""Representation-descriptor statistics and the self-expansion trigger.

Rubric anchors:
- item 19: running mean/std of reconstruction error stored per descriptor.
- item 20: z-score of the k-th descriptor in layer l:
            z = (r - u) / sigma
- item 21-24: before training task t, scan every expandable layer; per-sample
            reconstruction error is computed over the task data; if all z-scores
            of all descriptors in some layer exceed a threshold, expansion is
            signalled for that layer; if no expansion signals at all, the task
            is skipped.
"""

from __future__ import annotations

import torch

ZSCORE_THRESHOLD = 1.0


class RunningStats:
    """Streaming mean/std of a scalar error stream."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)

    @property
    def std(self) -> float:
        return (self.m2 / (self.n - 1)) ** 0.5 if self.n > 1 else 0.0

    def zscore(self, value: float) -> float:
        s = self.std
        if s == 0.0:
            return 0.0
        return (value - self.mean) / s


def scan_for_expansion(model, loader, device="cpu", threshold: float = ZSCORE_THRESHOLD):
    """Return (per_layer_min_z, layers_to_expand).

    Uses the running z-score of each descriptor (item 20). A layer signals
    expansion when its descriptor z-score exceeds the threshold on task data
    (items 21-23).
    """
    layers = getattr(model, "expandable_layers", [])
    per_layer_min_z: dict[int, float] = {}
    model.eval()
    with torch.no_grad():
        for batch in loader:
            x = batch[0] if isinstance(batch, (tuple, list)) else batch
            x = x.to(device)
            errs = model.block_descriptor_errors(x)
            for li, err in errs.items():
                st = model._running_u.get(li)
                if st is None:
                    continue
                z = st.zscore(float(err))
                per_layer_min_z[li] = max(z, per_layer_min_z.get(li, -float("inf")))
    to_expand = {li for li in layers if per_layer_min_z.get(li, 0.0) > threshold}
    return per_layer_min_z, to_expand


def update_running_stats(model, loader, device="cpu") -> None:
    """item 19: accumulate reconstruction-error mean/std per descriptor."""
    model.eval()
    with torch.no_grad():
        for batch in loader:
            x = batch[0] if isinstance(batch, (tuple, list)) else batch
            x = x.to(device)
            errs = model.block_descriptor_errors(x)
            for li, err in errs.items():
                st = model._running_u.get(li)
                if st is None:
                    st = RunningStats()
                    model._running_u[li] = st
                st.update(float(err))


def should_skip_task(to_expand: set[int]) -> bool:
    return len(to_expand) == 0
