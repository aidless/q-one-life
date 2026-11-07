"""Evaluation metrics from Section 5.1.

Average performance (eq. in 5.1):
    p_i(t) is the success rate on task i at timestep t of task i's training.
    AP_i = mean over the evaluation window of p_i(t)
    AP = (1/N) sum_i AP_i

Forward transfer (FT):
    FT = (1 / (N-1)) sum_{i=2..N} (AP_i - AP_ref_i) / AP_ref_i
where AP_ref_i is the reference (single-task) score at 1M timesteps.

Reference forward transfer uses the same shape with a fixed reference table.
"""

from __future__ import annotations

DEFAULT_WINDOW = 10_000


def episode_windows(timesteps, window: int = DEFAULT_WINDOW):
    """Group recorded timesteps into non-overlapping windows."""
    out = []
    cur = []
    for t in timesteps:
        cur.append(t)
        if len(cur) >= window:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def success_rate(task_records) -> float:
    """task_records: iterable of bools/dicts with a success flag."""
    vals = []
    for r in task_records:
        if isinstance(r, dict):
            vals.append(1.0 if r.get("success") or r.get("solved") else 0.0)
        elif isinstance(r, bool):
            vals.append(1.0 if r else 0.0)
        else:
            vals.append(float(r))
    return sum(vals) / len(vals) if vals else 0.0


def average_performance(per_task_curves: dict[str, list[float]]) -> float:
    if not per_task_curves:
        return 0.0
    vals = [sum(c) / len(c) if c else 0.0 for c in per_task_curves.values()]
    return sum(vals) / len(vals)


def forward_transfer(scores: list[float], reference_scores: list[float]) -> float:
    """Mean relative gain over the reference scores for tasks 2..N."""
    if len(scores) < 2:
        return 0.0
    gains = []
    for s, r in zip(scores[1:], reference_scores[1:]):
        gains.append((s - r) / r if r else 0.0)
    return sum(gains) / len(gains)


def reference_forward_transfer(scores: list[float], reference_scores: list[float]) -> float:
    """Reference FT: same shape, using the paper's fixed reference table."""
    return forward_transfer(scores, reference_scores)


def matching_rate(a, b) -> float:
    """Frequency that argmax(a) == argmax(b) (action-agreement metric)."""
    n = 0
    ok = 0
    for x, y in zip(a, b):
        if len(x) == 0:
            continue
        n += 1
        ax = max(range(len(x)), key=lambda i: x[i])
        ay = max(range(len(y)), key=lambda i: y[i])
        ok += int(ax == ay)
    return ok / n if n else 0.0
