#!/usr/bin/env bash
set -u
ROOT=/root/qone-paperbench-full10
SRC=/root/qone-paperbench-full10/local-scripts
PY=/opt/venv/bin/python
RUNS="$ROOT/runs"
mkdir -p "$RUNS"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$RUNS/linear-probe-matrix.log"; }
log "START linear-probe-matrix"
if env HF_ENDPOINT=https://hf-mirror.com "$PY" "$SRC/run_tiny_imagenet_linear_probe_matrix.py" \
  --root "$ROOT" --script "$SRC/run_tiny_imagenet_linear_probe.py" \
  --output "$RUNS/tiny-imagenet-linear-probe-matrix.json" \
  --train-images 5000 --val-images 1000 --epochs 2 \
  > "$RUNS/linear-probe-matrix.stdout.log" 2> "$RUNS/linear-probe-matrix.stderr.log"; then
  log "DONE linear-probe-matrix"
else
  code=$?
  log "BLOCKED linear-probe-matrix exit=$code"
fi
