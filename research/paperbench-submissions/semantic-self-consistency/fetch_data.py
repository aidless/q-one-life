#!/usr/bin/env python3
"""Fetch and verify the exact public dataset files used by this submission."""

from __future__ import annotations

import json
from pathlib import Path

from src.datasets import DATA_DIR, dataset_manifest, fetch_data, load_aqua_rat_test, load_strategyqa_test, load_svamp_full


def main() -> int:
    fetch_data()
    counts = {
        "aqua_rat": len(load_aqua_rat_test()),
        "svamp": len(load_svamp_full()),
        "strategyqa": len(load_strategyqa_test()),
    }
    receipt = {"schema": "qone-scc-data-receipt-v1", "counts": counts,
               "manifest": dataset_manifest()}
    (DATA_DIR / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
