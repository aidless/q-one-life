#!/usr/bin/env python3
"""Build a terminal-state ledger for all 2776 PaperBench rubric leaves.

The generated ledger is an execution contract, not evidence of completion.
Every leaf starts `unverified` and must eventually become `verified`,
`out_of_scope_waived`, or `blocked` before the full10 gate can pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "qone-paperbench-leaf-ledger-v1"
EXPECTED_LEAVES = 2776
TERMINAL_STATES = frozenset({
    "unverified", "carrier_present", "executed", "recomputed", "judge_scored",
    "out_of_scope_waived", "blocked",
})


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def leaves(node: dict) -> list[dict]:
    children = node.get("sub_tasks") or []
    if not children:
        return [node]
    out: list[dict] = []
    for child in children:
        out.extend(leaves(child))
    return out


def waiver_for(paper_id: str, addendum: str) -> list[dict]:
    """Conservative, explicit waiver rules from addendum text.

    Only leaves whose own requirement names a clearly out-of-scope subject are
    waived. Empty addendum means no waivers; no keyword guessing is used.
    """
    if not addendum.strip():
        return []
    markers = (
        ("out of scope", "out_of_scope"),
        ("deemed out of scope", "out_of_scope"),
    )
    lowered = addendum.lower()
    if not any(marker in lowered for marker, _ in markers):
        return []
    return [{
        "addendum_path": f"/tmp/paperbench-upstream/project/paperbench/data/papers/{paper_id}/addendum.md",
        "addendum_sha256": sha256_text(addendum),
        "reason": "addendum_contains_out_of_scope_clause",
        "scope": "out_of_scope",
        "note": "candidate only; each waived leaf must cite its exact clause",
    }]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    rows = coverage["rows"]
    entries: list[dict] = []
    tasks: list[dict] = []
    for row in rows:
        paper_id = row["paper_id"]
        paper_dir = args.papers / paper_id
        rubric = json.loads((paper_dir / "rubric.json").read_text(encoding="utf-8"))
        addendum_path = paper_dir / "addendum.md"
        addendum = addendum_path.read_text(encoding="utf-8") if addendum_path.is_file() else ""
        waivers = waiver_for(paper_id, addendum)
        for leaf in leaves(rubric):
            entries.append({
                "leaf_id": leaf["id"],
                "task_id": paper_id,
                "split": row["split"],
                "requirements": leaf["requirements"],
                "scope": "in_scope",
                "terminal_state": "unverified",
                "carrier_paths": [],
                "carrier_sha256": [],
                "recompute_command": "",
                "judge_scores": {},
                "waiver": {},
                "blocked_reason": "",
                "addendum_waivers": waivers,
            })
        tasks.append({
            "task_id": paper_id,
            "split": row["split"],
            "rubric_leaves": len(leaves(rubric)),
            "status": "architecture_stub",
            "asset_manifest": "",
            "checkpoint": "",
        })
    payload = {
        "schema": SCHEMA,
        "source_revision": coverage["source_revision"],
        "expected_leaves": EXPECTED_LEAVES,
        "terminal_states": sorted(TERMINAL_STATES),
        "panel": {
            "official": False,
            "judge_type": "free_multimodel",
            "model_ids": [],
            "locked": False,
            "user_go": {},
        },
        "tasks": tasks,
        "leaves": entries,
        "summary": {
            "total_leaves": len(entries),
            "verified": 0,
            "out_of_scope_waived": 0,
            "blocked": 0,
            "unverified": len(entries),
            "gate": "NOT_EXECUTED",
        },
    }
    payload["canonical_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in payload.items() if k != "canonical_sha256"},
                   sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(payload["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
