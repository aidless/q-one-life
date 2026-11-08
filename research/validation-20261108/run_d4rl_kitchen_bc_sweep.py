#!/usr/bin/env python3
"""Small deterministic BC sweep on public D4RL Kitchen transitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_policy(obs_dim: int, action_dim: int, width: int, depth: int) -> object:
    import torch

    layers = []
    last = obs_dim
    for _ in range(depth):
        layers.extend([torch.nn.Linear(last, width), torch.nn.ReLU()])
        last = width
    layers.append(torch.nn.Linear(last, action_dim))
    return torch.nn.Sequential(*layers)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()

    import h5py
    import numpy as np
    import torch
    from sklearn.model_selection import train_test_split

    started = time.monotonic()
    with h5py.File(args.data, "r") as handle:
        observations = handle["observations"][...]
        actions = handle["actions"][...]
    x = torch.as_tensor(observations, dtype=torch.float32)
    y = torch.as_tensor(actions, dtype=torch.float32)
    indices = np.arange(len(x))
    train_idx, val_idx = train_test_split(indices, test_size=0.1,
                                          random_state=20261108, shuffle=True)
    x_train, x_val = x[train_idx], x[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    configs = [(128, 2), (256, 2), (512, 2), (256, 3), (512, 3)]
    rows = []
    for width, depth in configs:
        for seed in (1, 2, 3, 4, 5):
            torch.manual_seed(seed)
            policy = make_policy(x.shape[1], y.shape[1], width, depth)
            optimizer = torch.optim.Adam(policy.parameters(), lr=1e-3)
            generator = torch.Generator().manual_seed(seed)
            for _ in range(args.epochs):
                order = torch.randperm(len(x_train), generator=generator)
                for start in range(0, len(order), args.batch_size):
                    batch = order[start:start + args.batch_size]
                    loss = torch.nn.functional.mse_loss(policy(x_train[batch]), y_train[batch])
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
            with torch.no_grad():
                val_mse = float(torch.nn.functional.mse_loss(policy(x_val), y_val))
                val_mae = float(torch.nn.functional.l1_loss(policy(x_val), y_val))
            rows.append({"width": width, "depth": depth, "seed": seed,
                         "val_mse": val_mse, "val_mae": val_mae})
    by_config = {}
    for row in rows:
        key = f"{row['width']}x{row['depth']}"
        by_config.setdefault(key, []).append(row)
    summary = {
        key: {
            "runs": len(values),
            "mean_val_mse": float(np.mean([row["val_mse"] for row in values])),
            "std_val_mse": float(np.std([row["val_mse"] for row in values])),
            "best_val_mse": float(min(row["val_mse"] for row in values)),
            "mean_val_mae": float(np.mean([row["val_mae"] for row in values])),
        }
        for key, values in by_config.items()
    }
    receipt = {
        "schema": "qone-d4rl-kitchen-bc-sweep-v1",
        "data": str(args.data),
        "data_sha256": sha256_file(args.data),
        "rows": int(len(x)),
        "train_rows": int(len(train_idx)),
        "val_rows": int(len(val_idx)),
        "configs": configs,
        "seeds": [1, 2, 3, 4, 5],
        "epochs": args.epochs,
        "summary": summary,
        "runs": rows,
        "elapsed_s": round(time.monotonic() - started, 2),
        "official": False,
        "note": "Supervised action prediction only; no online rollout or environment return.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": receipt["schema"], "runs": len(rows),
                      "summary": summary, "elapsed_s": receipt["elapsed_s"]}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
