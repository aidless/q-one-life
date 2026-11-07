#!/usr/bin/env python3
"""Deterministic behaviour probe over the three verified public datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

K = 10
METHODS = ("first_response", "modal", "cpw", "scw")
SCENARIOS = (
    "all_gold",
    "majority_gold",
    "minority_gold",
    "parse_noise",
    "no_answer",
)


def canonical_sha256(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def response_text(question: str, answer: str) -> str:
    return f"Reasoning for {question}\nThe answer is {answer}."


def build_responses(question: str, gold: str, scenario: str) -> list[str]:
    gold_response = response_text(question, gold)
    distractor = f"{gold}_alt"
    distractor_response = response_text(question, distractor)
    if scenario == "all_gold":
        return [gold_response for _ in range(K)]
    if scenario == "majority_gold":
        return [gold_response] * 6 + [distractor_response] * 4
    if scenario == "minority_gold":
        return [gold_response] * 4 + [distractor_response] * 6
    if scenario == "parse_noise":
        forms = [
            f"The answer is ({gold}).",
            f"The answer is {gold}.",
            f"The answer is  {gold}  .",
            f"The answer is ({gold})",
            f"The answer is {gold}   ",
            f"The answer is ({gold}.)",
            f"The answer is {gold}...",
            f"The answer is (({gold}))",
            f"The answer is {gold} .",
            f"The answer is ( {gold} ).",
        ]
        return [f"Reasoning for {question}\n{form}" for form in forms]
    if scenario == "no_answer":
        return [f"Reasoning for {question}" for _ in range(K)]
    raise ValueError(f"unknown scenario: {scenario}")


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-root", type=Path, required=True)
    parser.add_argument("--host-label", default="local")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    root = args.submission_root.resolve()
    sys.path.insert(0, str(root))
    from src.datasets import load_aqua_rat_test, load_strategyqa_test, load_svamp_full
    from src.methods import cpw_answer, scw_answer
    from src.utils import modal_answer, parse_answer

    datasets = {
        "aqua_rat": load_aqua_rat_test(),
        "svamp": load_svamp_full(),
        "strategyqa": load_strategyqa_test(),
    }
    payload: dict = {
        "schema": "qone-scc-real-data-probe-v1",
        "model_used": False,
        "paid_api_used": False,
        "k": K,
        "scenarios": list(SCENARIOS),
        "methods": list(METHODS),
        "datasets": {},
        "summary": {},
        "invariants": {},
    }
    for dataset_name, rows in datasets.items():
        dataset_result = {"rows": len(rows), "scenarios": {}}
        for scenario in SCENARIOS:
            method_counts = {method: {"matches_gold": 0, "answered": 0} for method in METHODS}
            parse_failures = 0
            exceptions = 0
            for row in rows:
                question = str(row["question"])
                gold = str(row["correct"])
                responses = build_responses(question, gold, scenario)
                parsed = [parse_answer(text) for text in responses]
                parse_failures += sum(value is None for value in parsed)
                try:
                    values = {
                        "first_response": parsed[0],
                        "modal": modal_answer(parsed),
                        "cpw": cpw_answer(responses, None, "scibert"),
                        "scw": scw_answer(responses, None, "scibert"),
                    }
                except Exception:
                    exceptions += 1
                    values = {method: None for method in METHODS}
                for method, value in values.items():
                    if value is not None:
                        method_counts[method]["answered"] += 1
                    if value == gold:
                        method_counts[method]["matches_gold"] += 1
            dataset_result["scenarios"][scenario] = {
                "parse_failures": parse_failures,
                "exceptions": exceptions,
                "methods": {
                    method: {
                        "matches_gold": counts["matches_gold"],
                        "answered": counts["answered"],
                        "recovery": rate(counts["matches_gold"], len(rows)),
                    }
                    for method, counts in method_counts.items()
                },
            }
        payload["datasets"][dataset_name] = dataset_result

    total_rows = sum(item["rows"] for item in payload["datasets"].values())
    scenario_rows = total_rows * len(SCENARIOS)
    total_exceptions = sum(
        scenario["exceptions"]
        for dataset in payload["datasets"].values()
        for scenario in dataset["scenarios"].values()
    )
    aggregate = {scenario: {method: {"matches_gold": 0, "answered": 0} for method in METHODS}
                 for scenario in SCENARIOS}
    parse_failures_by_scenario = {scenario: 0 for scenario in SCENARIOS}
    for dataset in payload["datasets"].values():
        for scenario, data in dataset["scenarios"].items():
            parse_failures_by_scenario[scenario] += data["parse_failures"]
            for method, counts in data["methods"].items():
                aggregate[scenario][method]["matches_gold"] += counts["matches_gold"]
                aggregate[scenario][method]["answered"] += counts["answered"]
    payload["summary"] = {
        "rows": total_rows,
        "scenario_rows": scenario_rows,
        "exceptions": total_exceptions,
        "parse_failures_by_scenario": parse_failures_by_scenario,
    }
    all_gold = aggregate["all_gold"]
    parse_noise = aggregate["parse_noise"]
    no_answer = aggregate["no_answer"]
    invariants = {
        "all_gold_all_methods_recovered": all(
            all_gold[method]["matches_gold"] == total_rows for method in METHODS
        ),
        "majority_gold_modal_recovered":
            aggregate["majority_gold"]["modal"]["matches_gold"] == total_rows,
        "minority_gold_modal_not_recovered":
            aggregate["minority_gold"]["modal"]["matches_gold"] == 0,
        "parse_noise_no_failures": parse_failures_by_scenario["parse_noise"] == 0,
        "no_answer_all_unparsed":
            parse_failures_by_scenario["no_answer"] == total_rows * K,
        "no_answer_no_method_answered": all(
            no_answer[method]["answered"] == 0 for method in METHODS
        ),
        "no_exceptions": total_exceptions == 0,
    }
    payload["invariants"] = invariants
    payload["summary"]["invariants_passed"] = all(invariants.values())
    payload["summary"]["problems"] = 0 if (total_exceptions == 0 and all(invariants.values())) else 1
    digest = canonical_sha256(payload)
    receipt = {
        "schema": "qone-scc-real-data-probe-receipt-v1",
        "canonical_sha256": digest,
        "payload": payload,
        "runtime": {
            "host_label": args.host_label,
            "python_executable": sys.executable,
            "elapsed_sec": round(time.monotonic() - start, 3),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"probe={'PASS' if payload['summary']['problems'] == 0 else 'FAIL'} "
        f"problems={payload['summary']['problems']} rows={total_rows} "
        f"scenario_rows={scenario_rows} canonical={digest[:12]}"
    )
    return 0 if payload["summary"]["problems"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
