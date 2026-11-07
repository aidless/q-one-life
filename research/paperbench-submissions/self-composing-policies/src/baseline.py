"""Single-module baselines and parameter-growth accounting (Section 5.4, App. C).

- FT-1 / FT-N: one module trained on task 1 / trained on all tasks sequentially.
- Parameter growth for CompoNet is linear because each module costs the same.
- ProgressiveNet-style quadratic and PackNet-style constant growth are
  reproduced purely as accounting formulas used by the scalability table.
"""

from __future__ import annotations


def componet_param_count(n_tasks: int, per_module: int) -> int:
    """CompoNet: O(m * n) (App. C)."""
    return per_module * n_tasks


def progressive_param_count(n_tasks: int, base: int) -> int:
    """Progressive Net: quadratic growth, a new column per task."""
    return base * (n_tasks * (n_tasks + 1)) // 2


def packnet_param_count(n_tasks: int, base: int) -> int:
    """PackNet: fixed capacity (constant growth)."""
    return base


def ftn_trainable_param_count(n_tasks: int, base: int) -> int:
    """FT-N: one shared network, constant size, retrained on every task."""
    return base


def growth_report(n_tasks: int, per_module: int, base: int) -> dict:
    return {
        "componet_total": componet_param_count(n_tasks, per_module),
        "componet_trainable": per_module,
        "progressive_total": progressive_param_count(n_tasks, base),
        "packnet_total": packnet_param_count(n_tasks, base),
        "ftn_total": ftn_trainable_param_count(n_tasks, base),
    }
