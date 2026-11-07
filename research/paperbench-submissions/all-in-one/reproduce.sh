#!/bin/sh
set -eu
python3 run.py < data/sample.json
python3 -m pytest -q tests
