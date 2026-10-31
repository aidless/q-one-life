"""从已经验证过的本地产物生成「哈希绑定」的简历证据回执。

这个脚本只做汇总与校验：把 clean-room 回执、benchmark 结果、研究工厂验证结果、
Noise Floor 的复现与修订候选回执逐个读进来，先确认它们都处于「已通过」状态，
再为每份被引用的文件算出 SHA-256，最后写出 artifacts/resume-kit/evidence.json
与配套的 SHA256SUMS.txt。

设计边界：
- 任何一项校验不通过就抛 ValueError 直接中断，绝不写出半成品回执；
- 回执里明确列出 non_claims，避免把「工程验收」说成「外部有效性研究」。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "artifacts" / "resume-kit"

# 本地 Qwen 模型的固定身份：hybrid benchmark 必须与这个哈希/字节数对得上，
# 否则说明换了模型，benchmark 数字就不再可比。
MODEL_SHA256 = "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"
MODEL_BYTES = 639_446_688


def read_json(path: Path) -> dict:
    """读取一个 JSON 文件，并确认顶层是对象（而不是数组或标量）。"""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    """分块计算文件哈希，避免把大文件（例如 PDF、模型）整个读进内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(pattern: str, path: Path) -> int:
    """从日志里按正则取出第一个捕获组并转成整数；取不到就报错。"""
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"could not parse {pattern!r} from {path}")
    return int(match.group(1))


def benchmark_summary(value: dict, expected_mode: str) -> dict:
    """校验一份 benchmark 结果，并抽出要写进回执的字段。

    校验项包括：schema 名、mode、任务数固定为 6、四个完成度字段都等于任务数、
    provider 归属正确；hybrid 模式还要比对模型哈希与字节数。
    """
    if value.get("schema") != "q-one-resume-benchmark-result-v1":
        raise ValueError(f"{expected_mode} benchmark has an unexpected schema")
    if value.get("mode") != expected_mode:
        raise ValueError(f"expected mode {expected_mode}, got {value.get('mode')}")
    if value.get("task_count") != 6:
        raise ValueError("benchmark task count changed without updating this receipt")

    for field in ("completed", "valid_goal_matches", "trace_bound", "actionable"):
        if value.get(field) != value.get("task_count"):
            raise ValueError(f"{expected_mode} benchmark field {field} is incomplete")

    # rules 模式由规则引擎产出，其余模式都是本地模型产出。
    expected_provider = "local"
    if expected_mode == "rules":
        expected_provider = "rules"
    if value.get("provider_counts") != {expected_provider: value.get("task_count")}:
        raise ValueError(f"{expected_mode} benchmark provider attribution is invalid")

    # hybrid 模式一旦换了模型就不再可比，所以把模型身份钉死。
    if expected_mode == "hybrid-local":
        runtime = value.get("runtime", {})
        if runtime.get("model_sha256") != MODEL_SHA256:
            raise ValueError("hybrid benchmark model hash is not the pinned Qwen model")
        if runtime.get("model_bytes") != MODEL_BYTES:
            raise ValueError("hybrid benchmark model byte count is not pinned")

    picked: dict = {}
    for key in (
        "mode",
        "task_count",
        "completed",
        "valid_goal_matches",
        "trace_bound",
        "actionable",
        "average_latency_ms",
        "maximum_latency_ms",
        "electron_working_set_kb",
        "electron_cpu_percent",
        "provider_counts",
        "runtime",
    ):
        picked[key] = value[key]
    return picked


