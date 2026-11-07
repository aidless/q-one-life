#!/usr/bin/env python3
"""Host-side hidden contract gate for the ten PaperBench submission packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_EXECUTED = 3

DEFAULT_PYTHON = sys.executable
VENV_PYTHON = Path.home() / ".cache/qone-life-venv/bin/python"
SCAN_SUFFIXES = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".sh"}
REQUIRED_PATHS = ("run.py", "data/sample.json", "tests", "results", "README.md")


class GateNotExecuted(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def load_contract(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GateNotExecuted(f"hidden contract missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise GateNotExecuted(f"hidden contract is not JSON: {path}") from exc
    if payload.get("schema") != "qone-host-hidden-contract-v1":
        raise GateNotExecuted("unexpected hidden contract schema")
    if payload.get("host_only") is not True:
        raise GateNotExecuted("hidden contract must be host_only")
    if payload.get("never_include_in_model_prompt") is not True:
        raise GateNotExecuted("hidden contract must forbid model prompts")
    if not isinstance(payload.get("tasks"), list) or not payload["tasks"]:
        raise GateNotExecuted("hidden contract has no tasks")
    if not isinstance(payload.get("leak_markers"), list) or not payload["leak_markers"]:
        raise GateNotExecuted("hidden contract has no leak markers")
    if not isinstance(payload.get("allowed_status"), list) or not payload["allowed_status"]:
        raise GateNotExecuted("hidden contract has no allowed status values")
    for entry in payload["tasks"]:
        if not isinstance(entry, dict) or not str(entry.get("paper_id") or "").strip():
            raise GateNotExecuted("hidden contract task needs paper_id")
        if int(entry.get("min_pytest_cases", 0)) <= 0:
            raise GateNotExecuted("hidden contract task needs positive min_pytest_cases")
    return payload


def discover_rows(contract: dict[str, Any], submissions_root: Path) -> list[tuple[dict[str, Any], Path]]:
    if not submissions_root.is_dir():
        raise GateNotExecuted(f"submissions root missing: {submissions_root}")
    rows = []
    for spec in contract["tasks"]:
        paper_id = spec["paper_id"]
        directory = submissions_root / paper_id
        if not directory.is_dir():
            raise GateNotExecuted(f"submission directory missing: {directory}")
        rows.append((spec, directory))
    return rows


def scan_for_leaks(directory: Path, markers: list[str]) -> list[str]:
    leaks = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        text = path.read_text(errors="ignore")
        if any(marker in text for marker in markers):
            leaks.append(path.relative_to(directory).as_posix())
    return leaks


def run_one(
    spec: dict[str, Any],
    directory: Path,
    contract: dict[str, Any],
    *,
    isolate_cwd: bool,
    shared_cwd: Path | None,
    min_delta: int,
    python_executable: str,
) -> dict[str, Any]:
    problems: list[str] = []
    leaks = scan_for_leaks(directory, contract["leak_markers"])
    if leaks:
        problems.append("hidden_contract_leak")

    for relative in REQUIRED_PATHS:
        if not (directory / relative).exists():
            problems.append(f"missing:{relative}")
    tests_dir = directory / "tests"
    if tests_dir.is_dir() and not any(tests_dir.glob("*.py")):
        problems.append("empty:tests")
    results_dir = directory / "results"
    if results_dir.is_dir() and not any(p.is_file() for p in results_dir.iterdir()):
        problems.append("empty:results")

    cwd = directory if isolate_cwd else shared_cwd
    if cwd is None:
        problems.append("no_execution_cwd")
        cwd = directory

    sample_path = directory / "data/sample.json"
    sample = sample_path.read_bytes() if sample_path.is_file() else b"{}"
    with tempfile.TemporaryDirectory(prefix="qone-hidden-gate-") as temporary:
        environment = {
            name: value for name, value in os.environ.items()
            if name in {"PATH", "LANG", "LC_ALL", "PYTHONHASHSEED"}
        }
        environment.update({
            "HF_HUB_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "HOME": temporary,
            "PYTHONUSERBASE": str(Path.home() / ".local"),
        })
        run_process = subprocess.run(
            [python_executable, "run.py"], cwd=cwd, input=sample,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=60, env=environment, check=False,
        )
        run_stdout = run_process.stdout.decode(errors="replace").strip()
        run_stderr = run_process.stderr.decode(errors="replace").strip()
        if run_process.returncode != 0:
            problems.append("run_failed")
        payload: dict[str, Any] | None = None
        if run_stdout:
            try:
                payload = json.loads(run_stdout.splitlines()[-1])
            except ValueError:
                payload = None
        if not isinstance(payload, dict):
            problems.append("run_output_not_json")
        else:
            if payload.get("paper_id") != spec["paper_id"]:
                problems.append("paper_id_mismatch")
            if payload.get("status") not in contract["allowed_status"]:
                problems.append("unexpected_status")

        pytest_process = subprocess.run(
            [python_executable, "-m", "pytest", "-q", "tests"], cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=90, env=environment, check=False,
        )
        pytest_stdout = pytest_process.stdout.decode(errors="replace")
        pytest_stderr = pytest_process.stderr.decode(errors="replace")
        if pytest_process.returncode != 0:
            problems.append("pytest_failed")
        match = re.search(r"(\d+) passed", pytest_stdout)
        cases = int(match.group(1)) if match else 0
        expected_min = int(spec["min_pytest_cases"]) + min_delta
        if cases < expected_min:
            problems.append(f"pytest_case_count:{cases}<{expected_min}")

    return {
        "paper_id": spec["paper_id"],
        "python_executable": python_executable,
        "problems": problems,
        "hidden_leaks": len(leaks),
        "leak_paths": leaks,
        "run_returncode": run_process.returncode,
        "pytest_returncode": pytest_process.returncode,
        "pytest_cases": cases,
        "expected_min_pytest_cases": expected_min,
        "run_stdout_sha256": sha256_text(run_stdout),
        "run_stderr_sha256": sha256_text(run_stderr),
        "pytest_stdout_sha256": sha256_text(pytest_stdout),
        "pytest_stderr_sha256": sha256_text(pytest_stderr),
    }


def run_gate(
    rows: list[tuple[dict[str, Any], Path]],
    contract: dict[str, Any],
    contract_sha256: str,
    *,
    isolate_cwd: bool = True,
    shared_cwd: Path | None = None,
    min_delta: int = 0,
    python_executable: str = DEFAULT_PYTHON,
) -> dict[str, Any]:
    task_results = []
    for spec, directory in rows:
        try:
            task_results.append(run_one(
                spec, directory, contract,
                isolate_cwd=isolate_cwd, shared_cwd=shared_cwd, min_delta=min_delta,
                python_executable=python_executable,
            ))
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            task_results.append({
                "paper_id": spec["paper_id"],
                "problems": [f"execution_error:{type(exc).__name__}"],
                "hidden_leaks": 0,
                "leak_paths": [],
            })
    problems = sum(len(row["problems"]) for row in task_results)
    hidden_leaks = sum(row["hidden_leaks"] for row in task_results)
    ok = sum(1 for row in task_results if not row["problems"])
    return {
        "schema": "qone-host-hidden-contract-result-v1",
        "contract_sha256": contract_sha256,
        "script_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "python_executable": python_executable,
        "summary": {
            "gate": "PASS" if problems == 0 else "FAIL",
            "not_executed": False,
            "problems": problems,
            "tasks": len(task_results),
            "ok": ok,
            "hidden_leaks": hidden_leaks,
            "isolate_cwd": isolate_cwd,
            "min_delta": min_delta,
        },
        "tasks": task_results,
    }


def self_test(
    rows: list[tuple[dict[str, Any], Path]],
    contract: dict[str, Any],
    contract_sha256: str,
    python_executable: str,
) -> dict[str, Any]:
    base = run_gate(rows, contract, contract_sha256, python_executable=python_executable)
    shared_cwd = rows[0][1]
    direction_a = run_gate(
        rows, contract, contract_sha256,
        isolate_cwd=False, shared_cwd=shared_cwd,
        python_executable=python_executable,
    )
    direction_b = run_gate(rows, contract, contract_sha256, min_delta=1,
                           python_executable=python_executable)
    restored = run_gate(rows, contract, contract_sha256,
                        python_executable=python_executable)
    a_mismatches = sum(
        1 for row in direction_a["tasks"] if "paper_id_mismatch" in row["problems"]
    )
    b_count_failures = sum(
        1 for row in direction_b["tasks"]
        if any(p.startswith("pytest_case_count") for p in row["problems"])
    )
    passed = (
        base["summary"]["problems"] == 0
        and direction_a["summary"]["problems"] > 0
        and direction_b["summary"]["problems"] > 0
        and restored["summary"]["problems"] == 0
        and a_mismatches > 0
        and b_count_failures > 0
    )
    return {
        "schema": "qone-host-hidden-contract-self-test-v1",
        "contract_sha256": contract_sha256,
        "script_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "python_executable": python_executable,
        "summary": {
            "passed": passed,
            "base_problems": base["summary"]["problems"],
            "direction_a_problems": direction_a["summary"]["problems"],
            "direction_b_problems": direction_b["summary"]["problems"],
            "restored_problems": restored["summary"]["problems"],
            "direction_a_paper_id_mismatches": a_mismatches,
            "direction_b_case_count_failures": b_count_failures,
            "direction_a_mutation": "shared cwd removes per-task isolation",
            "direction_b_mutation": "min_pytest_cases raised by one",
            "counter_fixture_band": "actual count equals the correct minimum and is below the broken minimum",
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
        "schema": "qone-host-hidden-contract-result-v1",
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
    parser = argparse.ArgumentParser(description="Verify host-only hidden contract for PaperBench packages")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", default=DEFAULT_PYTHON,
                        help="interpreter used to run the submission packages")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        contract = load_contract(args.contract)
        rows = discover_rows(contract, args.submissions)
        probe = subprocess.run(
            [args.python, "-m", "pytest", "--version"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if probe.returncode != 0:
            raise GateNotExecuted(
                f"pytest is unavailable in selected interpreter: {args.python}"
            )
    except GateNotExecuted as exc:
        write_not_executed(args.output, str(exc))
        print(f"gate=NOT_EXECUTED problems=unavailable note=gate_did_not_execute_not_equal_pass reason={exc}")
        return EXIT_NOT_EXECUTED
    except OSError as exc:
        write_not_executed(args.output, f"os error: {exc}")
        print(f"gate=NOT_EXECUTED problems=unavailable note=gate_did_not_execute_not_equal_pass reason=os_error")
        return EXIT_NOT_EXECUTED

    contract_sha256 = sha256_bytes(args.contract.read_bytes())
    if args.self_test:
        receipt = self_test(rows, contract, contract_sha256, args.python)
        write_receipt(args.output, receipt)
        summary = receipt["summary"]
        print(
            f"selftest={'PASS' if summary['passed'] else 'FAIL'} "
            f"base_problems={summary['base_problems']} "
            f"a_problems={summary['direction_a_problems']} "
            f"b_problems={summary['direction_b_problems']} "
            f"restored_problems={summary['restored_problems']}"
        )
        return EXIT_OK if summary["passed"] else EXIT_FAIL

    receipt = run_gate(rows, contract, contract_sha256,
                       python_executable=args.python)
    write_receipt(args.output, receipt)
    summary = receipt["summary"]
    print(
        f"gate={summary['gate']} problems={summary['problems']} "
        f"tasks={summary['tasks']} ok={summary['ok']} hidden_leaks={summary['hidden_leaks']}"
    )
    return EXIT_OK if summary["problems"] == 0 else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
