#!/usr/bin/env python3
"""Smoke-run SEMA on a short synthetic task stream.

This reproduces the *procedure* (scan -> expand -> freeze -> train -> metrics)
on tiny inputs so the pipeline is verifiable without GPU hours. Real
benchmark numbers require downloading CIFAR-100 / ImageNet-R / ImageNet-A /
VTAB and running 5-20 epochs per task (see README).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import torch

from src.data import build_synthetic_loader, class_split, prepare_manifest
from src.sema import run_sema
from src.vit_sema import SemaViT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=2)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--out", default="results/smoke.json")
    args = ap.parse_args()

    prepare_manifest()
    torch.manual_seed(0)
    model = SemaViT(num_classes=0)
    model.head = torch.nn.Identity()
    tasks = []
    for t in range(args.tasks):
        tasks.append({
            "train_loader": build_synthetic_loader(n_samples=args.samples, n_classes=10, seed=t),
            "test_loader": build_synthetic_loader(n_samples=args.samples, n_classes=10, seed=10 + t),
            "n_new_classes": 10,
        })
    logs = []

    def log(msg):
        logs.append(msg)
        print(msg)

    result = run_sema(model, tasks, device="cpu", log=log, epochs=args.epochs)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"result": result, "logs": logs, "tasks": args.tasks,
                   "epochs": args.epochs, "samples": args.samples,
                   "split": class_split()[: args.tasks]}, f, indent=2)
    print(json.dumps({"A_N": result["A_N"], "A_bar": result["A_bar"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