def main() -> None:
    """汇总全部已通过的回执，生成 evidence.json 与 SHA256SUMS.txt。"""
    cleanroom = read_json(KIT / "cleanroom-receipt.json")
    rules_raw = read_json(KIT / "benchmark" / "rules.json")
    hybrid_raw = read_json(KIT / "benchmark" / "hybrid-local.json")

    research_verification_path = (
        ROOT / "artifacts" / "research-factory" / "v2" / "verification.json"
    )
    research_status_path = (
        ROOT / "artifacts" / "research-factory" / "v2" / "pilot-status.json"
    )
    research_verification = read_json(research_verification_path)
    research_status = read_json(research_status_path)

    counterexample = read_json(
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "results"
        / "reproduction.json"
    )
    r3_root = (
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
    )
    r3_manifest = read_json(r3_root / "revision-manifest.json")
    r3_cleanroom = read_json(r3_root / "reports" / "cleanroom" / "receipt.json")
    r3_gates = read_json(r3_root / "reports" / "candidate-gates-summary.json")

    rules = benchmark_summary(rules_raw, "rules")
    hybrid = benchmark_summary(hybrid_raw, "hybrid-local")

    # 一、clean-room 必须是通过状态，且跑过严格的 Electron 端到端。
    if cleanroom.get("schema") != "q-one-cleanroom-check-v1":
        raise ValueError("clean-room receipt schema is invalid")
    if cleanroom.get("result") != "passed" or not cleanroom.get("strict_electron_e2e"):
        raise ValueError("clean-room strict E2E did not pass")

    # 二、研究工厂的每一项检查都必须是 passed。
    research_checks = research_verification.get("checks", {})
    for check in (
        "pytest",
        "unittest",
        "ruff_scoped_research",
        "git_diff_check",
        "json_schema",
    ):
        if research_checks.get(check, {}).get("result") != "passed":
            raise ValueError(f"research verification check did not pass: {check}")

    # 三、Noise Floor 的覆盖层必须存在于 pilot 列表里且通过校验。
    noise_floor = None
    for project in research_status.get("projects", []):
        if project.get("project_path") == "research/pilot-bench-noise-floor":
            noise_floor = project
            break
    if noise_floor is None or not noise_floor.get("validation", {}).get("valid"):
        raise ValueError("Noise Floor research overlay did not validate")

    # 四、反例必须真的被复现（逐字节一致才算）。
    if counterexample.get("schema") != "q-one-experiment-reproduction-v1":
        raise ValueError("producer-baseline counterexample was not reproduced")
    if counterexample.get("status") != "reproduced":
        raise ValueError("producer-baseline counterexample was not reproduced")
    if not counterexample.get("byte_identical"):
        raise ValueError("producer-baseline counterexample was not reproduced")

    # 五、R3 候选清单里的两个哈希必须与磁盘上的实际文件对得上。
    if r3_manifest.get("schema") != "q-one-revision-candidate-v1":
        raise ValueError("R3 candidate manifest is invalid")
    if r3_manifest.get("status") != "candidate":
        raise ValueError("R3 candidate manifest is invalid")
    if r3_manifest.get("candidate_source", {}).get("sha256") != sha256_file(
        r3_root / "source" / "main.tex"
    ):
        raise ValueError("R3 candidate manifest is invalid")
    if r3_manifest.get("review_request", {}).get("sha256") != sha256_file(
        r3_root / "REVIEW_REQUEST_R3.md"
    ):
        raise ValueError("R3 candidate manifest is invalid")

    # 六、R3 的 clean-room 回执：页数、确定性、两次编译哈希一致。
    if r3_cleanroom.get("pdf", {}).get("pages") != 46:
        raise ValueError("R3 clean-room receipt is invalid")
    if r3_cleanroom.get("pdf", {}).get("deterministic") is not True:
        raise ValueError("R3 clean-room receipt is invalid")
    if r3_cleanroom.get("pdf", {}).get("sha256_run1") != r3_cleanroom.get("pdf", {}).get(
        "sha256_run2"
    ):
        raise ValueError("R3 clean-room receipt is invalid")

    # 七、R3 的三道门（反向覆盖、锚点普查、措辞门）数字必须逐项对上。
    reverse_coverage = r3_gates.get("reverse_coverage", {})
    anchor_census = r3_gates.get("anchor_census", {})
    verdict_word_gate = r3_gates.get("verdict_word_gate", {})
    if r3_gates.get("status") != "passed":
        raise ValueError("R3 candidate gate summary is invalid")
    if reverse_coverage.get("n_tokens") != 355:
        raise ValueError("R3 candidate gate summary is invalid")
    if reverse_coverage.get("n_bound") != 352:
        raise ValueError("R3 candidate gate summary is invalid")
    if reverse_coverage.get("n_excused") != 3:
        raise ValueError("R3 candidate gate summary is invalid")
    if reverse_coverage.get("n_unbound") != 0:
        raise ValueError("R3 candidate gate summary is invalid")
    if anchor_census.get("verdict") != "GREEN":
        raise ValueError("R3 candidate gate summary is invalid")
    if anchor_census.get("anchor_missing") != 0:
        raise ValueError("R3 candidate gate summary is invalid")
    if verdict_word_gate.get("checks") != 137:
        raise ValueError("R3 candidate gate summary is invalid")
    if verdict_word_gate.get("failures") != 0:
        raise ValueError("R3 candidate gate summary is invalid")

    # 测试数量从 clean-room 日志里现读，不写死。
    log_root = KIT / "cleanroom-logs"
    tests = {
        "pytest_passed": parse_int(r"(\d+) passed", log_root / "pytest.log"),
        "pytest_subtests_passed": parse_int(
            r"(\d+) subtests passed", log_root / "pytest.log"
        ),
        "unittest_passed": parse_int(r"Ran (\d+) tests", log_root / "unittest.log"),
        "desktop_unit_passed": parse_int(
            r"ℹ pass (\d+)", log_root / "desktop-unit.log"
        ),
        "electron_e2e_passed": parse_int(
            r"(\d+) passed", log_root / "electron-e2e.log"
        ),
    }

    task_fixture = ROOT / "desktop" / "benchmarks" / "resume-tasks.json"
    demo_root = KIT / "demo"
    artifacts = [
        KIT / "README.md",
        KIT / "cleanroom-receipt.json",
        KIT / "benchmark" / "rules.json",
        KIT / "benchmark" / "hybrid-local.json",
        task_fixture,
        ROOT / "README.md",
        ROOT / "desktop" / "README.md",
        ROOT / "desktop" / "e2e" / "resume-benchmark.spec.ts",
        ROOT / "desktop" / "e2e" / "capture-demo.spec.ts",
        ROOT / "scripts" / "build_resume_evidence.py",
        ROOT / "scripts" / "cleanroom-check.sh",
        ROOT / "scripts" / "research_factory_verify.py",
        ROOT / "src" / "qone_life" / "research_factory" / "__init__.py",
        ROOT / "tests" / "test_research_factory.py",
        ROOT / "tests" / "test_research_experiment.py",
        research_verification_path,
        research_status_path,
        ROOT / "research" / "FACTORY_STATUS.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "CLAIM_LEDGER.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "evidence"
        / "source-lineage.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "preregistration.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "run_counterexample.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "results"
        / "run-1.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "results"
        / "reproduction.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "producer-baseline-counterexample"
        / "results"
        / "REPORT.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "preregistration.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "run_estimand_split.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "results"
        / "run-1.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "results"
        / "run-2.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "results"
        / "native-rerun-factuality.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "bootstrap-estimand-a2"
        / "results"
        / "REPORT.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "preregistration.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "run_common_support.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "run-1.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "run-2.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "reproduction.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "REPORT.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "SHA256SUMS.txt",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "preregistration.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "run_threshold_interface.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "results"
        / "run-1.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "results"
        / "run-2.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "results"
        / "reproduction.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "results"
        / "REPORT.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "threshold-interface-a4"
        / "SHA256SUMS.txt",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "revision-manifest.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "REVISION_R1.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "main.diff",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "source"
        / "main.tex",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "package-audit.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "ledger-reverse-coverage.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "ledger-anchor-census.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "verdict-word-gate.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "cleanroom"
        / "receipt.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-28-construct-validity-r1"
        / "reports"
        / "cleanroom"
        / "main.pdf",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "revision-manifest.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "REVIEW_REQUEST_R3.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "SHA256SUMS.txt",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "REVISION_R3.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "source"
        / "main.tex",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "main.diff",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "main-vs-canonical.diff",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "evidence"
        / "README.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "evidence"
        / "paper-ledger-overlay.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "evidence"
        / "verdict-claims-overlay.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "run_candidate_gates.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "package-audit.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "cleanroom"
        / "receipt.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "ledger-reverse-coverage.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "ledger-anchor-census.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "verdict-word-gate.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-support-threshold-r3"
        / "reports"
        / "candidate-gates-summary.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "revision-manifest.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "SHA256SUMS.txt",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "REVISION_R2.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "source"
        / "main.tex",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "main.diff",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "main-vs-canonical.diff",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "package-audit.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "ledger-reverse-coverage.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "ledger-anchor-census.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "verdict-word-gate.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "cleanroom"
        / "receipt.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "revisions"
        / "2026-10-29-estimand-split-r2"
        / "reports"
        / "cleanroom"
        / "main.pdf",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "preregistration.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "run_common_support.py",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "run-1.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "run-2.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "reproduction.json",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "results"
        / "REPORT.md",
        ROOT
        / "research"
        / "pilot-bench-noise-floor"
        / "experiments"
        / "kfold-common-support-a3"
        / "SHA256SUMS.txt",
        ROOT / "docs" / "career" / "QONE_RESUME_PACK.zh-CN.md",
        ROOT / "docs" / "demo" / "QONE_3_MINUTE_DEMO.zh-CN.md",
        ROOT
        / "docs"
        / "blog"
        / "2026-10-28-why-local-agents-need-evidence-gates.zh-CN.md",
        ROOT
        / "docs"
        / "images"
        / "qone-evidence-runtime-architecture.svg",
        ROOT
        / "docs"
        / "images"
        / "qone-evidence-runtime-architecture.png",
        *sorted(path for path in log_root.iterdir() if path.is_file()),
        *sorted(demo_root.glob("*.png")),
    ]

    # 为每份被引用的文件记录相对路径、字节数与哈希。
    artifact_rows = []
    for path in artifacts:
        artifact_rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    receipt = {
        "schema": "q-one-resume-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "Q-One",
        "positioning": (
            "Local-first, evidence-auditable personal decision agent"
        ),
        "cleanroom": {
            "source_manifest_sha256": cleanroom["source_manifest_sha256"],
            "source_manifest_scope": cleanroom.get("source_manifest_scope"),
            "started_at": cleanroom["started_at"],
            "finished_at": cleanroom["finished_at"],
            "strict_electron_e2e": cleanroom["strict_electron_e2e"],
            "pinned_sources": cleanroom["pinned_sources"],
            "documentation_and_evidence_excluded": cleanroom.get(
                "documentation_and_evidence_excluded", []
            ),
        },
        "tests": tests,
        "research_factory": {
            "verification_generated_at": research_verification.get("generated_at"),
            "verification_command": research_verification.get("command"),
            "pytest": research_checks.get("pytest"),
            "unittest": research_checks.get("unittest"),
            "project_validation": research_checks.get("project_validation"),
            "claim_ledger": noise_floor.get("claim_verification"),
            "noise_floor_claim_counts": noise_floor.get("claim_counts"),
            "noise_floor_validation": noise_floor.get("validation"),
            "counterexample": {
                "experiment_id": counterexample.get("experiment_id"),
                "status": counterexample.get("status"),
                "byte_identical": counterexample.get("byte_identical"),
                "hypothesis_decision": counterexample.get("hypothesis_decision"),
                "accepted_attempt": counterexample.get("accepted_attempt"),
                "narrow_conclusion": counterexample.get("narrow_conclusion"),
            },
            "revision_r3": {
                "status": r3_manifest.get("status"),
                "source_sha256": r3_manifest["candidate_source"]["sha256"],
                "manifest_sha256": sha256_file(
                    r3_root / "revision-manifest.json"
                ),
                "review_request_sha256": sha256_file(
                    r3_root / "REVIEW_REQUEST_R3.md"
                ),
                "checksum_inventory_sha256": sha256_file(
                    r3_root / "SHA256SUMS.txt"
                ),
                "pages": r3_cleanroom["pdf"]["pages"],
                "deterministic": r3_cleanroom["pdf"]["deterministic"],
                "reverse_coverage": r3_gates["reverse_coverage"],
                "anchor_census": r3_gates["anchor_census"],
                "verdict_word_gate": r3_gates["verdict_word_gate"],
            },
            "cleanroom_note": (
                "The strict Electron clean-room receipt is a separate earlier "
                "desktop/runtime run; research-factory verification is bound to "
                "the current research source and tests."
            ),
        },
        "benchmark": {
            "qualification": rules_raw["qualification"],
            "task_fixture_sha256": sha256_file(task_fixture),
            "rules": rules,
            "hybrid_local": hybrid,
        },
        "release_scope": {
            "public_release": False,
            "signed": False,
            "three_platform_clean_machine_validation": False,
            "arxiv_publication": False,
        },
        "non_claims": [
            "The benchmark is a six-task local engineering acceptance check.",
            "It is not an external validity study, user study, or benefit claim.",
            "The working SQLite database is not end-to-end encrypted.",
            "The current desktop artifacts are unsigned internal builds.",
            "No paper is publication-ready or uploaded.",
            "The producer-baseline counterexample is a synthetic logical witness, not an external leaderboard study.",
            "Noise Floor still has blocked source-identity and scientific-review claims; it is not arXiv-ready.",
            "R3 is an internal revision candidate; its compile and gate receipts do not establish scientific readiness or publication.",
        ],
        "artifacts": artifact_rows,
    }
    output = KIT / "evidence.json"
    output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # 校验和清单逐行列出每个产物，最后一行是 evidence.json 自己的哈希。
    sum_lines = []
    for row in artifact_rows:
        sum_lines.append(f"{row['sha256']}  {row['path']}")
    output_path = output.relative_to(ROOT).as_posix()
    sum_lines.append(f"{sha256_file(output)}  {output_path}")

    sums = KIT / "SHA256SUMS.txt"
    sums.write_text("\n".join(sum_lines) + "\n", encoding="utf-8")

    print(f"QONE_RESUME_EVIDENCE={output}")
    print(f"QONE_RESUME_EVIDENCE_SHA256={sha256_file(output)}")


if __name__ == "__main__":
    main()
