"""Recompute the report's headline numbers from the carriers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scipy.stats import binomtest


def check(name: str, expected, actual) -> dict:
    return {"check": name, "expected": expected, "actual": actual, "passed": expected == actual}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    results = json.loads((args.root / "results.json").read_text())
    faults = json.loads((args.root / "cloud-full/faults.json").read_text())
    peerread = json.loads((args.root / "peerread-check/result.json").read_text())
    peerread_match = json.loads((args.root / "peerread-submission-match/match.json").read_text())
    peerread_expanded = json.loads((args.root / "peerread-expanded/result.json").read_text())
    peerread_heldout = json.loads((args.root / "peerread-heldout/heldout.json").read_text())
    peerread_availability = json.loads((args.root / "peerread-availability/census.json").read_text())
    peerread_agreement = json.loads((args.root / "peerread-agreement/agreement.json").read_text())
    ridar_files = json.loads((args.root / "datasets/ridar-full-manifest.json").read_text())
    ridar_audit = json.loads((args.root / "ridar-audit/audit.json").read_text())
    runs = results["runs"]
    completed = [run for run in runs if run["status"] == "completed"]
    pairs = results["paired"]

    def sign(values):
        positive = sum(value > 0 for value in values)
        negative = sum(value < 0 for value in values)
        if positive + negative == 0:
            return None
        return round(float(binomtest(positive, positive + negative, 0.5).pvalue), 4)

    checks = [
        check("runs", 54, len(runs)),
        check("completed", 44, len(completed)),
        check("inconclusive", 10, len(runs) - len(completed)),
        check("hash_failures", 0, sum(bool(run["hash_failures"]) for run in completed)),
        check("replay_failures", 0, sum(run["replay_matches"] is not True for run in completed)),
        check("test_used_for_selection", 0,
              sum(run["test_used_for_selection"] is not False for run in completed)),
        check("all_inconclusive_are_schema_errors", 10,
              sum((run["failure_type"] or "") == "ValidationError" for run in runs
                  if run["status"] != "completed")),
        check("complete_task_seed_pairs", 10, len(pairs)),
        check("sign_test_multi_vs_single", 0.7266,
              sign([row["multi_minus_single"] for row in pairs])),
        check("sign_test_multi_vs_no_rebuttal", 0.6875,
              sign([row["multi_minus_no_rebuttal"] for row in pairs])),
        check("faults_injected", 10, faults["injected"]),
        check("faults_detected", 10, faults["detected"]),
        check("positive_controls", 2, faults["positive_controls"]),
        check("peerread_status", "exploratory_unmatched_versions", peerread["status"]),
        check("peerread_usable", 24, peerread["usable"]),
        check("peerread_pilot_matched", 24, peerread_match["matched"]),
        check("peerread_pilot_body_identical", 23, peerread_match["body_identical"]),
        check("peerread_pilot_title_match", 24, peerread_match["title_match"]),
        check("peerread_expanded_usable", 28, peerread_expanded["usable"]),
        check("peerread_expanded_status", "repository_parsed_pilot", peerread_expanded["status"]),
        check("peerread_expanded_rho_crosses_zero",
              peerread_expanded["bootstrap_rho_95ci"][0] < 0 < peerread_expanded["bootstrap_rho_95ci"][1],
              True),
        check("peerread_heldout_test_n", 6, peerread_heldout["test"]["n"]),
        check("peerread_heldout_test_ci_crosses_zero",
              peerread_heldout["test"]["ci"][0] < 0 < peerread_heldout["test"]["ci"][1], True),
        check("peerread_census_papers", 78, peerread_availability["total_papers"]),
        check("peerread_census_parsed", 40, peerread_availability["total_parsed"]),
        check("peerread_census_reviewed", 66, peerread_availability["total_reviewed"]),
        check("peerread_census_usable", 28, peerread_availability["total_usable"]),
        check("peerread_agreement_rows", 169, peerread_agreement["review_rows"]),
        check("peerread_agreement_papers", 66, peerread_agreement["papers_with_reviews"]),
        check("peerread_agreement_icc", 0.124, round(peerread_agreement["icc_1_1"], 3)),
        check("peerread_agreement_exact", 0.303,
              round(peerread_agreement["pairwise_exact_agreement"], 3)),
        check("peerread_agreement_within_one", 0.746,
              round(peerread_agreement["pairwise_within_one_point"], 3)),
        check("model_calls_total", 188, sum(run["model_calls"] for run in runs)),
        check("tokens_total", 804272,
              sum(run["prompt_tokens"] + run["completion_tokens"] for run in runs)),
        check("ridar_trace_files", 60, len(ridar_files["files"])),
        check("ridar_trace_bytes", 61459066,
              sum(record["bytes"] for record in ridar_files["files"])),
        check("ridar_records", 47797, ridar_audit["records_total"]),
        check("ridar_acts", 766, ridar_audit["acts_total"]),
        check("ridar_spans", 3461, ridar_audit["evidence_spans_total"]),
        check("ridar_spans_out_of_range", 0, ridar_audit["spans_out_of_range_total"]),
        check("ridar_categories_present", 13, ridar_audit["coverage"]["categories_present_in_data"]),
        check("ridar_trace_level_checks", 0, ridar_audit["coverage"]["implemented_trace_level"]),
    ]
    report = {
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
        "peerread_rho": peerread["spearman_rho"],
        "peerread_permutation_p": peerread["spearman_permutation_p"],
        "peerread_expanded_rho": peerread_expanded["spearman_rho"],
        "peerread_heldout_test_rho": peerread_heldout["test"]["rho"],
    }
    print(json.dumps(report, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
