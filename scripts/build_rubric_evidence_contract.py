#!/usr/bin/env python3
"""Build a per-leaf evidence contract for selected PaperBench tasks.

This is a static audit aid, not a judge. It classifies each rubric leaf by the
kind of carrier that would be needed to support it and records which local
carriers currently exist. It never marks a leaf as passed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_PAPERS = Path("/tmp/paperbench-upstream/project/paperbench/data/papers")
DEFAULT_SUBMISSIONS = Path("research/paperbench-submissions")
DEFAULT_COVERAGE = Path("research/validation-20261106/external-task-coverage/coverage.json")

CATEGORY_CONTRACT = {
    "Code Development": {
        "carrier": "source_code_or_config",
        "required_artifacts": ["run.py", "src/", "tests/"],
        "verification": "static_file_census_plus_smoke_tests",
    },
    "Code Execution": {
        "carrier": "execution_log",
        "required_artifacts": ["results/", "logs_or_receipts"],
        "verification": "rerun_and_compare_hashes",
    },
    "Result Analysis": {
        "carrier": "result_table_or_plot",
        "required_artifacts": ["results/table_or_figure", "claim_ledger_entry"],
        "verification": "recompute_numbers_from_raw_results",
    },
    "Logging, Analysis & Presentation": {
        "carrier": "result_table_or_plot",
        "required_artifacts": ["results/table_or_figure", "claim_ledger_entry"],
        "verification": "recompute_numbers_from_raw_results",
    },
}

FINE_CONTRACT = {
    "Dataset and Model Acquisition": "dataset_manifest_with_hashes",
    "Experimental Setup": "frozen_config_or_hyperparameters",
    "Method Implementation": "unit_tests_and_source_code",
    "Data Processing & Preparation": "input_output_examples",
    "Evaluation, Metrics & Benchmarking": "metric_definition_and_raw_scores",
    "Logging, Analysis & Presentation": "saved_logs_and_figure",
}

TRIGGER_GROUPS = {
    "needs_external_data": ["dataset", "download", "benchmark", "available for use"],
    "needs_model_or_api": ["model", "api", "inference", "pretrained", "checkpoint"],
    "needs_training": ["trained", "training", "epoch", "timesteps", "seed", "optimizer"],
    "needs_evaluation": ["accuracy", "score", "success rate", "performance", "evaluation", "metric"],
    "needs_figure_or_table": ["table", "figure", "plot", "curve", "results show"],
    "needs_judge": ["outperforms", "better", "shows that", "demonstrates", "as well as"],
}


def leaves(node: dict[str, Any]) -> list[dict[str, Any]]:
    children = node.get("sub_tasks") or []
    if not children:
        return [node]
    out: list[dict[str, Any]] = []
    for child in children:
        out.extend(leaves(child))
    return out


def classify_leaf(leaf: dict[str, Any]) -> dict[str, Any]:
    text = leaf["requirements"].lower()
    category = leaf.get("task_category") or "Unspecified"
    fine = leaf.get("finegrained_task_category") or "Unspecified"
    contract = CATEGORY_CONTRACT.get(category, {
        "carrier": "unclassified",
        "required_artifacts": [],
        "verification": "manual_review_required",
    })
    triggers = sorted(name for name, words in TRIGGER_GROUPS.items() if any(w in text for w in words))
    return {
        "leaf_id": leaf["id"],
        "requirements": leaf["requirements"],
        "task_category": category,
        "finegrained_task_category": fine,
        "primary_carrier": contract["carrier"],
        "fine_carrier": FINE_CONTRACT.get(fine, "manual_specification"),
        "required_artifacts": contract["required_artifacts"],
        "verification": contract["verification"],
        "triggers": triggers,
        "current_state": "unverified",
        "reason": "Static contract only; no real judge or recomputed result is attached.",
    }


def local_carriers(submission_dir: Path) -> dict[str, Any]:
    if not submission_dir.exists():
        return {"exists": False, "files": 0, "has_run": False, "has_tests": False,
                "has_results": False, "has_manifest": False}
    files = [p for p in submission_dir.rglob("*") if p.is_file()]
    return {
        "exists": True,
        "files": len(files),
        "has_run": (submission_dir / "run.py").is_file(),
        "has_tests": (submission_dir / "tests").is_dir() and any((submission_dir / "tests").glob("*.py")),
        "has_results": (submission_dir / "results").is_dir() and any((submission_dir / "results").iterdir()),
        "has_manifest": (submission_dir / "MANIFEST.json").is_file(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, default=DEFAULT_PAPERS)
    parser.add_argument("--submissions", type=Path, default=DEFAULT_SUBMISSIONS)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    coverage = json.loads(args.coverage.read_text())
    tasks = []
    global_categories = Counter()
    global_triggers = Counter()
    for row in coverage["rows"]:
        paper_id = row["paper_id"]
        rubric = json.loads((args.papers / paper_id / "rubric.json").read_text())
        entries = [classify_leaf(leaf) for leaf in leaves(rubric)]
        for entry in entries:
            global_categories[entry["primary_carrier"]] += 1
            global_triggers.update(entry["triggers"])
        carriers = local_carriers(args.submissions / paper_id)
        tasks.append({
            "paper_id": paper_id,
            "split": row["split"],
            "rubric_leaves": len(entries),
            "local_carriers": carriers,
            "carrier_counts": dict(Counter(e["primary_carrier"] for e in entries)),
            "trigger_counts": dict(Counter(t for e in entries for t in e["triggers"])),
            "leaves": entries,
        })
    summary = {
        "tasks": len(tasks),
        "rubric_leaves": sum(t["rubric_leaves"] for t in tasks),
        "primary_carrier_counts": dict(global_categories),
        "trigger_counts": dict(global_triggers),
        "verified_leaves": 0,
        "real_judge_scores": 0,
        "note": "No leaf is marked verified by this static contract.",
    }
    payload = {"schema": "qone-rubric-evidence-contract-v1", "summary": summary, "tasks": tasks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
