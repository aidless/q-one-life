#!/usr/bin/env python3
"""Full Jigsaw 90:10 GPT-2-medium residual-stream probe.

Runs on the authorized AMD host. Writes compact receipts locally; feature
matrices stay on the cloud host. This is a real data experiment, not a
paper-table reproduction claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np

LABEL_COLUMNS = ("toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            text = (row.get("comment_text") or "").strip()
            if not text:
                continue
            label = int(any(int(row.get(column, 0)) > 0 for column in LABEL_COLUMNS))
            rows.append({"id": row.get("id", ""), "text": text, "label": label})
    return rows


def split_90_10(rows: list[dict], seed: int) -> tuple[list[dict], list[dict]]:
    tagged = []
    for row in rows:
        key = f"{seed}:{row['id']}:{row['text']}".encode("utf-8")
        tagged.append((hashlib.sha256(key).hexdigest(), row))
    tagged.sort(key=lambda item: item[0])
    n_val = max(1, len(tagged) // 10)
    return [row for _, row in tagged[n_val:]], [row for _, row in tagged[:n_val]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--checkpoint-every", type=int, default=5000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--features-only", action="store_true")
    args = parser.parse_args()

    import torch
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
    from transformers import AutoModel, AutoTokenizer

    rows = load_rows(args.data)
    if args.limit:
        rows = rows[: args.limit]
    train, val = split_90_10(rows, args.seed)
    all_rows = train + val
    if args.end:
        all_rows = all_rows[args.start:args.end]
    y = np.asarray([row["label"] for row in all_rows], dtype=np.int64)

    tok = AutoTokenizer.from_pretrained(str(args.model))
    tok.pad_token = tok.eos_token
    model = AutoModel.from_pretrained(str(args.model), torch_dtype="float16")
    model.to("cuda")
    model.eval()

    features: list[np.ndarray] = []
    pending: list[np.ndarray] = []
    shard_dir = args.features.parent / (args.features.stem + "-shards")
    shard_dir.mkdir(parents=True, exist_ok=True)
    shard_paths: list[Path] = []
    started = time.monotonic()
    processed = 0
    checkpointed_rows = 0
    if args.resume and not args.features_only:
        for path in sorted(shard_dir.glob("features-*.npy")):
            features.append(np.load(path))
            shard_paths.append(path)
        processed = sum(part.shape[0] for part in features)
        checkpointed_rows = processed
        print(json.dumps({"resumed_rows": processed}), flush=True)
    with torch.no_grad():
        for start in range(processed, len(all_rows), args.batch_size):
            batch = all_rows[start:start + args.batch_size]
            encoded = tok(
                [row["text"] for row in batch],
                return_tensors="pt",
                truncation=True,
                max_length=args.max_length,
                padding=True,
            ).to("cuda")
            output = model(**encoded)
            hidden = output.last_hidden_state.mean(dim=1).float().cpu().numpy()
            features.append(hidden)
            pending.append(hidden)
            pending_rows = sum(part.shape[0] for part in pending)
            if pending_rows >= args.checkpoint_every or start + len(batch) >= len(all_rows):
                chunk = np.concatenate(pending, axis=0)
                shard_path = shard_dir / f"features-{len(shard_paths):05d}.npy"
                np.save(shard_path, chunk)
                shard_paths.append(shard_path)
                checkpointed_rows += chunk.shape[0]
                pending = []
                print(json.dumps({"checkpoint_rows": checkpointed_rows,
                                  "shard": shard_path.name}), flush=True)
            if (start // args.batch_size) % 100 == 0:
                elapsed = time.monotonic() - started
                done = min(start + len(batch), len(all_rows))
                print(json.dumps({"done": done, "total": len(all_rows),
                                  "elapsed_s": round(elapsed, 1)}), flush=True)

    if args.features_only:
        matrix = np.concatenate(features, axis=0).astype(np.float32)
        args.features.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.features, matrix)
        print(json.dumps({"features_only": True,
                          "rows": int(matrix.shape[0]),
                          "shape": list(matrix.shape),
                          "output": str(args.features)}), flush=True)
        return 0
    x = np.concatenate(features, axis=0).astype(np.float32)
    n_train = len(train)
    x_train, x_val = x[:n_train], x[n_train:]
    y_train, y_val = y[:n_train], y[n_train:]
    classifier = LogisticRegression(max_iter=1000, C=1.0)
    classifier.fit(x_train, y_train)
    probabilities = classifier.predict_proba(x_val)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    elapsed = time.monotonic() - started
    receipt = {
        "schema": "qone-gpt2-medium-jigsaw-full-probe-v1",
        "model": str(args.model),
        "data": str(args.data),
        "data_sha256": sha256_file(args.data),
        "official": False,
        "rows": len(rows),
        "train_rows": len(train),
        "val_rows": len(val),
        "positive_rows": int(y.sum()),
        "feature_shape": list(x.shape),
        "max_length": args.max_length,
        "batch_size": args.batch_size,
        "accuracy": float(accuracy_score(y_val, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_val, predictions)),
        "roc_auc": float(roc_auc_score(y_val, probabilities)),
        "elapsed_s": round(elapsed, 2),
        "note": (
            "Real GPT-2-medium last-layer residual features averaged over timesteps, "
            "trained as a binary softmax(Wx) probe. This is a full-Jigsaw data run, "
            "not the paper's full DPO/SVD/PPLM reproduction."
        ),
    }
    args.features.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.features, x=x, y=y, n_train=n_train)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
