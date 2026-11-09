#!/usr/bin/env python3
"""Derive task checkpoint counters from the authoritative leaf ledger.

This never changes leaf terminal states. It only repairs stale checkpoint
counters and writes a deterministic sync report for the verification gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def status_for(counts: Counter, total: int) -> str:
    if counts["blocked"] or counts["unverified"]:
        return "BLOCKED"
    if counts["out_of_scope_waived"]:
        return "REPRODUCED_IN_SCOPE"
    if counts["verified"] == total and total > 0:
        return "FULL_REPRODUCTION"
    return "BLOCKED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--tasks-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    leaves = ledger["leaves"]
    per_task: dict[str, Counter] = {}
    for leaf in leaves:
        per_task.setdefault(leaf["task_id"], Counter())[leaf["terminal_state"]] += 1

    rows = []
    problems = []
    for task in ledger["tasks"]:
        task_id = task["task_id"]
        path = args.tasks_root / task_id / "CHECKPOINT.json"
        if not path.is_file():
            problems.append(f"missing_checkpoint:{task_id}")
            continue
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
        counts = per_task.get(task_id, Counter())
        total = task["rubric_leaves"]
        state_sum = sum(counts.values())
        if state_sum != total:
            problems.append(f"leaf_count_mismatch:{task_id}:{state_sum}:{total}")
        checkpoint["verified_leaves"] = counts["verified"]
        checkpoint["waived_leaves"] = counts["out_of_scope_waived"]
        checkpoint["blocked_leaves"] = counts["blocked"]
        checkpoint["unverified_leaves"] = counts["unverified"]
        checkpoint["status"] = status_for(counts, total)
        checkpoint["ledger_state"] = "counts_from_leaf_ledger"
        checkpoint["note"] = "Checkpoint counters synchronized from leaf-ledger.json; not a reproduction result."
        path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rows.append({"task_id": task_id, "path": str(path.relative_to(args.tasks_root)),
                     "rubric_leaves": total, "state_counts": dict(counts),
                     "status": checkpoint["status"]})

    body = {"schema": "qone-full10-checkpoint-sync-v1",
            "source_ledger": str(args.ledger),
            "tasks": rows, "problems": problems,
            "summary": {"tasks": len(rows), "problems": len(problems),
                        "synced": not problems}}
    body["canonical_sha256"] = canonical_sha256(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(body["summary"]))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
