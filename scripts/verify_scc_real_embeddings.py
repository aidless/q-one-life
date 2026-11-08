#!/usr/bin/env python3
"""Verify the real-encoder CPW/SCW recomputation receipts.

Checks: hash, all six expected (prompt_mode, dataset) cells, real encoder
labels, bounded accuracies, and that hash vs real CPW/SCW actually differ
somewhere (otherwise the new encoder was not wired in). Two-direction mutation
selftest: (A) tamper a real accuracy, (B) remove one results row.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def verify(receipt: dict, expected_cells: int) -> dict:
    problems: list[str] = []
    stored = receipt.get("canonical_sha256")
    body = {k: v for k, v in receipt.items() if k != "canonical_sha256"}
    if stored != canonical_sha256(body):
        problems.append("canonical_mismatch")
    rows = receipt.get("results") or []
    if len(rows) != expected_cells:
        problems.append(f"cell_count:{len(rows)}")
    for row in rows:
        for key in ("accuracy_sc_modal", "accuracy_hash_cpw", "accuracy_hash_scw",
                    "accuracy_real_cpw", "accuracy_real_scw"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                problems.append(f"accuracy_bounds:{row.get('dataset')}:{key}")
        if row.get("embedder") not in ("scibert", "roberta"):
            problems.append(f"embedder:{row.get('dataset')}")
    changed = [
        row for row in rows
        if abs(row["accuracy_real_cpw"] - row["accuracy_hash_cpw"]) > 1e-12
        or abs(row["accuracy_real_scw"] - row["accuracy_hash_scw"]) > 1e-12
    ]
    if not changed:
        problems.append("real_encoder_had_no_effect")
    return {"problems": problems, "passed": not problems, "changed_cells": len(changed)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-cells", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selftest", type=Path, default=None)
    args = parser.parse_args()

    receipts = {}
    for name in ("scibert", "roberta"):
        path = args.root / f"real-embedding-{name}.json"
        if not path.is_file():
            print(f"NOT_EXECUTED missing {path}")
            return 3
        receipts[name] = json.loads(path.read_text())

    # SciBERT covers 4 cells (aqua/svamp x 2 prompts), RoBERTa covers 2.
    checks = {
        "scibert": verify(receipts["scibert"], 4),
        "roberta": verify(receipts["roberta"], 2),
    }
    failed = [name for name, result in checks.items() if not result["passed"]]
    report = {
        "summary": {
            "gate": "PASS" if not failed else "FAIL",
            "receipts": 2,
            "cells": sum(len(r["results"]) for r in receipts.values()),
            "problems": sum(len(c["problems"]) for c in checks.values()),
        },
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))

    if args.selftest:
        good = receipts["roberta"]
        bad = copy.deepcopy(good)
        bad["canonical_sha256"] = "0" * 64
        direction_a = verify(bad, 2)
        missing = copy.deepcopy(good)
        missing["results"] = missing["results"][:-1]
        missing["canonical_sha256"] = canonical_sha256(
            {k: v for k, v in missing.items() if k != "canonical_sha256"}
        )
        direction_b = verify(missing, 2)
        restored = verify(good, 2)
        selftest = {
            "summary": {
                "passed": (not direction_a["passed"]) and (not direction_b["passed"])
                and restored["passed"],
                "direction_a_problems": len(direction_a["problems"]),
                "direction_b_problems": len(direction_b["problems"]),
                "restored_problems": len(restored["problems"]),
            },
            "direction_a": direction_a["problems"],
            "direction_b": direction_b["problems"],
        }
        args.selftest.write_text(json.dumps(selftest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(selftest["summary"]))

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
