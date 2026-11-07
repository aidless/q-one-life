#!/usr/bin/env python3
"""Verify local/cloud real-data probe receipts with two-direction mutations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_EXECUTED = 3

EXPECTED_ROWS = 1941
EXPECTED_SCENARIO_ROWS = 9705
EXPECTED_K = 10
EXPECTED_DATASETS = {"aqua_rat": 254, "svamp": 1000, "strategyqa": 687}


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_receipt(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "qone-scc-real-data-probe-receipt-v1":
        raise ValueError("unexpected receipt schema")
    if not isinstance(receipt.get("payload"), dict):
        raise ValueError("receipt has no payload")
    return receipt


def verify(
    local: dict[str, Any],
    cloud: dict[str, Any],
    *,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    problems: list[str] = []
    local_payload = local["payload"]
    cloud_payload = cloud["payload"]
    local_digest = canonical_sha256(local_payload)
    cloud_digest = canonical_sha256(cloud_payload)
    if local.get("canonical_sha256") != local_digest:
        problems.append("local_canonical_mismatch")
    if cloud.get("canonical_sha256") != cloud_digest:
        problems.append("cloud_canonical_mismatch")
    if local_digest != cloud_digest:
        problems.append("local_cloud_canonical_mismatch")
    if local.get("canonical_sha256") != cloud.get("canonical_sha256"):
        problems.append("receipt_hash_mismatch")
    if local_payload.get("model_used") is not False or cloud_payload.get("model_used") is not False:
        problems.append("model_used_not_false")
    if local_payload.get("paid_api_used") is not False or cloud_payload.get("paid_api_used") is not False:
        problems.append("paid_api_used_not_false")
    if local_payload.get("k") != EXPECTED_K:
        problems.append("unexpected_k")
    summary = local_payload.get("summary", {})
    if summary.get("rows") != expected_rows:
        problems.append("rows_mismatch")
    if summary.get("scenario_rows") != EXPECTED_SCENARIO_ROWS:
        problems.append("scenario_rows_mismatch")
    if summary.get("exceptions") != 0:
        problems.append("exceptions_nonzero")
    datasets = local_payload.get("datasets", {})
    for name, rows in EXPECTED_DATASETS.items():
        if datasets.get(name, {}).get("rows") != rows:
            problems.append(f"dataset_rows:{name}")
    invariants = local_payload.get("invariants", {})
    if not all(invariants.values()):
        problems.append("invariants_failed")
    return {
        "schema": "qone-scc-real-data-probe-verification-v1",
        "summary": {
            "gate": "PASS" if not problems else "FAIL",
            "not_executed": False,
            "problems": len(problems),
            "problem_list": problems,
            "canonical_sha256": local_digest,
            "rows": summary.get("rows"),
            "scenario_rows": summary.get("scenario_rows"),
            "expected_rows": expected_rows,
        },
        "local_runtime": local.get("runtime", {}),
        "cloud_runtime": cloud.get("runtime", {}),
    }


def self_test(local: dict[str, Any], cloud: dict[str, Any]) -> dict[str, Any]:
    base = verify(local, cloud)
    mutated_cloud = copy.deepcopy(cloud)
    mutated_cloud["canonical_sha256"] = "0" * 64
    direction_a = verify(local, mutated_cloud)
    direction_b = verify(local, cloud, expected_rows=EXPECTED_ROWS + 1)
    restored = verify(local, cloud)
    a_hash_failures = sum(
        1 for problem in direction_a["summary"]["problem_list"]
        if "canonical" in problem or "hash" in problem
    )
    b_row_failures = sum(
        1 for problem in direction_b["summary"]["problem_list"]
        if problem == "rows_mismatch"
    )
    passed = (
        base["summary"]["problems"] == 0
        and direction_a["summary"]["problems"] > 0
        and direction_b["summary"]["problems"] > 0
        and restored["summary"]["problems"] == 0
        and a_hash_failures > 0
        and b_row_failures > 0
    )
    return {
        "schema": "qone-scc-real-data-probe-verification-selftest-v1",
        "summary": {
            "passed": passed,
            "base_problems": base["summary"]["problems"],
            "direction_a_problems": direction_a["summary"]["problems"],
            "direction_b_problems": direction_b["summary"]["problems"],
            "restored_problems": restored["summary"]["problems"],
            "direction_a_hash_failures": a_hash_failures,
            "direction_b_row_failures": b_row_failures,
            "direction_a_mutation": "cloud canonical hash replaced with zeros",
            "direction_b_mutation": "expected rows raised by one",
            "counter_fixture_band": "actual rows equal correct expectation and are below the broken expectation",
        },
        "base": base["summary"],
        "direction_a": direction_a["summary"],
        "direction_b": direction_b["summary"],
        "restored": restored["summary"],
    }


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_not_executed(path: Path, reason: str) -> None:
    payload = {
        "schema": "qone-scc-real-data-probe-verification-v1",
        "summary": {
            "gate": "NOT_EXECUTED",
            "not_executed": True,
            "problems": "unavailable",
            "note": "gate_did_not_execute_not_equal_pass",
            "reason": reason,
        },
    }
    write_receipt(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", type=Path, required=True)
    parser.add_argument("--cloud", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        local = load_receipt(args.local)
        cloud = load_receipt(args.cloud)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        write_not_executed(args.output, str(exc))
        print("gate=NOT_EXECUTED problems=unavailable note=gate_did_not_execute_not_equal_pass")
        return EXIT_NOT_EXECUTED
    if args.self_test:
        receipt = self_test(local, cloud)
        write_receipt(args.output, receipt)
        summary = receipt["summary"]
        print(
            f"selftest={'PASS' if summary['passed'] else 'FAIL'} "
            f"base={summary['base_problems']} a={summary['direction_a_problems']} "
            f"b={summary['direction_b_problems']} restored={summary['restored_problems']}"
        )
        return EXIT_OK if summary["passed"] else EXIT_FAIL
    receipt = verify(local, cloud)
    write_receipt(args.output, receipt)
    summary = receipt["summary"]
    print(
        f"gate={summary['gate']} problems={summary['problems']} "
        f"rows={summary['rows']} scenario_rows={summary['scenario_rows']} "
        f"canonical={summary['canonical_sha256'][:12]}"
    )
    return EXIT_OK if summary["problems"] == 0 else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
