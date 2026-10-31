#!/usr/bin/env python3
"""刷新 Research Factory 的验证结果、pilot 状态与打包回执。

这个脚本是控制面的总入口：跑测试与 lint、校验 JSON schema、校验 17 个
pilot overlay、校验 claim ledger、做机械打包审计，最后把结果写成
verification.json / pilot-status.json / package-audits 索引。

边界：这里只产出「机械可验证」的证据，不代表科学可发表，也不做任何上传。
"""

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
    """返回当前 UTC 时间的 ISO 字符串（以 Z 结尾）。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """原子地写出一份回执，避免读到只写了一半的文件。

    做法：先写临时文件并 fsync，再 os.replace 覆盖目标，最后 fsync 目录项。
    这是并发/崩溃安全的关键，因此保留临时文件 + 替换的完整流程。
    """
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
        # 任何异常都要清掉临时文件，避免留下半成品。
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def run(
    command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """跑一条外部命令并捕获输出（不因非零退出码抛异常）。"""
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def artifact(path: Path, root: Path) -> dict[str, Any]:
    """把一个文件描述成 {相对路径, sha256, 字节数} 的登记项。"""
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def research_test_pythonpath(root: Path) -> str:
    """把本仓库与相邻的 q-one-core/q-one-agent 源码目录拼成 PYTHONPATH。

    为了避免在 F:\\ 这类含特殊字符的路径上直接拼接出问题，这里在临时目录里
    建一组符号链接，再把这些链接目录串成 PYTHONPATH。链接目录名带内容哈希，
    同一组源码复用同一个目录。
    """
    sources = {"qone-life-src": root / "src"}
    for sibling in ("q-one-core", "q-one-agent"):
        source = root.parent / sibling / "src"
        if source.is_dir():
            sources[f"{sibling}-src"] = source

    identity_parts = []
    for name, path in sources.items():
        identity_parts.append(f"{name}={path.resolve()}")
    identity = "\0".join(identity_parts)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    overlay = Path(tempfile.gettempdir()) / f"qone-research-test-paths-{digest}"
    overlay.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for name, source in sources.items():
        link = overlay / name
        # 已存在的链接若指向别处（源码位置变了），先删掉重建。
        if link.is_symlink() and link.resolve() != source.resolve():
            link.unlink()
        if not link.exists():
            link.symlink_to(source.resolve(), target_is_directory=True)
        paths.append(str(link))
    return os.pathsep.join(paths)


def schema_check(root: Path) -> dict[str, Any]:
    """用 jsonschema 校验关键产物；子进程里跑，避免污染当前解释器。

    注意：下面这段代码是作为字符串传给子进程的，内容必须保持原样。
    """
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
        return {
            "result": "failed",
            "error": result.stderr.strip(),
            "checked": 0,
            "errors": [],
        }
    payload = json.loads(result.stdout)
    if payload["errors"]:
        payload["result"] = "failed"
    else:
        payload["result"] = "passed"
    return payload


def claim_summary(report: Path) -> str | None:
    """从 claim ledger 校验报告里取出「## Summary: ...」那一行。"""
    if not report.is_file():
        return None
    match = re.search(
        r"^## Summary: (.*)$", report.read_text(encoding="utf-8"), re.MULTILINE
    )
    if match:
        return match.group(1)
    return None


