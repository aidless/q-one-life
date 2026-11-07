"""Recompute the report's headline numbers from the carriers."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from subprocess import run as subprocess_run
from pathlib import Path

from scipy.stats import binomtest


def check(name: str, expected, actual) -> dict:
    return {"check": name, "expected": expected, "actual": actual, "passed": expected == actual}


def _pytest_suite(root: Path) -> int:
    """Run the submission's own test suite; returns pytest's exit code."""
    if not root.exists():
        return 1
    proc = subprocess_run(["python3", "-m", "pytest", "-q", "tests"],
                          cwd=root, capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                               "HF_HUB_OFFLINE": "1"})
    return proc.returncode


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
    paperbench_grade_path = next(
        (args.root / "paperbench-smoke").glob(
            "2026-11-07T10-27-44-GMT_run-group_direct_submission_solver"
            "/*semantic-self-consistency*/grade.json"
        ),
        args.root / "paperbench-smoke/2026-11-07T10-27-44-GMT_run-group_direct_submission_solver"
        / "semantic-self-consistency_609d6c0c-c270-4010-941e-3c7b0aa1ed75/grade.json",
    )
    paperbench_grade = json.loads(paperbench_grade_path.read_text())
    peerread_availability = json.loads((args.root / "peerread-availability/census.json").read_text())
    peerread_agreement = json.loads((args.root / "peerread-agreement/agreement.json").read_text())
    llm_tce = json.loads((args.root / "ridar-detector/result-llm-tce.json").read_text())
    autolab_code = json.loads((args.root / "autonomous-code-lab/qone-generated.json").read_text())
    autolab_exec = json.loads((args.root / "autonomous-code-lab/qone-execution.json").read_text())
    autolab_verdict = json.loads((args.root / "autonomous-code-lab/qone-verdict.json").read_text())
    proj_receipt = json.loads((args.root / "autonomous-project-lab/qone-project-receipt.json").read_text())
    proj_verdict = json.loads((args.root / "autonomous-project-lab/qone-project-verdict.json").read_text())
    pb_loop_verdict = json.loads((args.root / "autonomous-paperbench-loop/qone-pb-verdict.json").read_text())
    pb_loop_grade = next(json.loads(p.read_text()) for p in
                         (args.root / "paperbench-smoke/2026-11-07T14-59-44-GMT_run-group_direct_submission_solver")
                         .glob("semantic-self-consistency*/grade.json"))
    fullpkg_receipt = json.loads((args.root / "autonomous-full-package/qone-full-receipt.json").read_text())
    fullpkg_verdict = json.loads((args.root / "autonomous-full-package/qone-full-verdict.json").read_text())
    fullpkg_package = json.loads((args.root / "autonomous-full-package/qone-full-package.json").read_text())
    fullpkg_grade = next(json.loads(p.read_text()) for p in
                         (args.root / "paperbench-smoke/2026-11-07T15-26-43-GMT_run-group_direct_submission_solver")
                         .glob("semantic-self-consistency*/grade.json"))
    allmodel_receipt = json.loads((args.root / "autonomous-allmodel-core/receipt.json").read_text())
    allmodel_verdict = json.loads((args.root / "autonomous-allmodel-core/verdict.json").read_text())
    allmodel_package = json.loads((args.root / "autonomous-allmodel-core/package.json").read_text())
    allmodel_grade = next(json.loads(p.read_text()) for p in
                          (args.root / "paperbench-smoke/2026-11-07T15-37-44-GMT_run-group_direct_submission_solver")
                          .glob("semantic-self-consistency*/grade.json"))
    cloud_log = (args.root / "cloud-allmodel-smoke/result.log").read_text()
    executor_status = json.loads((args.root / "cloud-allmodel-smoke/executor/status.json").read_text())
    executor_result = json.loads((args.root / "cloud-allmodel-smoke/executor/outputs/result.json").read_text())
    decision_rows = [json.loads(line) for line in
                     (args.root / "cloud-allmodel-smoke/decisions/measurements.jsonl")
                     .read_text().splitlines() if line.strip()]
    coverage = json.loads((args.root / "external-task-coverage/coverage.json").read_text())
    archive_summary = json.loads((args.root / "external-task-coverage/runs/archive-summary.json").read_text())
    cloud_matrix = json.loads((args.root / "external-task-coverage/cloud/matrix.json").read_text())
    evidence_contract = json.loads((args.root / "external-task-coverage/evidence-contract.json").read_text())
    hidden_local = json.loads((args.root / "external-task-coverage/hidden/local-result.json").read_text())
    hidden_cloud = json.loads((args.root / "external-task-coverage/hidden/cloud-result.json").read_text())
    hidden_selftest = json.loads((args.root / "external-task-coverage/hidden/selftest.json").read_text())
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
        check("llm_tce_requested", 12, llm_tce["requested"]),
        check("llm_tce_judged", 12, llm_tce["judged"]),
        check("llm_tce_precision", 1.0, llm_tce["precision"]),
        check("llm_tce_recall", 0.5, llm_tce["recall"]),
        check("llm_tce_stopped_after_dev", True,
              llm_tce["stop"] == "eligible_for_new_preregistration"),
        check("paperbench_dummy_score", 1.0, paperbench_grade["score"]),
        check("autolab_code_hash", "dde4f80487ce5acd2c74599eb65a242ff08626a255bc03a6505bae338dde68b7",
              autolab_code["code_sha256"]),
        check("autolab_execution_returncode", 0, autolab_exec["returncode"]),
        check("autolab_sandbox_network", "not_granted", autolab_exec["sandbox"]["network"]),
        check("autolab_hidden_tests_passed", True, autolab_verdict["passed"]),
        check("project_lab_schema", "q-one-project-lab-v1", proj_receipt["schema"]),
        check("project_lab_file_count", 4, len(proj_receipt["files"])),
        check("project_lab_pytest_passed", 0, proj_verdict["pytest_returncode"]),
        check("project_lab_run_passed", 0, proj_verdict["run_returncode"]),
        check("project_lab_passed", True, proj_verdict["passed"]),
        check("paperbench_loop_project_passed", True, pb_loop_verdict["passed"]),
        check("paperbench_loop_grade", 1.0, pb_loop_grade["score"]),
        check("fullpkg_file_count", 10, len(fullpkg_receipt["files"])),
        check("fullpkg_manifest", "f02bf47bf9482d0758b1fb57b7e252bd3286d8ae7fc92686a5c3592568b59498",
              fullpkg_receipt["manifest_sha256"]),
        check("fullpkg_model_fragments", 3, len(fullpkg_receipt["model_fragments"])),
        check("fullpkg_verification_passed", True, fullpkg_verdict["passed"]),
        check("fullpkg_package_files", 12, fullpkg_package["file_count"]),
        check("fullpkg_grade", 1.0, fullpkg_grade["score"]),
        check("allmodel_fragments", 6, len(allmodel_receipt["model_fragments"])),
        check("allmodel_required_files", 10, len(allmodel_receipt["required_files"])),
        check("allmodel_verification_passed", True, allmodel_verdict["passed"]),
        check("allmodel_package_files", 12, allmodel_package["file_count"]),
        check("allmodel_grade", 1.0, allmodel_grade["score"]),
        check("allmodel_cloud_pytest", True, "6 passed" in cloud_log),
        check("allmodel_cloud_run_output", True, '"chosen": "1"' in cloud_log),
        check("allmodel_cloud_core_hash", True,
              "7a8de9ac7b8b015ec5341378ec030585341e22ba8d852a413375bbab25258ac4" in cloud_log),
        check("formal_executor_state", "succeeded", executor_status["state"]),
        check("formal_executor_exit_code", 0, executor_status["exit_code"]),
        check("formal_executor_result_state", "ok", executor_result["state"]),
        check("cloud_decision_rows", 2, len(decision_rows)),
        check("cloud_decision_types", ["decision", "outcome"], [r["type"] for r in decision_rows]),
        check("cloud_outcome_matched", True, decision_rows[1]["payload"]["matched"]),
        check("external_task_count", 10, coverage["summary"]["tasks"]),
        check("external_task_text_materialised", 10, coverage["summary"]["text_materialised"]),
        check("external_task_submissions", 10, coverage["summary"]["with_qone_submission"]),
        check("external_task_real_scores", 0, coverage["summary"]["real_score_count"]),
        check("external_task_archived", 10, archive_summary["summary"]["graded_tasks"]),
        check("external_task_dummy_scores", 10, archive_summary["summary"]["dummy_scores"]),
        check("external_task_real_score_zero", 0, archive_summary["summary"]["real_scores"]),
        check("external_cloud_matrix_tasks", 10, cloud_matrix["summary"]["tasks"]),
        check("external_cloud_entry_ok", 10, cloud_matrix["summary"]["entry_ok"]),
        check("external_cloud_test_packages", 10, cloud_matrix["summary"]["test_packages"]),
        check("external_cloud_total_tests", 48, cloud_matrix["summary"]["total_tests"]),
        check("evidence_contract_tasks", 10, evidence_contract["summary"]["tasks"]),
        check("evidence_contract_leaves", 2776, evidence_contract["summary"]["rubric_leaves"]),
        check("evidence_contract_verified_leaves", 0, evidence_contract["summary"]["verified_leaves"]),
        check("evidence_contract_real_scores", 0, evidence_contract["summary"]["real_judge_scores"]),
        check("hidden_gate_local_pass", "PASS", hidden_local["summary"]["gate"]),
        check("hidden_gate_cloud_pass", "PASS", hidden_cloud["summary"]["gate"]),
        check("hidden_gate_leaks", 0, hidden_local["summary"]["hidden_leaks"]),
        check("hidden_selftest_passed", True, hidden_selftest["summary"]["passed"]),
        check("hidden_mutation_a_problems", 9, hidden_selftest["summary"]["direction_a_problems"]),
        check("hidden_mutation_b_problems", 10, hidden_selftest["summary"]["direction_b_problems"]),
        check("paperbench_dummy_judge", "dummy",
              paperbench_grade["paperbench_result"]["judge_output"]["judge_type"]),
        check("paperbench_reproduction_skipped", True,
              paperbench_grade["paperbench_result"]["skipped_reproduction"]),
        check("paperbench_dev_tasks_graded", 3, len(list(
            (args.root / "paperbench-smoke/2026-11-07T14-34-31-GMT_run-group_direct_submission_solver")
            .glob("*/grade.json")))),
        check("paperbench_dev_min_score", 1.0, min(
            json.loads(p.read_text())["score"] for p in
            (args.root / "paperbench-smoke/2026-11-07T14-34-31-GMT_run-group_direct_submission_solver")
            .glob("*/grade.json"))),
        check("self_expansion_smoke_tests", 0, _pytest_suite(
            args.root.parent / "paperbench-submissions/self-expansion")),
        check("self_composing_tests", 0, _pytest_suite(
            args.root.parent / "paperbench-submissions/self-composing-policies")),
        check("semantic_self_consistency_tests", 0, _pytest_suite(
            args.root.parent / "paperbench-submissions/semantic-self-consistency")),
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
        "llm_tce_confusion": llm_tce["confusion"],
        "paperbench_dummy_score": paperbench_grade["score"],
        "autolab_hidden_tests_passed": autolab_verdict["passed"],
        "project_lab_passed": proj_verdict["passed"],
        "paperbench_loop_grade": pb_loop_grade["score"],
        "fullpkg_grade": fullpkg_grade["score"],
        "allmodel_grade": allmodel_grade["score"],
        "allmodel_cloud_pytest": "6 passed" in cloud_log,
        "formal_executor_state": executor_status["state"],
        "cloud_decision_hit_rate": 1.0,
        "external_task_count": coverage["summary"]["tasks"],
        "external_real_score_count": coverage["summary"]["real_score_count"],
        "external_archived_count": archive_summary["summary"]["graded_tasks"],
        "external_cloud_total_tests": cloud_matrix["summary"]["total_tests"],
        "evidence_contract_leaves": evidence_contract["summary"]["rubric_leaves"],
        "hidden_selftest_passed": hidden_selftest["summary"]["passed"],
    }
    print(json.dumps(report, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
