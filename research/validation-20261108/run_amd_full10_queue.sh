#!/usr/bin/env bash
set -u
ROOT=/root/qone-paperbench-full10
SRC=/root/qone-paperbench-full10/local-scripts
PY=/opt/venv/bin/python
RUNS="$ROOT/runs"
mkdir -p "$RUNS" "$ROOT/d4rl" "$ROOT/public-models" /tmp/qone-h5py

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$RUNS/full10-queue.log"; }

run_step() {
  name="$1"; shift
  log "START $name"
  if "$@" > "$RUNS/$name.stdout.log" 2> "$RUNS/$name.stderr.log"; then
    log "DONE $name"
  else
    code=$?
    log "BLOCKED $name exit=$code"
  fi
}

run_step asset-download env HF_ENDPOINT=https://hf-mirror.com "$PY" "$SRC/download_full10_assets.py" \
  --root "$ROOT" --output "$ROOT/runs/public-assets.json" --include-large-d4rl

run_step vision-matrix "$PY" "$SRC/run_vision_multimodel_matrix.py" \
  --root "$ROOT" --script "$SRC/run_tiny_imagenet_vision_matrix.py" \
  --output "$ROOT/runs/vision-multimodel.json" --images 2000 --device cuda

run_step toxicity-dpo env HF_ENDPOINT=https://hf-mirror.com "$PY" "$SRC/run_mechanistic_toxicity_dpo.py" \
  --lm "$ROOT/public-models/gpt2-medium" \
  --classifier "$ROOT/public-models/unbiased-toxic-roberta" \
  --rtp "$ROOT/real-toxicity-prompts.jsonl" \
  --output "$ROOT/runs/mechanistic-toxicity-dpo.json" \
  --limit 128 --max-new-tokens 20 --dpo-steps 16 --batch-size 4 --device cuda

run_step d4rl-bc env PYTHONPATH=/tmp/qone-h5py "$PY" "$SRC/run_d4rl_multi_bc.py" \
  --root "$ROOT" --output "$ROOT/runs/d4rl-multi-bc.json" --epochs 4 --max-rows 200000

log "QUEUE_STOPPED"
