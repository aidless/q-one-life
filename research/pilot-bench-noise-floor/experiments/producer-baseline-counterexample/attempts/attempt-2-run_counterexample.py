#!/usr/bin/env python3
"""Run the preregistered producer-baseline necessity counterexample.

The experiment is deliberately small and standard-library-only. It tests a
logical claim with deterministic synthetic labels; it is not an estimate of the
external validity of any real leaderboard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


class ExperimentError(ValueError):
    """Raised when the frozen protocol or construction is invalid."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExperimentError(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def labels_for_blocks(
    truth: list[int],
    *,
    wrong_label: int,
    error_blocks: list[list[int]],
) -> list[int]:
    labels = list(truth)
    for block in error_blocks:
        if (
            not isinstance(block, list)
            or len(block) != 2
            or not all(isinstance(value, int) for value in block)
        ):
            raise ExperimentError(f"invalid error block: {block!r}")
        start, stop = block
        if start < 0 or stop < start or stop > len(labels):
            raise ExperimentError(f"error block out of range: {block!r}")
        for index in range(start, stop):
            labels[index] = wrong_label
    return labels


def majority(labels: list[int]) -> int | None:
    if not labels:
        raise ExperimentError("strict-majority helper requires at least one label")
    for candidate in sorted(set(labels)):
        if labels.count(candidate) * 2 > len(labels):
            return candidate
    return None


def gold_from_producers(producers: dict[str, list[int]]) -> list[int | None]:
    names = sorted(producers)
    if len(names) != 3:
        raise ExperimentError("the frozen construction requires exactly three producers")
    rows = list(zip(*(producers[name] for name in names), strict=True))
    return [majority(list(row)) for row in rows]


def leave_one_out_gold(
    producers: dict[str, list[int]], excluded: str
) -> list[int | None]:
    peers = [name for name in sorted(producers) if name != excluded]
    rows = list(zip(*(producers[name] for name in peers), strict=True))
    return [majority(list(row)) for row in rows]


def score(labels: list[int], gold: list[int | None]) -> dict[str, Any]:
    if len(labels) != len(gold):
        raise ExperimentError("labels and gold have different lengths")
    scored = 0
    correct = 0
    for label, reference in zip(labels, gold, strict=True):
        if reference is None:
            continue
        scored += 1
        correct += int(label == reference)
    return {
        "correct": correct,
        "scored": scored,
        "accuracy": correct / scored if scored else None,
    }


def paired_comparison(
    first: list[int],
    second: list[int],
    gold: list[int | None],
) -> dict[str, Any]:
    first_only = 0
    second_only = 0
    both_correct = 0
    neither_correct = 0
    for first_label, second_label, reference in zip(
        first, second, gold, strict=True
    ):
        if reference is None:
            continue
        first_correct = first_label == reference
        second_correct = second_label == reference
        first_only += int(first_correct and not second_correct)
        second_only += int(second_correct and not first_correct)
        both_correct += int(first_correct and second_correct)
        neither_correct += int(not first_correct and not second_correct)
    discordant = first_only + second_only
    one_sided = math.ldexp(1.0, -discordant) if discordant else 1.0
    return {
        "first_only_correct": first_only,
        "second_only_correct": second_only,
        "both_correct": both_correct,
        "neither_correct": neither_correct,
        "discordant": discordant,
        "one_sided_sign_test_p": one_sided,
        "two_sided_sign_test_p": min(1.0, 2.0 * one_sided),
        "test_note": (
            "Exact sign-test tail under the predeclared item-exchangeability null; "
            "the p-value is supporting evidence for the constructed ordering, not "
            "an external leaderboard estimate."
        ),
    }


def relation(first: dict[str, Any], second: dict[str, Any]) -> str:
    first_accuracy = first["accuracy"]
    second_accuracy = second["accuracy"]
    if first_accuracy is None or second_accuracy is None:
        return "undefined"
    if first_accuracy > second_accuracy:
        return "first_gt_second"
    if first_accuracy < second_accuracy:
        return "first_lt_second"
    return "tie"


