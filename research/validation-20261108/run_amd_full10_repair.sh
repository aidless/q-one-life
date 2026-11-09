#!/usr/bin/env bash
set -u
ROOT=/root/qone-paperbench-full10
SRC=/root/qone-paperbench-full10/local-scripts
PY=/opt/venv/bin/python
RUNS="$ROOT/runs"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$RUNS/full10-repair.log"; }

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

run_step toxicity-dpo-fp32 env HF_ENDPOINT=https://hf-mirror.com "$PY" "$SRC/run_mechanistic_toxicity_dpo.py" \
  --lm "$ROOT/public-models/gpt2-medium" \
  --classifier "$ROOT/public-models/unbiased-toxic-roberta" \
  --rtp "$ROOT/real-toxicity-prompts.jsonl" \
  --output "$ROOT/runs/mechanistic-toxicity-dpo.json" \
  --limit 128 --max-new-tokens 20 --dpo-steps 16 --batch-size 4 --device cuda

run_step d4rl-bc-fixed env PYTHONPATH=/tmp/qone-h5py-only QONE_D4RL_ROOT="$ROOT/d4rl" "$PY" "$SRC/run_d4rl_multi_bc.py" \
  --root "$ROOT" --output "$ROOT/runs/d4rl-multi-bc.json" --epochs 2 --max-rows 100000

run_step d4rl-verification env PYTHONPATH=/tmp/qone-h5py-only "$PY" "$SRC/verify_full10_continuation.py" \
  --root "$ROOT/runs" --output "$ROOT/runs/full10-continuation-verification.json" --selftest

log "REPAIR_STOPPED"
