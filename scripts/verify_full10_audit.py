#!/usr/bin/env python3
"""Deterministic gate for checkpoint and blocked-leaf audit artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def check(name: str, expected, actual) -> dict:
    return {"check": name, "expected": expected, "actual": actual,
            "passed": expected == actual}


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def verify(root: Path) -> dict:
    ledger = json.loads((root / "leaf-ledger.json").read_text(encoding="utf-8"))
    sync = json.loads((root / "full10-checkpoint-sync.json").read_text(encoding="utf-8"))
    gap = json.loads((root / "full10-gap-matrix.json").read_text(encoding="utf-8"))
    state_counts = {}
    for leaf in ledger["leaves"]:
        state_counts[leaf["terminal_state"]] = state_counts.get(leaf["terminal_state"], 0) + 1

    sync_body = {k: v for k, v in sync.items() if k != "canonical_sha256"}
    gap_body = {k: v for k, v in gap.items() if k != "canonical_sha256"}
    mismatches = []
    for row in sync["tasks"]:
        path = root / "tasks" / row["path"]
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "verified_leaves": row["state_counts"].get("verified", 0),
            "waived_leaves": row["state_counts"].get("out_of_scope_waived", 0),
            "blocked_leaves": row["state_counts"].get("blocked", 0),
            "unverified_leaves": row["state_counts"].get("unverified", 0),
        }
        if any(checkpoint.get(key) != value for key, value in expected.items()):
            mismatches.append(row["task_id"])

    checks = [
        check("ledger_leaves", 2776, len(ledger["leaves"])),
        check("ledger_verified", 3, state_counts.get("verified", 0)),
        check("ledger_waived", 22, state_counts.get("out_of_scope_waived", 0)),
        check("ledger_blocked", 2751, state_counts.get("blocked", 0)),
        check("ledger_unverified", 0, state_counts.get("unverified", 0)),
        check("sync_schema", "qone-full10-checkpoint-sync-v1", sync["schema"]),
        check("sync_tasks", 10, sync["summary"]["tasks"]),
        check("sync_problems", 0, sync["summary"]["problems"]),
        check("sync_canonical", sync["canonical_sha256"], canonical_sha256(sync_body)),
        check("checkpoint_mismatches", 0, len(mismatches)),
        check("gap_schema", "qone-full10-gap-matrix-v1", gap["schema"]),
        check("gap_total_leaves", 2776, gap["total_leaves"]),
        check("gap_blocked_leaves", 2751, gap["blocked_leaves"]),
        check("gap_state_counts", sorted(state_counts.items()),
              sorted(gap["state_counts"].items())),
        check("gap_rows", 2776, len(gap["rows"])),
        check("gap_promotions", 0, gap["summary"]["promoted_leaves"]),
        check("gap_gate", "REVIEW_ONLY", gap["summary"]["gate"]),
        check("gap_canonical", gap["canonical_sha256"], canonical_sha256(gap_body)),
    ]
    report = {"checks": checks, "passed": all(row["passed"] for row in checks),
              "summary": {"gate": "PASS" if all(row["passed"] for row in checks) else "FAIL",
                          "checks": len(checks)}}
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    report = verify(args.root)
    if args.selftest:
        gap = json.loads((args.root / "full10-gap-matrix.json").read_text(encoding="utf-8"))
        mutation = {k: v for k, v in gap.items() if k != "canonical_sha256"}
        mutation["blocked_leaves"] = 0
        mutation["canonical_sha256"] = canonical_sha256(mutation)
        temp = Path("/tmp/qone-full10-audit-selftest")
        temp.mkdir(parents=True, exist_ok=True)
        (temp / "leaf-ledger.json").write_bytes((args.root / "leaf-ledger.json").read_bytes())
        (temp / "full10-checkpoint-sync.json").write_bytes(
            (args.root / "full10-checkpoint-sync.json").read_bytes())
        (temp / "full10-gap-matrix.json").write_text(
            json.dumps(mutation, ensure_ascii=False), encoding="utf-8")
        (temp / "tasks").mkdir(exist_ok=True)
        for path in (args.root / "tasks").glob("*/CHECKPOINT.json"):
            target = temp / "tasks" / path.parent.name
            target.mkdir(exist_ok=True)
            (target / "CHECKPOINT.json").write_bytes(path.read_bytes())
        mutated = verify(temp)
        report["selftest"] = {"summary": {"passed": not mutated["passed"],
                                          "direction": "blocked_leaf_count_mutation"}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
