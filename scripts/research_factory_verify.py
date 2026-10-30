#!/usr/bin/env python3
"""Refresh Research Factory verification, pilot status and package receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qone_life.research import sha256_file, validate_research_project
from qone_life.research_factory import (
    audit_arxiv_package,
    build_research_plan,
    write_package_audit,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a receipt without exposing a partially written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def artifact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def research_test_pythonpath(root: Path) -> str:
    sources = {"qone-life-src": root / "src"}
    for sibling in ("q-one-core", "q-one-agent"):
        source = root.parent / sibling / "src"
        if source.is_dir():
            sources[f"{sibling}-src"] = source
    identity = "\0".join(f"{name}={path.resolve()}" for name, path in sources.items())
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    overlay = Path(tempfile.gettempdir()) / f"qone-research-test-paths-{digest}"
    overlay.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for name, source in sources.items():
        link = overlay / name
        if link.is_symlink() and link.resolve() != source.resolve():
            link.unlink()
        if not link.exists():
            link.symlink_to(source.resolve(), target_is_directory=True)
        paths.append(str(link))
    return os.pathsep.join(paths)


def schema_check(root: Path) -> dict[str, Any]:
    code = r"""
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
mappings = {
    "schemas/paper-portfolio.schema.json": [
        "artifacts/research-paper-portfolio/v1/paper-portfolio.json"
    ],
    "schemas/research-project.schema.json": [
        "research/arc-paper-track/project.json",
        "research/pilot-paper11/project.json",
        "research/pilot-bench-noise-floor/project.json",
        "research/pilot-f-acceptance/project.json",
        "research/pilot-gemma/project.json",
        "research/pilot-paper2-coupling/project.json",
        "research/pilot-agent-behavior-regression/project.json",
        "research/pilot-verifier-capture-aggregation/project.json",
        "research/pilot-calibrating-evaluator/project.json",
        "research/pilot-closing-calibration-landscape/project.json",
        "research/pilot-conditional-communication-effects/project.json",
        "research/pilot-memory-architecture-effects/project.json",
        "research/pilot-f2-k-generalization/project.json",
        "research/pilot-f4-verification/project.json",
        "research/pilot-n-sensitive-calibration/project.json",
        "research/pilot-hidden-cost-resampling/project.json",
        "research/pilot-calibration-fatigue/project.json",
    ],
    "schemas/research-triage.schema.json": [
        "artifacts/research-factory/v2/triage.json"
    ],
    "schemas/arxiv-package-audit.schema.json": [
        "artifacts/research-factory/v2/package-audits/f-acceptance.json",
        "artifacts/research-factory/v2/package-audits/noise-floor.json",
        "artifacts/research-factory/v2/package-audits/paper11.json",
        "artifacts/research-factory/v2/package-audits/paper11-overlay.json",
        "artifacts/research-factory/v2/package-audits/paper2-coupling.json",
        "artifacts/research-factory/v2/package-audits/agent-behavior-regression.json",
        "artifacts/research-factory/v2/package-audits/verifier-capture-aggregation.json",
        "artifacts/research-factory/v2/package-audits/closing-landscape.json",
        "artifacts/research-factory/v2/package-audits/memory-architecture.json",
    ],
}
errors = []
checked = 0
for schema_name, payloads in mappings.items():
    schema = json.loads((root / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for payload_name in payloads:
        payload = json.loads((root / payload_name).read_text(encoding="utf-8"))
        checked += 1
        for error in validator.iter_errors(payload):
            errors.append(f"{payload_name}: {error.message}")
print(json.dumps({"checked": checked, "errors": errors}))
"""
    result = run(["/usr/bin/python3", "-c", code, str(root)], cwd=root)
    if result.returncode != 0:
        return {"result": "failed", "error": result.stderr.strip(), "checked": 0, "errors": []}
    payload = json.loads(result.stdout)
    payload["result"] = "passed" if not payload["errors"] else "failed"
    return payload


def claim_summary(report: Path) -> str | None:
    if not report.is_file():
        return None
    match = re.search(r"^## Summary: (.*)$", report.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    artifact_dir = root / "artifacts" / "research-factory" / "v2"
    package_dir = artifact_dir / "package-audits"
    package_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": research_test_pythonpath(root)}

    tests: dict[str, Any]
    if args.skip_tests:
        previous = artifact_dir / "verification.json"
        previous_payload = (
            json.loads(previous.read_text(encoding="utf-8"))
            if previous.is_file()
            else {}
        )
        previous_checks = previous_payload.get("checks", {})
        tests = {
            "pytest": previous_checks.get("pytest", {"result": "unknown", "tests": None}),
            "unittest": previous_checks.get(
                "unittest", {"result": "unknown", "tests": None}
            ),
        }
    else:
        pytest_result = run([sys.executable, "-m", "pytest", "-q"], cwd=root, env=env)
        unittest_result = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=root,
            env=env,
        )
        pytest_match = re.search(
            r"(\d+) passed(?:, (\d+) warning)?(?:, (\d+) subtests passed)?",
            pytest_result.stdout,
        )
        unittest_match = re.search(r"Ran (\d+) tests", unittest_result.stderr)
        tests = {
            "pytest": {
                "result": "passed" if pytest_result.returncode == 0 else "failed",
                "tests": int(pytest_match.group(1)) if pytest_match else None,
                "warnings": int(pytest_match.group(2) or 0) if pytest_match else None,
                "subtests": int(pytest_match.group(3) or 0) if pytest_match else None,
            },
            "unittest": {
                "result": "passed" if unittest_result.returncode == 0 else "failed",
                "tests": int(unittest_match.group(1)) if unittest_match else None,
                "resource_warnings": unittest_result.stderr.count("ResourceWarning"),
            },
        }

    dispositions_result = run(
        [
            sys.executable,
            "scripts/research_dispositions.py",
            "--triage",
            "artifacts/research-factory/v2/triage.json",
            "--review-packets",
            "artifacts/research-factory/v2/review-packets",
            "--output-dir",
            "artifacts/research-factory/v2",
        ],
        cwd=root,
        env=env,
    )
    dispositions_path = artifact_dir / "agent-dispositions.json"
    dispositions = (
        json.loads(dispositions_path.read_text(encoding="utf-8"))
        if dispositions_path.is_file()
        else {}
    )
    triage_payload = json.loads(
        (artifact_dir / "triage.json").read_text(encoding="utf-8")
    )
    triage_family_count = len(triage_payload.get("projects", []))

    ruff = shutil.which("ruff")
    ruff_result = (
        run(
            [
                ruff,
                "check",
                "src/qone_life/research.py",
                "src/qone_life/research_factory.py",
                "src/qone_life/cli.py",
                "tests/test_research.py",
                "tests/test_research_factory.py",
                "tests/test_research_experiment.py",
                "tests/test_research_dispositions.py",
                "scripts/research_portfolio.py",
                "scripts/research_factory.py",
                "scripts/research_review_packets.py",
                "scripts/cleanroom_compile.py",
                "scripts/build_arxiv_archive.py",
                "scripts/research_dispositions.py",
                "research/pilot-f-acceptance/tools",
                "research/pilot-bench-noise-floor/tools",
                "research/pilot-bench-noise-floor/experiments/producer-baseline-counterexample",
                "research/pilot-bench-noise-floor/experiments/kfold-common-support-a3",
                "research/pilot-bench-noise-floor/experiments/threshold-interface-a4",
                "research/pilot-bench-noise-floor/revisions/2026-10-29-support-threshold-r3/run_candidate_gates.py",
                "research/pilot-paper2-coupling/tools",
                "research/pilot-agent-behavior-regression/tools",
                "research/pilot-verifier-capture-aggregation/tools",
                "research/pilot-closing-calibration-landscape/tools",
                "research/pilot-conditional-communication-effects/tools",
                "research/pilot-memory-architecture-effects/tools",
                "research/pilot-f2-k-generalization/tools",
                "research/pilot-f4-verification/tools",
                "research/pilot-n-sensitive-calibration/tools",
                "research/pilot-hidden-cost-resampling/tools",
                "research/pilot-calibration-fatigue/tools",
            ],
            cwd=root,
            env=env,
        )
        if ruff
        else None
    )
    diff_result = run(["git", "diff", "--check"], cwd=root)

    project_paths = [
        root / "research" / "arc-paper-track",
        root / "research" / "pilot-paper11",
        root / "research" / "pilot-bench-noise-floor",
        root / "research" / "pilot-f-acceptance",
        root / "research" / "pilot-gemma",
        root / "research" / "pilot-paper2-coupling",
        root / "research" / "pilot-agent-behavior-regression",
        root / "research" / "pilot-verifier-capture-aggregation",
        root / "research" / "pilot-calibrating-evaluator",
        root / "research" / "pilot-closing-calibration-landscape",
        root / "research" / "pilot-conditional-communication-effects",
        root / "research" / "pilot-memory-architecture-effects",
        root / "research" / "pilot-f2-k-generalization",
        root / "research" / "pilot-f4-verification",
        root / "research" / "pilot-n-sensitive-calibration",
        root / "research" / "pilot-hidden-cost-resampling",
        root / "research" / "pilot-calibration-fatigue",
    ]
    validations = {path.name: validate_research_project(path) for path in project_paths}

    verifier = Path(
        "/home/liuzewen/.codex/skills/paper-writing-agent/scripts/verify_claim_ledger.py"
    )
    claim_results: dict[str, Any] = {}
    for path in project_paths:
        ledger = path / "CLAIM_LEDGER.md"
        if not ledger.is_file():
            continue
        report = path / "reports" / "claim-ledger-verification.md"
        result = run(
            [
                sys.executable,
                str(verifier),
                str(path),
                "--out",
                str(report),
            ],
            cwd=root,
            env=env,
        )
        claim_results[path.name] = {
            "result": "passed" if result.returncode == 0 else "failed",
            "summary": claim_summary(report),
            "report": artifact(report, root) if report.is_file() else None,
        }

    package_specs = [
        ("f-acceptance", root / "research" / "pilot-f-acceptance" / "source"),
        (
            "noise-floor",
            root / "research" / "pilot-bench-noise-floor" / "source",
        ),
        (
            "paper11",
            Path(
                "/home/liuzewen/WorkBuddy/2026-10-22-23-12-56/paper11-latex/v3/paper"
            ),
        ),
        ("paper11-overlay", root / "research" / "pilot-paper11" / "source"),
        (
            "paper2-coupling",
            root / "research" / "pilot-paper2-coupling" / "source",
        ),
        (
            "agent-behavior-regression",
            root / "research" / "pilot-agent-behavior-regression" / "source",
        ),
        (
            "verifier-capture-aggregation",
            root / "research" / "pilot-verifier-capture-aggregation" / "source",
        ),
        (
            "closing-landscape",
            root / "research" / "pilot-closing-calibration-landscape" / "source",
        ),
        (
            "memory-architecture",
            root / "research" / "pilot-memory-architecture-effects" / "source",
        ),
    ]
    package_audits: list[dict[str, Any]] = []
    for name, source in package_specs:
        if not source.is_dir():
            continue
        audit = audit_arxiv_package(source)
        output = package_dir / f"{name}.json"
        write_package_audit(audit, output)
        package_audits.append(
            {
                "name": name,
                **artifact(output, root),
                "source_dir": str(source),
                "mechanical_pass": audit["mechanical_pass"],
                "blocker_count": len(audit["blockers"]),
                "warning_count": len(audit["warnings"]),
                "ready_for_upload": audit["ready_for_upload"],
            }
        )
    index = {
        "schema": "q-one-package-audit-index-v1",
        "generated_at": now(),
        "audits": package_audits,
        "notes": [
            "Mechanical packageability is not scientific readiness.",
            "No audit authorizes upload.",
        ],
    }
    (package_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    schemas = schema_check(root)
    pilots: list[dict[str, Any]] = []
    for path in project_paths:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
        validation = validations[path.name]
        plan = build_research_plan(path)
        claim_counts = Counter(
            claim.get("state")
            for claim in project.get("claims", [])
            if isinstance(claim, dict)
        )
        cleanroom_receipt = path / "reports" / "cleanroom" / "receipt.json"
        package_receipt = path / "reports" / "package" / "package-receipt.json"
        pilots.append(
            {
                "project_path": str(path.relative_to(root)),
                "paper_id": project.get("paper_id"),
                "title": project.get("title"),
                "status": project.get("status"),
                "target": project.get("target"),
                "validation": {
                    "valid": validation.get("valid"),
                    "ready": validation.get("ready"),
                    "blocked_claims": validation.get("blocked_claims", []),
                    "failed_gate_receipts": validation.get(
                        "failed_gate_receipts", []
                    ),
                },
                "claim_counts": dict(sorted(claim_counts.items())),
                "claims_total": sum(claim_counts.values()),
                "package_state": project.get("package", {}).get("state"),
                "package_blockers": project.get("package", {}).get("blockers", []),
                "plan_stages": {item["stage"]: item["state"] for item in plan["stages"]},
                "plan_actions": [item["action_id"] for item in plan["next_actions"]],
                "claim_verification": claim_results.get(path.name),
                "cleanroom_receipt": artifact(cleanroom_receipt, root)
                if cleanroom_receipt.is_file()
                else None,
                "candidate_package_receipt": artifact(package_receipt, root)
                if package_receipt.is_file()
                else None,
            }
        )
    pilot_summary = {
        "pilots": len(pilots),
        "valid_overlays": sum(1 for item in pilots if item["validation"]["valid"]),
        "ready_projects": sum(1 for item in pilots if item["validation"]["ready"]),
        "compiled_packages": sum(
            1 for item in pilots if item["package_state"] in {"compiled", "ready"}
        ),
        "candidate_packages": sum(
            1 for item in pilots if item["candidate_package_receipt"]
        ),
        "blocked_claims": sum(
            item["claim_counts"].get("blocked", 0) for item in pilots
        ),
        "inconclusive_claims": sum(
            item["claim_counts"].get("inconclusive", 0) for item in pilots
        ),
        "uploaded_papers": 0,
    }
    pilot_status = {
        "schema": "q-one-research-pilot-status-v1",
        "generated_at": now(),
        "projects": pilots,
        "summary": pilot_summary,
        "notes": [
            "No project is ready for external submission.",
            "Candidate package receipts do not authorize upload.",
        ],
    }
    pilot_path = artifact_dir / "pilot-status.json"
    write_json_atomic(pilot_path, pilot_status)

    verification_paths = [
        artifact_dir / "artifact.json",
        artifact_dir / "triage.json",
        artifact_dir / "triage.md",
        artifact_dir / "triage.csv",
        artifact_dir / "pilot-status.json",
        artifact_dir / "agent-dispositions.json",
        artifact_dir / "agent-dispositions.md",
        artifact_dir / "agent-dispositions.csv",
        root / "research" / "FACTORY_STATUS.md",
        root / "docs" / "RESEARCH_FACTORY_AUTONOMOUS_ITERATION_PLAN.zh-CN.md",
        artifact_dir / "review-packets" / "index.json",
        artifact_dir / "review-packets" / "top20.md",
        package_dir / "index.json",
        *sorted(package_dir.glob("*.json")),
        *sorted((root / "research").glob("pilot-*/.gitkeep")),
    ]
    unique_paths = [path for path in dict.fromkeys(verification_paths) if path.is_file()]
    head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    status = run(["git", "status", "--short"], cwd=root).stdout
    verification = {
        "schema": "q-one-research-factory-verification-v1",
        "generated_at": now(),
        "command": (
            f"PYTHONPATH={shlex.quote(env['PYTHONPATH'])} "
            f"{shlex.quote(sys.executable)} "
            f"{shlex.quote(str(root / 'scripts' / 'research_factory_verify.py'))}"
            + (" --skip-tests" if args.skip_tests else "")
        ),
        "scope": (
            "Research Factory control plane, seventeen pilot overlays, claim ledgers, "
            "mechanical package audits, clean-room compilation and candidate archives"
        ),
        "source": {
            "workspace": str(root),
            "head": head,
            "dirty": bool(status.strip()),
        },
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "test_pythonpath": env["PYTHONPATH"],
            "cpu_count": os.cpu_count(),
        },
        "checks": {
            **(tests if isinstance(tests, dict) else {}),
            "ruff_scoped_research": {
                "result": (
                    "passed"
                    if ruff_result and ruff_result.returncode == 0
                    else "failed"
                )
            },
            "git_diff_check": {
                "result": "passed" if diff_result.returncode == 0 else "failed"
            },
            "json_schema": schemas,
            "project_validation": {
                "valid": sum(1 for item in validations.values() if item["valid"]),
                "ready": sum(1 for item in validations.values() if item["ready"]),
                "projects": len(validations),
            },
            "claim_ledgers": claim_results,
            "agent_dispositions": {
                "result": (
                    "passed"
                    if dispositions_result.returncode == 0
                    and dispositions.get("summary", {}).get("families")
                    == triage_family_count
                    and dispositions.get("summary", {})
                    .get("final_human_dispositions", {})
                    .get("unreviewed")
                    == triage_family_count
                    else "failed"
                ),
                "summary": dispositions.get("summary"),
                "artifact": (
                    artifact(dispositions_path, root)
                    if dispositions_path.is_file()
                    else None
                ),
            },
        },
        "pilots": pilot_summary,
        "artifact_hashes": [artifact(path, root) for path in unique_paths],
        "notes": [
            "Unknown readiness remains null; no aggregate quality score is produced.",
            "Compilation and packageability do not establish scientific readiness.",
            "No upload, account action or publication occurred.",
        ],
    }
    verification_path = artifact_dir / "verification.json"
    write_json_atomic(verification_path, verification)
    print(json.dumps({"checks": verification["checks"], "pilots": pilot_summary}, indent=2))
    failed = (
        tests.get("pytest", {}).get("result") == "failed"
        if isinstance(tests, dict)
        else False
    ) or (
        tests.get("unittest", {}).get("result") == "failed"
        if isinstance(tests, dict)
        else False
    ) or (ruff_result is None or ruff_result.returncode != 0) or diff_result.returncode != 0
    failed = failed or schemas["result"] != "passed"
    failed = failed or any(not item["valid"] for item in validations.values())
    failed = failed or any(
        item["result"] != "passed" for item in claim_results.values()
    )
    failed = failed or (
        verification["checks"]["agent_dispositions"]["result"] != "passed"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
