#!/usr/bin/env python3
"""CPU smoke test of the CompoNet reproduction.

Checks structure, freezing, shape correctness, linear parameter growth and the
metric code paths. It does not train SAC/PPO: those runs need GPU hours on the
ALE / Meta-World stacks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import torch

from src.agent import CompoNetAgent
from src.baseline import growth_report
from src.metrics import average_performance, forward_transfer, matching_rate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", type=int, default=6)
    ap.add_argument("--out", default="results/smoke.json")
    args = ap.parse_args()

    torch.manual_seed(0)
    agent = CompoNetAgent(n_actions=6)
    checks = {}
    accounting = []
    for k in range(args.modules):
        agent.add_module()
        agent.freeze_all_but_last()
        accounting.append(agent.parameter_accounting())
        state = torch.zeros(2, 4, 210, 160)
        out, phi, h = agent(state)
        trainable = sum(1 for p in agent.parameters() if p.requires_grad)
        checks[f"k{k + 1}"] = {
            "out_shape": list(out.shape),
            "phi_shape": list(phi.shape),
            "h_shape": list(h.shape),
            "trainable_tensors": trainable,
            "n_modules": agent.parameter_accounting()["n_modules"],
        }

    per_module = accounting[-1]["per_module_params"][0]
    growth = growth_report(args.modules, per_module, base=1_000_000)
    checks["linear_growth"] = all(
        a["per_module_params"] == [per_module] * len(a["per_module_params"])
        for a in accounting
    )
    checks["growth"] = growth
    checks["metrics"] = {
        "average_performance": average_performance({"t1": [0.5, 0.6], "t2": [0.7]}),
        "forward_transfer": forward_transfer([0.8, 0.7], [0.8, 0.5]),
        "matching_rate": matching_rate([[1, 0], [0, 1]], [[1, 0], [1, 0]]),
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2)
    print(json.dumps({"linear_growth": checks["linear_growth"],
                      "per_module_params": per_module,
                      "growth": growth}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