def main() -> int:
    """跑完整个控制面校验流程，并写出三份回执。"""
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
        # 跳过测试时沿用上一次 verification.json 里记录的测试结论。
        previous = artifact_dir / "verification.json"
        if previous.is_file():
            previous_payload = json.loads(previous.read_text(encoding="utf-8"))
        else:
            previous_payload = {}
        previous_checks = previous_payload.get("checks", {})
        pytest_previous = previous_checks.get(
            "pytest", {"result": "unknown", "tests": None}
        )
        unittest_previous = previous_checks.get(
            "unittest", {"result": "unknown", "tests": None}
        )
        tests = {"pytest": pytest_previous, "unittest": unittest_previous}
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

        # 从 pytest 摘要里拆出「通过数 / 警告数 / subtests 数」三个数字。
        if pytest_match:
            pytest_tests = int(pytest_match.group(1))
            pytest_warnings = int(pytest_match.group(2) or 0)
            pytest_subtests = int(pytest_match.group(3) or 0)
        else:
            pytest_tests = None
            pytest_warnings = None
            pytest_subtests = None

        # 先假定失败，只有退出码为 0 才记为通过。
        pytest_verdict = "failed"
        if pytest_result.returncode == 0:
            pytest_verdict = "passed"

        # 摘要里没匹配到「Ran N tests」时记为 None，而不是猜一个数字。
        unittest_tests = None
        if unittest_match:
            unittest_tests = int(unittest_match.group(1))

        # 同上：默认失败，退出码 0 才记通过。
        unittest_verdict = "failed"
        if unittest_result.returncode == 0:
            unittest_verdict = "passed"

        tests = {
            "pytest": {
                "result": pytest_verdict,
                "tests": pytest_tests,
                "warnings": pytest_warnings,
                "subtests": pytest_subtests,
            },
            "unittest": {
                "result": unittest_verdict,
                "tests": unittest_tests,
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
    if dispositions_path.is_file():
        dispositions = json.loads(dispositions_path.read_text(encoding="utf-8"))
    else:
        dispositions = {}
    triage_payload = json.loads(
        (artifact_dir / "triage.json").read_text(encoding="utf-8")
    )
    triage_family_count = len(triage_payload.get("projects", []))

    ruff = shutil.which("ruff")
    ruff_result = None
    if ruff:
        ruff_result = run(
            [
                ruff,
                "check",
                "src/qone_life/research.py",
                "src/qone_life/research_factory",
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

    # claim ledger 校验脚本来自本机 skill 目录；路径不存在时下面会失败并被记录。
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
        # 校验脚本退出码为 0 才算该族的 claim ledger 通过。
        claim_verdict = "failed"
        if result.returncode == 0:
            claim_verdict = "passed"
        # 报告文件不存在时登记为 None，避免把缺失误读成通过。
        claim_report = None
        if report.is_file():
            claim_report = artifact(report, root)
        claim_results[path.name] = {
            "result": claim_verdict,
            "summary": claim_summary(report),
            "report": claim_report,
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

        # 统计 claim 各状态的数量（只统计 dict 形式的 claim）。
        claim_counts: Counter[Any] = Counter()
        for claim in project.get("claims", []):
            if isinstance(claim, dict):
                claim_counts[claim.get("state")] += 1
        claims_total = 0
        for count in claim_counts.values():
            claims_total += count

        plan_stages: dict[str, Any] = {}
        for item in plan["stages"]:
            plan_stages[item["stage"]] = item["state"]

        plan_actions: list[Any] = []
        for item in plan["next_actions"]:
            plan_actions.append(item["action_id"])

        cleanroom_receipt = path / "reports" / "cleanroom" / "receipt.json"
        package_receipt = path / "reports" / "package" / "package-receipt.json"
        if cleanroom_receipt.is_file():
            cleanroom_artifact = artifact(cleanroom_receipt, root)
        else:
            cleanroom_artifact = None
        # 候选包回执缺失时记为 None（代表「尚未产出」，不是「已通过」）。
        package_artifact = None
        if package_receipt.is_file():
            package_artifact = artifact(package_receipt, root)

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
                    "failed_gate_receipts": validation.get("failed_gate_receipts", []),
                },
                "claim_counts": dict(sorted(claim_counts.items())),
                "claims_total": claims_total,
                "package_state": project.get("package", {}).get("state"),
                "package_blockers": project.get("package", {}).get("blockers", []),
                "plan_stages": plan_stages,
                "plan_actions": plan_actions,
                "claim_verification": claim_results.get(path.name),
                "cleanroom_receipt": cleanroom_artifact,
                "candidate_package_receipt": package_artifact,
            }
        )

    # pilot 汇总：各类计数全部用显式循环累加，便于逐个读懂。
    valid_overlays = 0
    ready_projects = 0
    compiled_packages = 0
    candidate_packages = 0
    blocked_claims = 0
    inconclusive_claims = 0
    for item in pilots:
        if item["validation"]["valid"]:
            valid_overlays += 1
        if item["validation"]["ready"]:
            ready_projects += 1
        if item["package_state"] in {"compiled", "ready"}:
            compiled_packages += 1
        if item["candidate_package_receipt"]:
            candidate_packages += 1
        blocked_claims += item["claim_counts"].get("blocked", 0)
        inconclusive_claims += item["claim_counts"].get("inconclusive", 0)

    pilot_summary = {
        "pilots": len(pilots),
        "valid_overlays": valid_overlays,
        "ready_projects": ready_projects,
        "compiled_packages": compiled_packages,
        "candidate_packages": candidate_packages,
        "blocked_claims": blocked_claims,
        "inconclusive_claims": inconclusive_claims,
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
    # 去重并丢掉不存在的文件（保留首次出现的顺序）。
    unique_paths: list[Path] = []
    seen_paths: set[str] = set()
    for path in verification_paths:
        key = str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)
        if path.is_file():
            unique_paths.append(path)

    head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    status = run(["git", "status", "--short"], cwd=root).stdout

    # 三个检查项的结论先算出来，再拼进 verification。
    # ruff 未安装或退出码非 0 都算失败（fail-closed）。
    ruff_verdict = "failed"
    if ruff_result and ruff_result.returncode == 0:
        ruff_verdict = "passed"

    diff_verdict = "failed"
    if diff_result.returncode == 0:
        diff_verdict = "passed"

    dispositions_ok = False
    if dispositions_result.returncode == 0:
        dispositions_summary = dispositions.get("summary", {})
        unreviewed_count = (
            dispositions_summary.get("final_human_dispositions", {}).get("unreviewed")
        )
        if (
            dispositions_summary.get("families") == triage_family_count
            and unreviewed_count == triage_family_count
        ):
            dispositions_ok = True
    dispositions_verdict = "failed"
    if dispositions_ok:
        dispositions_verdict = "passed"

    valid_count = 0
    ready_count = 0
    for item in validations.values():
        if item["valid"]:
            valid_count += 1
        if item["ready"]:
            ready_count += 1

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
            "ruff_scoped_research": {"result": ruff_verdict},
            "git_diff_check": {"result": diff_verdict},
            "json_schema": schemas,
            "project_validation": {
                "valid": valid_count,
                "ready": ready_count,
                "projects": len(validations),
            },
            "claim_ledgers": claim_results,
            "agent_dispositions": {
                "result": dispositions_verdict,
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
    print(
        json.dumps(
            {"checks": verification["checks"], "pilots": pilot_summary}, indent=2
        )
    )

    # 汇总最终成败：任何一项检查未通过都返回 1。
    failed = False
    if isinstance(tests, dict):
        if tests.get("pytest", {}).get("result") == "failed":
            failed = True
        if tests.get("unittest", {}).get("result") == "failed":
            failed = True
    if ruff_result is None or ruff_result.returncode != 0:
        failed = True
    if diff_result.returncode != 0:
        failed = True
    if schemas["result"] != "passed":
        failed = True
    for item in validations.values():
        if not item["valid"]:
            failed = True
    for item in claim_results.values():
        if item["result"] != "passed":
            failed = True
    if verification["checks"]["agent_dispositions"]["result"] != "passed":
        failed = True

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
