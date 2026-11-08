#!/usr/bin/env python3
"""Minimal behavior-cloning baseline on the public D4RL Kitchen HDF5.

No MuJoCo environment or rollout is used. It measures supervised action
prediction on a held-out split of transitions from one public Kitchen dataset.
"""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()

    import h5py
    import numpy as np
    import torch
    from sklearn.model_selection import train_test_split

    started = time.monotonic()
    with h5py.File(args.data, "r") as handle:
        observations = handle["observations"][...]
        actions = handle["actions"][...]
        rewards = handle["rewards"][...]
        terminals = handle["terminals"][...]
        timeouts = handle["timeouts"][...]
    if args.limit:
        observations = observations[:args.limit]
        actions = actions[:args.limit]
        rewards = rewards[:args.limit]
        terminals = terminals[:args.limit]
        timeouts = timeouts[:args.limit]

    indices = np.arange(len(observations))
    train_idx, val_idx = train_test_split(indices, test_size=0.1,
                                          random_state=args.seed, shuffle=True)
    x = torch.as_tensor(observations, dtype=torch.float32)
    y = torch.as_tensor(actions, dtype=torch.float32)
    x_train, x_val = x[train_idx], x[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    torch.manual_seed(args.seed)
    policy = torch.nn.Sequential(
        torch.nn.Linear(x.shape[1], 256), torch.nn.ReLU(),
        torch.nn.Linear(256, 256), torch.nn.ReLU(),
        torch.nn.Linear(256, y.shape[1]),
    )
    optimizer = torch.optim.Adam(policy.parameters(), lr=1e-3)
    history = []
    rng = torch.Generator().manual_seed(args.seed)
    for epoch in range(args.epochs):
        order = torch.randperm(len(x_train), generator=rng)
        losses = []
        for start in range(0, len(order), args.batch_size):
            batch = order[start:start + args.batch_size]
            prediction = policy(x_train[batch])
            loss = torch.nn.functional.mse_loss(prediction, y_train[batch])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(float(loss))
        with torch.no_grad():
            val_mse = float(torch.nn.functional.mse_loss(policy(x_val), y_val))
            val_mae = float(torch.nn.functional.l1_loss(policy(x_val), y_val))
        history.append({"epoch": epoch + 1,
                        "train_mse": float(np.mean(losses)),
                        "val_mse": val_mse,
                        "val_mae": val_mae})

    receipt = {
        "schema": "qone-d4rl-kitchen-bc-baseline-v1",
        "data": str(args.data),
        "data_sha256": sha256_file(args.data),
        "rows": int(len(observations)),
        "obs_dim": int(observations.shape[1]),
        "action_dim": int(actions.shape[1]),
        "reward_mean": float(rewards.mean()),
        "terminals": int(terminals.sum()),
        "timeouts": int(timeouts.sum()),
        "train_rows": int(len(train_idx)),
        "val_rows": int(len(val_idx)),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "history": history,
        "final_val_mse": history[-1]["val_mse"],
        "final_val_mae": history[-1]["val_mae"],
        "elapsed_s": round(time.monotonic() - started, 2),
        "official": False,
        "note": (
            "Behavior-cloning MLP on held-out transitions from one public D4RL "
            "Kitchen HDF5. No online rollout, no environment return, no RL result."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(receipt, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
