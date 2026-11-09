#!/usr/bin/env bash
# Record one synthetic observation with the stdlib CLI.
# No model, no network, no q-one-core or q-one-agent import.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
deadline=900
start_ns=$(date +%s%N)
work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

export PYTHONPATH="$project_dir/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m qone_life --data-dir "$work/life" init
python3 -m qone_life --data-dir "$work/life" add-observation \
  --domain learning \
  --metric focused_hours \
  --value 1 \
  --minimum 0 \
  --maximum 8 \
  --source "record-only smoke; synthetic row, not a life outcome" \
  --note "smoke"
python3 -m qone_life --data-dir "$work/life" score --spec-file examples/metric-spec.json >"$work/score.json"
python3 -m qone_life --data-dir "$work/life" verify | grep -q "verified 1 events"
python3 - "$work/score.json" <<'PY'
import json
import sys

sys.path.insert(0, "src")
import qone_life.cli  # noqa: F401

loaded = set(sys.modules)
forbidden = sorted(name for name in ("qone_core", "qone_agent", "httpx", "fastapi") if name in loaded)
if forbidden:
    raise SystemExit("record-only import loaded: " + ", ".join(forbidden))
report = json.load(open(sys.argv[1], encoding="utf-8"))
if report.get("global_score") is not None:
    raise SystemExit("record-only score produced a global score")
if report.get("score_type") != "dimension_vector" or report.get("observations") != 1:
    raise SystemExit("unexpected score report")
learning = report["dimensions"]["learning"]["metrics"]["focused_hours"]
if learning["n"] != 1 or learning["score"] is None:
    raise SystemExit("smoke observation was not scored")
if report["dimensions"]["energy"]["metrics"]["sleep_quality"]["score"] is not None:
    raise SystemExit("a missing metric was imputed")
print("record-only smoke ok")
PY

end_ns=$(date +%s%N)
python3 - "$start_ns" "$end_ns" "$deadline" <<'PY'
import sys
elapsed = (int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000
deadline = int(sys.argv[3])
print(f"elapsed_seconds={elapsed:.3f}")
if elapsed >= deadline:
    raise SystemExit(f"record-only path exceeded {deadline}s")
PY