def jackknife_pair_stability(
    first: list[int],
    second: list[int],
    gold: list[int | None],
    *,
    expected_relation: str,
) -> dict[str, Any]:
    stable = 0
    undefined = 0
    differences: list[float] = []
    for omitted in range(len(gold)):
        reduced_gold = gold[:omitted] + gold[omitted + 1 :]
        reduced_first = first[:omitted] + first[omitted + 1 :]
        reduced_second = second[:omitted] + second[omitted + 1 :]
        first_score = score(reduced_first, reduced_gold)["accuracy"]
        second_score = score(reduced_second, reduced_gold)["accuracy"]
        if first_score is None or second_score is None:
            undefined += 1
            continue
        differences.append(first_score - second_score)
        observed = (
            "first_gt_second"
            if first_score > second_score
            else "first_lt_second"
            if first_score < second_score
            else "tie"
        )
        stable += int(observed == expected_relation)
    return {
        "deletions": len(gold),
        "defined": len(differences),
        "stable": stable,
        "undefined": undefined,
        "all_defined_deletions_stable": stable == len(differences),
        "min_first_minus_second": min(differences) if differences else None,
        "max_first_minus_second": max(differences) if differences else None,
    }


def verify_frozen_inputs(
    preregistration_path: Path,
    preregistration: dict[str, Any],
    implementation_path: Path,
) -> dict[str, Any]:
    if preregistration.get("schema") != "q-one-preregistration-v1":
        raise ExperimentError("unsupported preregistration schema")
    implementation = preregistration.get("implementation", {})
    if not isinstance(implementation, dict):
        raise ExperimentError("implementation metadata must be an object")
    implementation_sha256 = sha256_file(implementation_path)
    if implementation.get("sha256") != implementation_sha256:
        raise ExperimentError(
            "runner SHA-256 does not match the preregistered implementation"
        )

    manuscript = preregistration.get("manuscript", {})
    if not isinstance(manuscript, dict):
        raise ExperimentError("manuscript metadata must be an object")
    manuscript_path = Path(str(manuscript.get("path", "")))
    if not manuscript_path.is_absolute():
        manuscript_path = preregistration_path.parent / manuscript_path
    manuscript_path = manuscript_path.resolve()
    if not manuscript_path.is_file():
        raise ExperimentError(f"manuscript is missing: {manuscript_path}")
    manuscript_sha256 = sha256_file(manuscript_path)
    if manuscript.get("sha256") != manuscript_sha256:
        raise ExperimentError("manuscript SHA-256 changed after preregistration")

    return {
        "preregistration_sha256": sha256_file(preregistration_path),
        "implementation_sha256": implementation_sha256,
        "manuscript_sha256": manuscript_sha256,
    }


def run_condition(
    condition: dict[str, Any],
    *,
    n_items: int,
    margin_threshold: float,
) -> dict[str, Any]:
    truth = [int(condition.get("truth_label", 0))] * n_items
    wrong_label = int(condition.get("wrong_label", 1))
    producer_specs = condition.get("producers")
    system_specs = condition.get("systems")
    if not isinstance(producer_specs, dict) or not isinstance(system_specs, dict):
        raise ExperimentError("condition producers and systems must be objects")

    producers = {
        name: labels_for_blocks(
            truth,
            wrong_label=wrong_label,
            error_blocks=spec.get("error_blocks", []),
        )
        for name, spec in sorted(producer_specs.items())
    }
    systems = {
        name: labels_for_blocks(
            truth,
            wrong_label=wrong_label,
            error_blocks=spec.get("error_blocks", []),
        )
        for name, spec in sorted(system_specs.items())
    }
    gold = gold_from_producers(producers)
    full_gold_matches_truth = all(reference == label for label, reference in zip(truth, gold))

    producer_scores = {}
    for name in sorted(producers):
        loo_gold = leave_one_out_gold(producers, name)
        producer_scores[name] = {
            **score(producers[name], loo_gold),
            "loo_gold_ties": sum(reference is None for reference in loo_gold),
        }
    floor_score = max(item["accuracy"] for item in producer_scores.values())

    system_scores = {
        name: score(labels, gold) for name, labels in sorted(systems.items())
    }
    ranked = sorted(
        system_scores,
        key=lambda name: (
            system_scores[name]["accuracy"] is not None,
            system_scores[name]["accuracy"] or float("-inf"),
            name,
        ),
        reverse=True,
    )
    leader = ranked[0]
    leader_score = system_scores[leader]["accuracy"]
    margin = leader_score - floor_score
    readable = margin >= margin_threshold

    pair = condition.get("ranked_pair")
    if (
        not isinstance(pair, list)
        or len(pair) != 2
        or pair[0] not in systems
        or pair[1] not in systems
    ):
        raise ExperimentError(f"invalid ranked_pair: {pair!r}")
    first, second = pair
    observed_relation = relation(system_scores[first], system_scores[second])
    expected_relation = str(condition.get("expected_relation"))
    stability = jackknife_pair_stability(
        systems[first],
        systems[second],
        gold,
        expected_relation=expected_relation,
    )
    paired = paired_comparison(systems[first], systems[second], gold)

    expected_gate = bool(condition.get("expected_gate_readable"))
    checks = {
        "gate_reading_matches": readable == expected_gate,
        "ranked_relation_matches": observed_relation == expected_relation,
        "all_delete_one_orders_stable": stability["all_defined_deletions_stable"],
    }
    return {
        "condition_id": condition.get("condition_id"),
        "role": condition.get("role"),
        "n_items": n_items,
        "gold_rule": "strict majority of three producer labels",
        "full_gold_matches_truth": full_gold_matches_truth,
        "producer_loo_scores": producer_scores,
        "producer_floor": floor_score,
        "system_scores": system_scores,
        "leader": leader,
        "leader_score": leader_score,
        "margin": margin,
        "margin_threshold": margin_threshold,
        "gate_readable": readable,
        "expected_gate_readable": expected_gate,
        "ranked_pair": [first, second],
        "observed_relation": observed_relation,
        "expected_relation": expected_relation,
        "paired_comparison": paired,
        "delete_one_stability": stability,
        "checks": checks,
        "expected_signature_met": all(checks.values()),
    }


