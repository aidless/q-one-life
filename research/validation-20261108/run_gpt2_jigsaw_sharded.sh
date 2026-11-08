#!/bin/sh
set -eu

ROOT=/root/qone-paperbench-full10
SCRIPT=$ROOT/run_gpt2_jigsaw_full.py
DATA=$ROOT/jigsaw_train.csv
MODEL=$ROOT/public-models/gpt2-medium
OUT=$ROOT/runs/gpt2-jigsaw-full.json
FEATURES=$ROOT/runs/gpt2-jigsaw-full-features.npz
SHARDS=$ROOT/runs/gpt2-jigsaw-features-parts
TOTAL=159571
CHUNK=8000
BATCH=8
MAXLEN=64

mkdir -p "$SHARDS" "$ROOT/runs"

start=0
while [ "$start" -lt "$TOTAL" ]; do
    end=$((start + CHUNK))
    [ "$end" -gt "$TOTAL" ] && end=$TOTAL
    shard=$SHARDS/part-$(printf '%06d' "$start")-$(printf '%06d' "$end").npy
    if [ -f "$shard" ]; then
        echo "skip $start $end"
        start=$end
        continue
    fi
    echo "run $start $end"
    ok=0
    attempt=1
    while [ "$attempt" -le 3 ] && [ "$ok" -eq 0 ]; do
        if HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 /opt/venv/bin/python -u "$SCRIPT" \
            --data "$DATA" --model "$MODEL" \
            --start "$start" --end "$end" \
            --batch-size "$BATCH" --max-length "$MAXLEN" \
            --checkpoint-every 2000 --features-only \
            --output "$OUT" --features "$shard"; then
            ok=1
        else
            echo "retry $start $end attempt $attempt"
            attempt=$((attempt + 1))
            sleep 10
        fi
    done
    [ "$ok" -eq 1 ] || { echo "FAILED segment $start $end"; exit 1; }
    start=$end
done

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 /opt/venv/bin/python -u - <<'PY'
import json, time
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
import run_gpt2_jigsaw_full as job

root = Path("/root/qone-paperbench-full10")
rows = job.load_rows(root / "jigsaw_train.csv")
train, val = job.split_90_10(rows, 20261108)
all_rows = train + val
y = np.asarray([row["label"] for row in all_rows], dtype=np.int64)
parts = sorted((root / "runs/gpt2-jigsaw-features-parts").glob("part-*.npy"))
x = np.concatenate([np.load(path) for path in parts], axis=0).astype(np.float32)
assert x.shape[0] == len(all_rows), (x.shape, len(all_rows))
n_train = len(train)
x_train, x_val = x[:n_train], x[n_train:]
y_train, y_val = y[:n_train], y[n_train:]
started = time.monotonic()
clf = LogisticRegression(max_iter=1000, C=1.0).fit(x_train, y_train)
proba = clf.predict_proba(x_val)[:, 1]
pred = (proba >= 0.5).astype(int)
receipt = {
    "schema": "qone-gpt2-medium-jigsaw-full-probe-v1",
    "model": "public-models/gpt2-medium",
    "data": "jigsaw_train.csv",
    "data_sha256": job.sha256_file(root / "jigsaw_train.csv"),
    "official": False,
    "rows": len(rows), "train_rows": len(train), "val_rows": len(val),
    "positive_rows": int(y.sum()), "feature_shape": list(x.shape),
    "max_length": 64, "batch_size": 8, "segments": len(parts),
    "accuracy": float(accuracy_score(y_val, pred)),
    "balanced_accuracy": float(balanced_accuracy_score(y_val, pred)),
    "roc_auc": float(roc_auc_score(y_val, proba)),
    "elapsed_s": round(time.monotonic() - started, 2),
    "note": "Full Jigsaw 90:10 GPT-2-medium residual probe, sharded to avoid long ROCm HIP kernel failures; not a paper-table reproduction.",
}
np.savez_compressed(root / "runs/gpt2-jigsaw-full-features.npz", x=x, y=y, n_train=n_train)
(root / "runs/gpt2-jigsaw-full.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt), flush=True)
PY
