#!/usr/bin/env python3
"""Classify blocked full10 leaves into reproducible gap categories.

The classifier is deterministic keyword matching over each leaf's own
requirement and blocked reason. It does not mark any leaf verified and does not
infer that a resource is available from classification alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

CATEGORIES = (
    ("paid_model_inference", (
        "gpt-3.5", "gpt-4o", "paid", "openai api", "paid api")),
    ("gated_or_licensed_data", (
        "imagenet-1k", "imagenet validation", "imagenet test", "objectnet",
        "gated", "401", "license", "must be authenticated")),
    ("long_rl_training", (
        "1m timestep", "10 seeds", "10 seed", "meta-world", "spaceinvaders",
        "freeway", "ppo", "offline rl", "d4rl", "exorl", "rollout")),
    ("model_training_or_weights", (
        "dpo", "pplm", "fine-tun", "training", "trained", "pretrained",
        "weights", "model zoo", "vlm", "36 vision", "39 vision")),
    ("benchmark_or_dataset", (
        "dataset", "benchmark", "wikitext", "prompts", "samples",
        "imageNet-c", "imageNet-v2", "sketch", "rendition")),
    ("judge_evidence", (
        "judge", "disagreement", "score", "spread", "mean", "not promoted")),
    ("code_or_implementation", (
        "code has been", "code for", "implemented", "implementation")),
    ("result_or_claim", (
        "outperform", "achieve", "accuracy", "results show", "reduces",
        "increases", "slope", "correlation")),
)


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def classify(text: str) -> tuple[str, str]:
    lowered = text.lower()
    for category, markers in CATEGORIES:
        for marker in markers:
            if marker.lower() in lowered:
                return category, marker
    return "unclassified", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    rows = []
    leaves = ledger["leaves"]
    blocked = [leaf for leaf in leaves if leaf["terminal_state"] == "blocked"]
    for leaf in leaves:
        state = leaf["terminal_state"]
        if state == "blocked":
            text = f"{leaf.get('requirements', '')}\n{leaf.get('blocked_reason', '')}"
            category, marker = classify(text)
        elif state == "verified":
            category, marker = "verified", "terminal_state"
        elif state == "out_of_scope_waived":
            category, marker = "out_of_scope_waived", "terminal_state"
        else:
            category, marker = "nonterminal", "terminal_state"
        rows.append({
            "leaf_id": leaf["leaf_id"], "task_id": leaf["task_id"],
            "terminal_state": state,
            "category": category, "marker": marker,
            "has_carriers": bool(leaf.get("carrier_paths")),
            "has_hashes": bool(leaf.get("carrier_sha256")),
            "has_recompute": bool(leaf.get("recompute_command")),
            "judge_score_count": len(leaf.get("judge_scores") or {}),
            "requirement_sha256": hashlib.sha256(
                leaf.get("requirements", "").encode("utf-8")).hexdigest(),
        })
    categories = Counter(row["category"] for row in rows)
    state_counts = Counter(row["terminal_state"] for row in rows)
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task_id"], Counter())[row["category"]] += 1
    body = {
        "schema": "qone-full10-gap-matrix-v1",
        "source_ledger": str(args.ledger),
        "total_leaves": len(rows),
        "blocked_leaves": len(blocked),
        "state_counts": dict(sorted(state_counts.items())),
        "categories": dict(sorted(categories.items())),
        "by_task": {task: dict(sorted(counts.items()))
                    for task, counts in sorted(by_task.items())},
        "carrier_present": sum(row["has_carriers"] for row in rows),
        "hash_present": sum(row["has_hashes"] for row in rows),
        "recompute_present": sum(row["has_recompute"] for row in rows),
        "judge_scored_leaves": sum(row["judge_score_count"] > 0 for row in rows),
        "rows": rows,
        "summary": {"gate": "REVIEW_ONLY", "promoted_leaves": 0,
                    "note": "Classification is not evidence of completion; no leaf state changed."},
    }
    body["canonical_sha256"] = canonical_sha256(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"total_leaves": len(rows), "blocked_leaves": len(blocked),
                      "categories": body["categories"],
                      "gate": body["summary"]["gate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
