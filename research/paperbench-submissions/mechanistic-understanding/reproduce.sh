#!/bin/sh
set -eu
python3 run.py < data/sample.json
QONE_REPO_ROOT="${QONE_REPO_ROOT:-$(pwd)/../../..}" python3 -c 'import json,sys;sys.path.insert(0,".");from src.pipeline import run_reproduction_slice;print(json.dumps(run_reproduction_slice()))' > results/full-slice.json
python3 -m pytest -q tests