def run(
    preregistration_path: Path,
    implementation_path: Path,
) -> dict[str, Any]:
    preregistration = load_json(preregistration_path)
    frozen = verify_frozen_inputs(
        preregistration_path, preregistration, implementation_path
    )
    n_items = preregistration.get("design", {}).get("n_items")
    margin_threshold = preregistration.get("design", {}).get("margin_threshold")
    conditions = preregistration.get("conditions")
    if not isinstance(n_items, int) or n_items < 3:
        raise ExperimentError("design.n_items must be an integer >= 3")
    if not isinstance(margin_threshold, (int, float)):
        raise ExperimentError("design.margin_threshold must be numeric")
    if not isinstance(conditions, list) or not conditions:
        raise ExperimentError("conditions must be a non-empty array")

    results = [
        run_condition(
            condition,
            n_items=n_items,
            margin_threshold=float(margin_threshold),
        )
        for condition in conditions
    ]
    critical = next(
        (item for item in results if item["role"] == "critical_counterexample"),
        None,
    )
    positive = next(
        (item for item in results if item["role"] == "positive_control"),
        None,
    )
    negative = next(
        (item for item in results if item["role"] == "negative_control"),
        None,
    )
    all_expected = all(item["expected_signature_met"] for item in results)
    h1_supported = bool(
        all_expected
        and critical
        and positive
        and negative
        and critical["gate_readable"] is False
        and critical["observed_relation"] == "first_gt_second"
        and critical["delete_one_stability"]["all_defined_deletions_stable"]
        and positive["gate_readable"] is True
        and negative["observed_relation"] == "first_lt_second"
    )
    return {
        "schema": "q-one-counterexample-receipt-v1",
        "experiment_id": preregistration.get("experiment_id"),
        "frozen_inputs": frozen,
        "design": {
            "n_items": n_items,
            "margin_threshold": margin_threshold,
            "gate_rule": "leader_score - producer_floor >= margin_threshold",
            "seed": None,
            "randomness": "none; every label and error block is deterministic",
        },
        "conditions": results,
        "all_expected_signatures_met": all_expected,
        "hypothesis_decision": (
            "reject_H0_in_declared_synthetic_condition"
            if h1_supported
            else "H1_not_supported"
        ),
        "narrow_conclusion": (
            "The declared producer-baseline gate can refuse a top ordering that is "
            "deterministic and stable under every single-item deletion. Therefore "
            "clearance of that gate is not a necessary condition for every resolvable "
            "top ordering, and the gate cannot by itself be read as a general ranking "
            "noise bound."
            if h1_supported
            else
            "The frozen experiment did not reproduce the predeclared counterexample signature."
        ),
        "interpretation_limits": [
            "This is a synthetic logical witness, not a study of real leaderboard prevalence.",
            "The result does not show that the producer floor is uninformative in every benchmark.",
            "The result does not establish any model's accuracy on a real task.",
            "Sign-test p-values describe the constructed item sample only.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    preregistration_path = args.preregistration.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    implementation_path = Path(__file__).resolve()
    try:
        receipt = run(preregistration_path, implementation_path)
    except (ExperimentError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    write_json(output_path, receipt)
    print(json.dumps({
        "output": str(output_path),
        "sha256": sha256_file(output_path),
        "hypothesis_decision": receipt["hypothesis_decision"],
        "all_expected_signatures_met": receipt["all_expected_signatures_met"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["hypothesis_decision"] == "reject_H0_in_declared_synthetic_condition" else 1


if __name__ == "__main__":
    raise SystemExit(main())
