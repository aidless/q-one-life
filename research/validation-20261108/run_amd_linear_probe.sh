#!/usr/bin/env bash
set -u
ROOT=/root/qone-paperbench-full10
SRC=/root/qone-paperbench-full10/local-scripts
PY=/opt/venv/bin/python
RUNS="$ROOT/runs"
mkdir -p "$RUNS"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$RUNS/linear-probe.log"; }
log "START linear-probe"
if env HF_ENDPOINT=https://hf-mirror.com "$PY" "$SRC/run_tiny_imagenet_linear_probe.py" \
  --zip "$ROOT/vision/tiny-imagenet-200.zip" \
  --weights "$ROOT/vision/resnet50.a1_in1k.safetensors" \
  --model-name resnet50.a1_in1k \
  --output "$RUNS/tiny-imagenet-linear-probe.json" \
  --train-images 10000 --val-images 2000 --epochs 3 \
  --batch-size 256 --learning-rate 0.01 --device cuda \
  > "$RUNS/linear-probe.stdout.log" 2> "$RUNS/linear-probe.stderr.log"; then
  log "DONE linear-probe"
else
  code=$?
  log "BLOCKED linear-probe exit=$code"
fi
