"""Aggregate bounded research-validation runs without inventing a composite score."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_run(directory: Path, kinds: dict[str, str] | None = None) -> dict[str, Any]:
    receipt = json.loads((directory / "receipt.json").read_text())
    prompt_tokens = 0
    completion_tokens = 0
    call_errors = 0
    for path in sorted(directory.glob("call-*.json")):
        call = json.loads(path.read_text())
        usage = call.get("usage") or {}
        prompt_tokens += int(usage.get("prompt_tokens") or 0)
        completion_tokens += int(usage.get("completion_tokens") or 0)
        if call.get("error_type"):
            call_errors += 1
    hash_failures = []
    for entry in receipt.get("outputs") or []:
        target = directory / entry["path"]
        if not target.is_file() or digest(target) != entry["sha256"]:
            hash_failures.append(entry["path"])
    metrics = receipt.get("metrics") or {}
    return {
        "directory": directory.name,
        "task_id": receipt.get("task_id"),
        "kind": (kinds or {}).get(receipt.get("task_id")),
        "seed": receipt.get("seed"),
        "variant": receipt.get("variant"),
        "status": receipt.get("status"),
        "metric_name": metrics.get("metric_name"),
        "baseline_test": metrics.get("baseline_test"),
        "validation": metrics.get("validation"),
        "test": metrics.get("test"),
        "test_delta": metrics.get("test_delta"),
        "replay_matches": receipt.get("replay_matches"),
        "test_used_for_selection": receipt.get("test_used_for_selection"),
        "model_calls": receipt.get("model_calls"),
        "failure_type": receipt.get("failure_type"),
        "failure": receipt.get("failure"),
        "call_errors": call_errors,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "elapsed_sec": receipt.get("elapsed_sec"),
        "hash_failures": hash_failures,
        "environment": receipt.get("environment"),
    }


def paired(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for run in runs:
        if run["status"] != "completed":
            continue
        by_key.setdefault((run["task_id"], run["seed"]), {})[run["variant"]] = run
    rows = []
    for (task_id, seed), variants in sorted(by_key.items()):
        if not {"single_agent", "multi_agent", "no_rebuttal"} <= set(variants):
            continue
        row = {"task_id": task_id, "seed": seed}
        for name, run in variants.items():
            row[f"{name}_delta"] = run["test_delta"]
            row[f"{name}_calls"] = run.get("model_calls")
            row[f"{name}_tokens"] = (run.get("prompt_tokens") or 0) + (run.get("completion_tokens") or 0)
        row["multi_minus_single"] = variants["multi_agent"]["test_delta"] - variants["single_agent"]["test_delta"]
        row["multi_minus_no_rebuttal"] = (
            variants["multi_agent"]["test_delta"] - variants["no_rebuttal"]["test_delta"]
        )
        rows.append(row)
    return rows


def render(runs: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> str:
    lines = [
        "| task | seed | variant | v_validation | v_test | baseline_test | test_delta | calls | tokens | replay | status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in sorted(runs, key=lambda item: (item["task_id"] or "", item["seed"] or 0, item["variant"] or "")):
        values = [
            run["task_id"] or "-",
            str(run["seed"]),
            run["variant"] or "-",
            f"{run['validation']:.4f}" if run["validation"] is not None else "-",
            f"{run['test']:.4f}" if run["test"] is not None else "-",
            f"{run['baseline_test']:.4f}" if run["baseline_test"] is not None else "-",
            f"{run['test_delta']:+.4f}" if run["test_delta"] is not None else "-",
            str(run["model_calls"]),
            str(run["prompt_tokens"] + run["completion_tokens"]),
            "yes" if run["replay_matches"] else "no",
            run["status"] or "-",
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines += [
        "",
        "| task | seed | single | multi | no_rebuttal | multi-single | multi-no_rebuttal |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in pairs:
        values = [
            row["task_id"],
            str(row["seed"]),
            f"{row['single_agent_delta']:+.4f}",
            f"{row['multi_agent_delta']:+.4f}",
            f"{row['no_rebuttal_delta']:+.4f}",
            f"{row['multi_minus_single']:+.4f}",
            f"{row['multi_minus_no_rebuttal']:+.4f}",
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def sign_test(differences: list[float]) -> dict[str, Any]:
    from scipy.stats import binomtest

    positive = sum(value > 0 for value in differences)
    negative = sum(value < 0 for value in differences)
    ties = len(differences) - positive - negative
    if positive + negative == 0:
        return {"positive": 0, "negative": 0, "ties": ties, "p_two_sided": None}
    result = binomtest(positive, positive + negative, 0.5, alternative="two-sided")
    return {"positive": positive, "negative": negative, "ties": ties,
            "p_two_sided": float(result.pvalue)}


def variant_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    from statistics import median

    output: dict[str, Any] = {}
    for variant in ("single_agent", "multi_agent", "no_rebuttal"):
        subset = [run for run in runs if run["variant"] == variant and run["status"] == "completed"]
        for metric in ("balanced_accuracy", "r2"):
            values = [run["test_delta"] for run in subset if run["metric_name"] == metric]
            if not values:
                continue
            output[f"{variant}:{metric}"] = {
                "n": len(values), "median_delta": median(values),
                "mean_delta": sum(values) / len(values),
                "min": min(values), "max": max(values),
                "positive": sum(value > 0 for value in values),
                "zero": sum(value == 0 for value in values),
            }
    return output


def kind_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    from statistics import median

    output: dict[str, Any] = {}
    for variant in ("single_agent", "multi_agent", "no_rebuttal"):
        for kind in ("reproduction", "extension", "null"):
            values = [run["test_delta"] for run in runs
                      if run["variant"] == variant and run["kind"] == kind
                      and run["status"] == "completed" and run["test_delta"] is not None]
            if values:
                output[f"{variant}:{kind}"] = {
                    "n": len(values), "median_delta": median(values),
                    "min": min(values), "max": max(values),
                    "positive": sum(value > 0 for value in values),
                }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--suite", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args()
    kinds: dict[str, str] = {}
    if args.suite and args.suite.is_file():
        suite = json.loads(args.suite.read_text())
        kinds = {task["task_id"]: task["kind"] for task in suite["tasks"]}
    runs = []
    for directory in sorted(args.root.iterdir()):
        if directory.is_dir() and (directory / "receipt.json").is_file():
            runs.append(load_run(directory, kinds))
    pairs = paired(runs)
    report = {
        "root": str(args.root),
        "runs": runs,
        "paired": pairs,
        "variant_stats": variant_stats(runs),
        "kind_stats": kind_stats(runs),
        "sign_tests": {
            "multi_minus_single": sign_test([row["multi_minus_single"] for row in pairs]),
            "multi_minus_no_rebuttal": sign_test([row["multi_minus_no_rebuttal"] for row in pairs]),
        },
        "counts": {
            "runs": len(runs),
            "completed": sum(run["status"] == "completed" for run in runs),
            "inconclusive": sum(run["status"] != "completed" for run in runs),
            "hash_failures": sum(bool(run["hash_failures"]) for run in runs),
            "replay_failures": sum(run["status"] == "completed" and run["replay_matches"] is not True for run in runs),
            "test_used_for_selection": sum(
                run["status"] == "completed" and run["test_used_for_selection"] is not False for run in runs
            ),
        },
        "scope": "bounded algorithm/parameter research; per-task paired deltas only, no cross-task composite",
    }
    text = render(runs, pairs)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(text)
    print(json.dumps(report["counts"]))
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
