#!/usr/bin/env python3
"""Run a compact supervised behavior-cloning matrix on public D4RL HDF5 files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_policy(obs_dim: int, action_dim: int, width: int, depth: int):
    import torch

    layers = []
    last = obs_dim
    for _ in range(depth):
        layers.extend([torch.nn.Linear(last, width), torch.nn.ReLU()])
        last = width
    layers.append(torch.nn.Linear(last, action_dim))
    return torch.nn.Sequential(*layers)


def run_dataset(path: Path, epochs: int, batch_size: int, widths: tuple[int, ...],
                seeds: tuple[int, ...], max_rows: int) -> dict:
    import h5py
    import numpy as np
    import torch
    from sklearn.model_selection import train_test_split

    with h5py.File(path, "r") as handle:
        observations = handle["observations"][...]
        actions = handle["actions"][...]
    if max_rows and len(observations) > max_rows:
        observations = observations[:max_rows]
        actions = actions[:max_rows]
    x = torch.as_tensor(observations, dtype=torch.float32)
    y = torch.as_tensor(actions, dtype=torch.float32)
    indices = np.arange(len(x))
    train_idx, val_idx = train_test_split(indices, test_size=0.1,
                                          random_state=20261108, shuffle=True)
    x_train, x_val = x[train_idx], x[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    rows = []
    for width in widths:
        for seed in seeds:
            torch.manual_seed(seed)
            policy = make_policy(x.shape[1], y.shape[1], width, 2)
            optimizer = torch.optim.Adam(policy.parameters(), lr=1e-3)
            generator = torch.Generator().manual_seed(seed)
            for _ in range(epochs):
                order = torch.randperm(len(x_train), generator=generator)
                for start in range(0, len(order), batch_size):
                    batch = order[start:start + batch_size]
                    loss = torch.nn.functional.mse_loss(policy(x_train[batch]), y_train[batch])
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
            with torch.no_grad():
                val_mse = float(torch.nn.functional.mse_loss(policy(x_val), y_val))
                val_mae = float(torch.nn.functional.l1_loss(policy(x_val), y_val))
            rows.append({"width": width, "depth": 2, "seed": seed,
                         "val_mse": val_mse, "val_mae": val_mae})
    by_width = {}
    for row in rows:
        by_width.setdefault(str(row["width"]), []).append(row)
    summary = {
        width: {"runs": len(values),
                "mean_val_mse": float(np.mean([item["val_mse"] for item in values])),
                "best_val_mse": float(min(item["val_mse"] for item in values)),
                "mean_val_mae": float(np.mean([item["val_mae"] for item in values]))}
        for width, values in by_width.items()
    }
    return {
        "path": str(path), "sha256": sha256_file(path), "rows": int(len(x)),
        "observation_dim": int(x.shape[1]), "action_dim": int(y.shape[1]),
        "train_rows": int(len(train_idx)), "val_rows": int(len(val_idx)),
        "epochs": epochs, "batch_size": batch_size, "widths": list(widths),
        "seeds": list(seeds), "summary": summary, "runs": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/root/qone-paperbench-full10"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--max-rows", type=int, default=200000)
    args = parser.parse_args()

    data_root = Path(os.environ.get("QONE_D4RL_ROOT") or args.root / "d4rl")
    candidates = sorted(data_root.glob("*.hdf5"))
    kitchen = args.root / "kitchen_microwave_kettle_bottomburner_light-v0.hdf5"
    include_legacy_kitchen = os.environ.get("QONE_D4RL_ONLY") != "1"
    if include_legacy_kitchen and kitchen.is_file() and kitchen not in candidates:
        candidates.append(kitchen)
    started = time.monotonic()
    datasets = []
    for path in candidates:
        row = {"path": str(path)}
        try:
            row.update(run_dataset(path, args.epochs, args.batch_size,
                                   (128, 256, 512), (1, 2, 3), args.max_rows))
            row["status"] = "completed"
        except Exception as exc:
            row.update({"status": "blocked",
                        "error": f"{type(exc).__name__}: {exc}"[:300]})
        datasets.append(row)
        print(json.dumps({"done": path.name, "status": row["status"],
                          "rows": row.get("rows")}), flush=True)
    report = {
        "schema": "qone-d4rl-multi-bc-v1",
        "official": False,
        "datasets": datasets,
        "completed": sum(row["status"] == "completed" for row in datasets),
        "blocked": sum(row["status"] == "blocked" for row in datasets),
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": "Supervised action prediction only; no online rollout or environment return.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "datasets"}, indent=1),
          flush=True)
    return 0 if report["completed"] > 0 and report["blocked"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
