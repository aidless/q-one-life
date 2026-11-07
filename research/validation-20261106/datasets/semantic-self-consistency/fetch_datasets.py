#!/usr/bin/env python3
"""Fetch and verify the three public datasets used by semantic-self-consistency."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "raw"
SOURCES = {
    "aqua_test.jsonl": {
        "url": "https://raw.githubusercontent.com/google-deepmind/AQuA/master/test.json",
        "expected_rows": 254,
        "license": "AQuA repository public distribution; verify upstream terms before redistribution",
    },
    "svamp.json": {
        "url": "https://raw.githubusercontent.com/arkilpatel/SVAMP/main/SVAMP.json",
        "expected_rows": 1000,
        "license": "SVAMP repository public distribution; verify upstream terms before redistribution",
    },
    "strategyqa_test.json": {
        "url": "https://huggingface.co/datasets/ChilleD/StrategyQA/resolve/main/test.json",
        "expected_rows": 687,
        "license": "MIT (ChilleD/StrategyQA mirror)",
    },
    "strategyqa_train.json": {
        "url": "https://huggingface.co/datasets/ChilleD/StrategyQA/resolve/main/train.json",
        "expected_rows": 1603,
        "license": "MIT (ChilleD/StrategyQA mirror)",
    },
}


def count_rows(name: str, data: bytes) -> int:
    if name == "aqua_test.jsonl":
        return sum(1 for line in data.decode().splitlines() if line.strip())
    payload = json.loads(data)
    if isinstance(payload, list):
        return len(payload)
    for key in ("data", "examples"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return len(payload[key])
    return 0


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    receipt = {}
    for name, meta in SOURCES.items():
        data = urllib.request.urlopen(meta["url"], timeout=60).read()
        rows = count_rows(name, data)
        digest = hashlib.sha256(data).hexdigest()
        if rows != meta["expected_rows"]:
            raise RuntimeError(f"{name}: expected {meta['expected_rows']} rows, got {rows}")
        (ROOT / name).write_bytes(data)
        receipt[name] = {"url": meta["url"], "license": meta["license"],
                         "bytes": len(data), "rows": rows, "sha256": digest}
        print(name, rows, digest[:12])
    (ROOT / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
