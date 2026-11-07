"""本机个人观察数据与评审报告的命令行入口。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

from .adversarial_review import AdversarialError, AdversarialReview
from .cloud_executor import CloudExecutionError, CloudExecutor
from .measurement import MeasurementError, MeasurementStore
from .model_gateway import DEFAULT_URL as DEFAULT_MODEL_URL
from .model_gateway import make_model_call
from .models import LifeValidationError, Observation, load_metric_specs, utc_now
from .rebuttal_loop import RebuttalError, build_rebuttal_plan, write_rebuttal_plan
from .redaction import export_observations
from .research_factory.autopilot import AutopilotError
from .research_factory.code_lab import CodeLabError, execute_code, generate_code, run_hidden_tests
from .research_factory.project_lab import (
    build_project,
    generate_project,
    generate_project_receipt_hash,
    package_project,
    parse_project,
    verify_project,
)
from .research_factory.direction_diversity import DiversityError
from .research_factory.environment_manifest import EnvironmentError
from .research_factory.meta_review import MetaReviewError
from .research_factory.outcome_predictor import PredictorError
from .research_factory.research_integrity import IntegrityError
from .research_factory.review_rubric import ReviewRubricError
from .research_factory.rubric_calibration import CalibrationError
from .research_factory.rubric_types import TYPE_RUBRICS, TypeRubricError
from .research_factory.writer import WriterError
from .research_production import ProductionError, ResearchProduction
from .review import build_review
from .scoring import score_observations
from .store import LifeStore, StoreError


def _store(args: argparse.Namespace) -> LifeStore:
    """根据 --data-dir 打开（或创建）事件存储。"""
    root = Path(args.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return LifeStore(root / "events.jsonl")


def _load_json(path: str) -> Any:
    """读取一个 JSON 文件。"""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _report(args: argparse.Namespace) -> dict[str, Any]:
    """按给定指标定义对当前存储的观察数据打分。"""
    specs = load_metric_specs(_load_json(args.spec_file))
    return score_observations(_store(args).observations(), specs)


def cmd_init(args: argparse.Namespace) -> int:
    """初始化本地存储并打印事件数。"""
    store = _store(args)
    print(f"initialized {store.path} ({store.verify()} events)")
    return 0


def cmd_add_observation(args: argparse.Namespace) -> int:
    """新增一条有上下界的个人观察，并打印其 id。"""
    observation = Observation.from_payload(
        {
            "domain": args.domain,
            "metric": args.metric,
            "value": args.value,
            "minimum": args.minimum,
            "maximum": args.maximum,
            "observed_at": args.observed_at or utc_now(),
            "source": args.source,
            "note": args.note,
            "decision_id": args.decision_id,
        }
    )
    event = _store(args).record_observation(observation)
    print(event["payload"]["observation_id"])
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """打印维度向量得分。"""
    report = _report(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_iterate(args: argparse.Namespace) -> int:
    """打印逐日维度得分、环比变化与趋势。"""
    from .iteration import daily_iteration

    specs = load_metric_specs(_load_json(args.spec_file))
    report = daily_iteration(_store(args).observations(), specs, window_days=args.window_days)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    """打印每个领域可执行的下一步建议。"""
    from .suggestion import suggest_improvements

    specs = load_metric_specs(_load_json(args.spec_file))
    report = suggest_improvements(_store(args).observations(), specs, threshold=args.threshold)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """打印评审提示与缺失项。"""
    print(json.dumps(build_review(_report(args)), ensure_ascii=False, indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """导出观察数据（默认脱敏）。"""
    payload = export_observations(_store(args).observations(), redacted=args.redacted)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """校验本地哈希链并打印事件数。"""
    print(f"verified {_store(args).verify()} events")
    return 0


def cmd_serve(args):
    """启动本机 Web 工作台。"""
    import uvicorn

    from .web import create_app
    uvicorn.run(create_app(args.home), host=args.host, port=args.port, workers=1)
    return 0


def cmd_sidecar(args):
    """启动桌面 sidecar 进程。"""
    from .sidecar import main as sidecar_main
    return sidecar_main(["--data-dir", args.data_dir])


def cmd_system_import(args):
    """导入个人状态、目标、资源与学习记录。"""
    from .repository import Repository
    from .system import SystemService

    directory = Path(args.home or os.environ.get("QONE_HOME", Path.home() / ".local/share/q-one"))
    service = SystemService(Repository(directory))
    result = service.save(_load_json(args.file), args.parent_revision)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_system_inspect(args):
    """比较方案，或按历史时间点回放预测。"""
    from .repository import Repository, now
    from .system import SystemService

    directory = Path(args.home or os.environ.get("QONE_HOME", Path.home() / ".local/share/q-one"))
    service = SystemService(Repository(directory))
    if args.calibration_shadow and not args.replay:
        raise LifeValidationError("--calibration-shadow需要同时使用--replay")

    if args.replay:
        # 回放时可选择性地带上在线校准候选参数；不改变推荐与保存设置。
        if args.calibration_shadow:
            candidate = {"method": "prequential_aci", "step_size": 0.01, "window": 64, "min_samples": 10}
        else:
            candidate = None
        result = service.replay(candidate)
    else:
        result = service.evaluate(args.as_of or now(), available_minutes=args.available_minutes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_research_inventory(args):
    """只读扫描论文项目并生成去重后的组合清单。"""
    from .research import build_portfolio, write_portfolio

    config = _load_json(args.config) if args.config else {}
    roots = args.root or config.get("roots", [])
    if not roots:
        raise LifeValidationError("research-inventory requires --root or a config containing roots")
    portfolio = build_portfolio(
        roots,
        exclude_dirs=args.exclude_dir or config.get("exclude_dirs", []),
        exclude_path_fragments=(
            args.exclude_path_fragment or config.get("exclude_path_fragments", [])
        ),
        writeup_globs=args.writeup_glob or config.get("writeup_globs", []),
        max_depth=args.max_depth or config.get("max_depth", 8),
    )
    write_portfolio(
        portfolio,
        Path(args.output),
        Path(args.markdown) if args.markdown else None,
        Path(args.triage) if args.triage else None,
    )
    print(json.dumps(portfolio["summary"], ensure_ascii=False, indent=2))
    return 0


def cmd_research_validate(args):
    """验证论文项目的哈希、证据、论断与就绪状态。"""
    from .research import validate_research_project

    report = validate_research_project(args.project)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        return 1
    if args.require_ready and not report["ready"]:
        return 1
    return 0


def cmd_research_triage(args):
    """生成论文生产分流队列（不修改人工最终处置）。"""
    from .research_factory import triage_portfolio, write_triage

    portfolio = _load_json(args.portfolio)
    pilots = []
    if args.pilots:
        pilots = _load_json(args.pilots).get("pilots", [])
    report = triage_portfolio(portfolio, pilots=pilots)
    write_triage(
        report,
        args.output,
        markdown=args.markdown,
        csv_path=args.csv,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def cmd_research_scaffold(args):
    """为一个论文族创建外部研究覆盖层（不修改原稿）。"""
    from .research_factory import create_research_scaffold

    portfolio = _load_json(args.portfolio)
    result = create_research_scaffold(
        portfolio,
        family_id=args.family,
        output_dir=args.output,
        target=args.target,
        source=args.source,
        evidence_paths=args.evidence or [],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_research_plan(args):
    """生成证据门控的研究下一步计划。"""
    from .research_factory import build_research_plan, render_plan_markdown, write_plan

    plan = build_research_plan(args.project)
    if args.output:
        write_plan(plan, args.output, args.markdown)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.markdown and not args.output:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(render_plan_markdown(plan), encoding="utf-8")
    return 0


def cmd_research_package_check(args):
    """检查 LaTeX 源树能否被机械打包（不代表学术可投）。"""
    from .research_factory import audit_arxiv_package, write_package_audit

    audit = audit_arxiv_package(args.source, main_file=args.main)
    if args.output:
        write_package_audit(audit, args.output)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["mechanical_pass"] else 1


def cmd_research_native_ledger(args):
    """验证原生论断账本的源文件、字段与值。"""
    from .research_factory import audit_native_paper_ledger, write_native_ledger_audit

    audit = audit_native_paper_ledger(args.ledger, args.workspace_root)
    write_native_ledger_audit(audit, args.output, markdown=args.markdown)
    print(json.dumps(audit["counts"], ensure_ascii=False, indent=2))
    return 0 if audit["mechanically_valid"] else 1


def cmd_research_source_lineage(args):
    """从 git commit 恢复源哈希，并记录当前稿的可审计修订差异。"""
    from .research_factory import audit_git_source_lineage

    result = audit_git_source_lineage(
        args.repo,
        commit=args.commit,
        path=args.path,
        expected_sha256=args.expected_sha256,
        current_path=args.current,
        max_diff_lines=args.max_diff_lines,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "lineage_valid": result["lineage_valid"],
                "expected_sha256": result["expected_sha256"],
                "current_sha256": result["current"]["sha256"],
                "added_lines": result["diff"]["added_lines"],
                "removed_lines": result["diff"]["removed_lines"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["lineage_valid"] else 1


def parser() -> argparse.ArgumentParser:
    """构建完整的命令行参数解析器。"""
    root = argparse.ArgumentParser(prog="qone-life", description="Q-One local life layer")
    root.add_argument(
        "--data-dir",
        default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"),
        help="directory containing events.jsonl (default: .life-data)",
    )
    commands = root.add_subparsers(dest="command", required=True)

    command = commands.add_parser('system-import',help='导入个人状态、目标、资源及学习记录')
    command.add_argument('--file',required=True)
    command.add_argument('--home')
    command.add_argument('--parent-revision',default=None,help='更新时填写当前版本ID，首次留空')
    command.set_defaults(handler=cmd_system_import)

    command = commands.add_parser('system-inspect',help='比较方案或按历史时间回放预测')
    command.add_argument('--home')
    command.add_argument('--as-of')
    command.add_argument('--available-minutes',type=int,default=90)
    command.add_argument('--replay',action='store_true')
    command.add_argument('--calibration-shadow',action='store_true',help='对照在线校准候选；不改变推荐或保存设置')
    command.set_defaults(handler=cmd_system_inspect)

    command = commands.add_parser("serve", help="启动中文个人工作台（仅本机）")
    command.add_argument("--home", default=os.environ.get("QONE_HOME"), help="个人数据目录")
    command.add_argument("--host", choices=["127.0.0.1", "localhost", "::1"], default="127.0.0.1")
    command.add_argument("--port", type=int, default=8765)
    command.set_defaults(handler=cmd_serve)

    command = commands.add_parser("sidecar", help="启动桌面 sidecar")
    command.add_argument("--data-dir", required=True)
    command.set_defaults(handler=cmd_sidecar)

    command = commands.add_parser(
        "research-inventory",
        help="只读扫描论文项目并生成去重后的组合清单",
    )
    command.add_argument("--config", help="包含 roots、排除规则和 writeup_globs 的 JSON")
    command.add_argument("--root", action="append", help="扫描根目录，可重复")
    command.add_argument("--exclude-dir", action="append")
    command.add_argument("--exclude-path-fragment", action="append")
    command.add_argument("--writeup-glob", action="append")
    command.add_argument("--max-depth", type=int)
    command.add_argument("--output", required=True, help="组合清单 JSON")
    command.add_argument("--markdown", help="人类可读摘要 Markdown")
    command.add_argument("--triage", help="供人工分流填写的 CSV")
    command.set_defaults(handler=cmd_research_inventory)

    command = commands.add_parser(
        "research-validate",
        help="验证论文项目的哈希、证据、论断和就绪状态",
    )
    command.add_argument("--project", required=True)
    command.add_argument("--require-ready", action="store_true")
    command.set_defaults(handler=cmd_research_validate)

    command = commands.add_parser(
        "research-triage",
        help="按可解释信号生成论文生产队列；不修改人工最终处置",
    )
    command.add_argument("--portfolio", required=True)
    command.add_argument("--pilots")
    command.add_argument("--output", required=True)
    command.add_argument("--markdown")
    command.add_argument("--csv")
    command.set_defaults(handler=cmd_research_triage)

    command = commands.add_parser(
        "research-scaffold",
        help="为一个论文族创建不修改原稿的外部研究覆盖层",
    )
    command.add_argument("--portfolio", required=True)
    command.add_argument("--family", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--target", default="arxiv")
    command.add_argument("--source", help="显式选择源稿；默认使用组合中的规范稿")
    command.add_argument("--evidence", action="append")
    command.set_defaults(handler=cmd_research_scaffold)

    command = commands.add_parser(
        "research-plan",
        help="生成证据门控制的研究下一步计划",
    )
    command.add_argument("--project", required=True)
    command.add_argument("--output")
    command.add_argument("--markdown")
    command.set_defaults(handler=cmd_research_plan)

    command = commands.add_parser(
        "research-package-check",
        help="检查 LaTeX 源树是否能被机械打包；不等于学术可投",
    )
    command.add_argument("--source", required=True)
    command.add_argument("--main")
    command.add_argument("--output")
    command.set_defaults(handler=cmd_research_package_check)

    command = commands.add_parser(
        "research-native-ledger",
        help="验证原生 paper-ledger.json 的源文件、字段和值；不执行具名派生公式",
    )
    command.add_argument("--ledger", required=True)
    command.add_argument("--workspace-root", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--markdown")
    command.set_defaults(handler=cmd_research_native_ledger)

    command = commands.add_parser(
        "research-source-lineage",
        help="从 git commit 恢复 manifest 源哈希，并记录当前稿的可审计修订差异",
    )
    command.add_argument("--repo", required=True)
    command.add_argument("--commit", required=True)
    command.add_argument("--path", required=True)
    command.add_argument("--expected-sha256", required=True)
    command.add_argument("--current", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--max-diff-lines", type=int, default=400)
    command.set_defaults(handler=cmd_research_source_lineage)

    command = commands.add_parser("init", help="create or verify a local life store")
    command.set_defaults(handler=cmd_init)

    command = commands.add_parser("add-observation", help="record a bounded personal observation")
    command.add_argument("--domain", required=True)
    command.add_argument("--metric", required=True)
    command.add_argument("--value", type=float, required=True)
    command.add_argument("--minimum", type=float, required=True)
    command.add_argument("--maximum", type=float, required=True)
    command.add_argument("--observed-at")
    command.add_argument("--source", required=True)
    command.add_argument("--note", default="")
    command.add_argument("--decision-id")
    command.set_defaults(handler=cmd_add_observation)

    command = commands.add_parser("score", help="print a dimension-vector score")
    command.add_argument("--spec-file", required=True)
    command.set_defaults(handler=cmd_score)

    command = commands.add_parser("iterate", help="print per-day dimension scores, deltas, and trends")
    command.add_argument("--spec-file", required=True)
    command.add_argument("--window-days", type=int, default=7, help="number of days to include (default: 7)")
    command.set_defaults(handler=cmd_iterate)

    command = commands.add_parser("suggest", help="print actionable next-step suggestions per domain")
    command.add_argument("--spec-file", required=True)
    command.add_argument("--threshold", type=float, default=0.5,
                         help="suggest only metrics scoring below this (default: 0.5)")
    command.set_defaults(handler=cmd_suggest)

    command = commands.add_parser("review", help="print review prompts and missingness")
    command.add_argument("--spec-file", required=True)
    command.set_defaults(handler=cmd_review)

    command = commands.add_parser("export", help="export observations")
    command.add_argument(
        "--full", dest="redacted", action="store_false", default=True,
        help="include local notes, source strings, and decision links",
    )
    command.set_defaults(handler=cmd_export)

    command = commands.add_parser("verify", help="verify the local hash chain")
    command.set_defaults(handler=cmd_verify)

    command = commands.add_parser("measure-add", help="record a daily measurement")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.add_argument("--type", required=True, choices=["code_commit", "experiment_run", "model_review"])
    command.add_argument("--subject", required=True, help="what is being measured")
    command.add_argument("--metric", required=True, help="the metric name")
    command.add_argument("--value", required=True, help="the measured value")
    command.add_argument("--unit", required=True, help="unit of measurement")
    command.add_argument("--definition", required=True, help="what exactly this measures")
    command.add_argument("--source", required=True, help="where the value came from")
    command.set_defaults(handler=cmd_measure_add)

    command = commands.add_parser("measure-list", help="list all measurements")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.set_defaults(handler=cmd_measure_list)

    command = commands.add_parser("measure-verify", help="verify the measurement hash chain")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.set_defaults(handler=cmd_measure_verify)


    command = commands.add_parser("measure-decide", help="record a decision with options and rationale")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.add_argument("--subject", required=True)
    command.add_argument("--option", action="append", required=True)
    command.add_argument("--chosen", required=True)
    command.add_argument("--rationale", required=True)
    command.add_argument("--evidence", required=True)
    command.add_argument("--expected-outcome", required=True)
    command.add_argument("--cost", default=None, help="resource or time cost of the chosen option")
    command.add_argument("--reversibility", default=None, choices=["reversible", "partially_reversible", "irreversible"], help="how reversible the decision is")
    command.add_argument("--deadline", default=None, help="decision deadline (ISO 8601)")
    command.set_defaults(handler=cmd_measure_decide)

    command = commands.add_parser("measure-outcome", help="record the observed outcome of a decision")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.add_argument("--decision-seq", type=int, required=True)
    command.add_argument("--subject", required=True)
    command.add_argument("--observed-outcome", required=True)
    command.add_argument("--matched", action="store_true")
    command.add_argument("--latency-sec", type=int, default=None, help="seconds between decision and observed outcome")
    command.set_defaults(handler=cmd_measure_outcome)

    command = commands.add_parser("measure-stats", help="show decision hit rate and record counts")
    command.add_argument("--data-dir", default=os.environ.get("QONE_LIFE_DATA_DIR", ".life-data"))
    command.set_defaults(handler=cmd_measure_stats)

    command = commands.add_parser("research-produce", help="register a research question in the production pipeline")
    command.add_argument("--workspace", default=".")
    command.add_argument("--question", required=True)
    command.add_argument("--venue", default="arxiv")
    command.add_argument("--slug", required=True)
    command.add_argument("--cloud", action="store_true", help="attach the remote cloud executor")
    command.set_defaults(handler=cmd_research_produce)

    command = commands.add_parser("research-adversarial", help="run adversarial review rounds over a claim ledger")
    command.add_argument("--ledger", required=True)
    command.add_argument("--rounds", type=int, default=3)
    command.add_argument("--model", action="append", required=True)
    command.add_argument("--claim", action="append", help="only attack this claim id (repeatable)")
    command.add_argument("--magpie-url", default="http://127.0.0.1:3425/v1/chat/completions")
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_adversarial)

    command = commands.add_parser("research-rebuttal", help="turn adversarial objections into classified rebuttal experiments")
    command.add_argument("--attack-output", required=True, help="output directory of research-adversarial")
    command.add_argument("--output", required=True, help="path for REBUTTAL_PLAN.md")
    command.add_argument("--json", dest="as_json", action="store_true", help="print the plan as JSON instead of a short summary")
    command.add_argument("--workspace", help="optional pipeline workspace to attach the plan into")
    command.add_argument("--slug", help="pipeline slug required when --workspace is set")
    command.set_defaults(handler=cmd_research_rebuttal)

    command = commands.add_parser("research-autopilot", help="generate candidate hypotheses for a research question")
    command.add_argument("--question", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--n", type=int, default=5)
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.set_defaults(handler=cmd_research_autopilot)

    command = commands.add_parser("research-screen", help="screen candidate hypotheses with a proxy scorer")
    command.add_argument("--candidates", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--top-k", type=int, default=2)
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.set_defaults(handler=cmd_research_screen)

    command = commands.add_parser("research-review", help="score a manuscript with mechanical checks and a model rubric")
    command.add_argument("--manuscript", required=True)
    command.add_argument("--ledger", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.set_defaults(handler=cmd_research_review)

    command = commands.add_parser("research-write", help="render a LaTeX draft with numbers bound to a results receipt")
    command.add_argument("--title", required=True)
    command.add_argument("--question", required=True, help="question markdown file")
    command.add_argument("--hypothesis", required=True, help="hypothesis JSON file")
    command.add_argument("--claims", required=True, help="claim ledger markdown file")
    command.add_argument("--results", required=True, help="results JSON file")
    command.add_argument("--venue", default="arxiv")
    command.add_argument("--output", required=True, help="output .tex path")
    command.set_defaults(handler=cmd_research_write)

    command = commands.add_parser("research-decide", help="aggregate rubric, adversarial review and rebuttal into a decision")
    command.add_argument("--rubric", required=True)
    command.add_argument("--adversarial", help="adversarial summary.json")
    command.add_argument("--rebuttal", help="rebuttal plan.json")
    command.add_argument("--integrity", help="integrity report JSON")
    command.add_argument("--closure", help="rebuttal closure report JSON")
    command.add_argument("--previous-total", type=float)
    command.add_argument("--accept-threshold", type=float, default=4.0)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_decide)

    command = commands.add_parser("research-batch", help="run autopilot generation and screening over a list of questions")
    command.add_argument("--items", required=True, help="JSON list of {slug, question}")
    command.add_argument("--output-dir", required=True)
    command.add_argument("--n", type=int, default=5)
    command.add_argument("--top-k", type=int, default=2)
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.set_defaults(handler=cmd_research_batch)

    command = commands.add_parser("research-calibrate", help="check rubric negative controls and human-score alignment")
    command.add_argument("--output", required=True)
    command.add_argument("--human-records", help="JSON list of {rubric_total, human_score}")
    command.add_argument("--decision-records", help="JSON list of {rubric_total, decision}")
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.set_defaults(handler=cmd_research_calibrate)

    command = commands.add_parser("research-integrity", help="audit deterministic RIVT integrity checks")
    command.add_argument("--manuscript")
    command.add_argument("--ledger")
    command.add_argument("--results")
    command.add_argument("--bibliography")
    command.add_argument("--preregistration")
    command.add_argument("--frozen-preregistration")
    command.add_argument("--evaluator")
    command.add_argument("--evaluator-sha256")
    command.add_argument("--job")
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_integrity)

    command = commands.add_parser("research-type-rubric", help="check type-level structural requirements")
    command.add_argument("--manuscript", required=True)
    command.add_argument("--type", dest="paper_type", choices=sorted(TYPE_RUBRICS))
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_type_rubric)

    command = commands.add_parser("research-environment-check", help="validate an executable environment manifest")
    command.add_argument("--manifest", required=True)
    command.add_argument("--root", required=True)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_environment_check)

    command = commands.add_parser("research-directions", help="rank families with a direction exploration bonus")
    command.add_argument("--items", required=True, help="JSON list of {family_id, roi, direction}")
    command.add_argument("--capacity", type=int, default=5)
    command.add_argument("--bonus", type=float, default=0.15)
    command.add_argument("--open-cost", type=float, default=0.05)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_directions)

    command = commands.add_parser("research-screen-plans", help="rank plans by predicted outcome and mark must-run")
    command.add_argument("--plans", required=True, help="JSON list of {plan_id, ...}")
    command.add_argument("--predictions", required=True, help="JSON object plan_id -> {predicted:{score:..},confidence:..}")
    command.add_argument("--metric", default="score")
    command.add_argument("--top-k", type=int, default=2)
    command.add_argument("--confidence-threshold", type=float, default=0.6)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_screen_plans)

    command = commands.add_parser("research-optimize", help="rank paper families by evidence ROI")
    command.add_argument("--portfolio", required=True)
    command.add_argument("--pilots", required=True)
    command.add_argument("--capacity", type=int, default=5)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_optimize)

    command = commands.add_parser("research-code", help="generate and run bounded research code")
    command.add_argument("action", choices=["generate", "execute", "test"])
    command.add_argument("--task", help="research task for generate")
    command.add_argument("--code", help="code receipt JSON for execute/test")
    command.add_argument("--data", help="input data JSON for execute")
    command.add_argument("--execution", help="execution receipt JSON for test")
    command.add_argument("--tests", help="path::function returning the hidden test list")
    command.add_argument("--model", default="group/auto-gpt-6")
    command.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_code)
    project = commands.add_parser("research-project", help="generate and verify a multi-file research project")
    project.add_argument("action", choices=["generate", "build", "verify", "package"])
    project.add_argument("--task", help="research task for generate")
    project.add_argument("--profile", choices=["minimal", "paperbench"], default="minimal")
    project.add_argument("--attempts", type=int, default=3)
    project.add_argument("--receipt", help="project receipt JSON")
    project.add_argument("--output-dir", help="directory to materialise the project")
    project.add_argument("--paper-id", help="PaperBench paper id for package")
    project.add_argument("--verdict", help="verification receipt JSON for package")
    project.add_argument("--output", help="output receipt path")
    project.add_argument("--input", help="input data JSON for verify")
    project.add_argument("--hidden-tests", help="python source of host hidden tests")
    project.add_argument("--model", default="group/auto-gpt-6")
    project.add_argument("--magpie-url", default=DEFAULT_MODEL_URL)
    project.set_defaults(handler=cmd_research_project)

    return root



def _measurement_store(args: argparse.Namespace) -> MeasurementStore:
    """根据 --data-dir 打开（或创建）测量记录存储。"""
    root = Path(args.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return MeasurementStore(root / "measurements.jsonl")


def cmd_measure_add(args: argparse.Namespace) -> int:
    """新增一条每日测量记录。"""
    store = _measurement_store(args)
    event = store.add(args.type, args.subject, args.metric, args.value, args.unit, args.definition, args.source)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def cmd_measure_list(args: argparse.Namespace) -> int:
    """列出全部测量记录。"""
    store = _measurement_store(args)
    events = store.list_all()
    for event in events:
        payload = event.get("payload", {})
        print(f'{event["seq"]:>4}  {event["ts"]}  {event["type"]:<16}  {payload.get("subject",""):<40}  {payload.get("metric",""):<30}  {payload.get("value","")}')
    print(f"total: {len(events)} measurements")
    return 0


def cmd_measure_verify(args: argparse.Namespace) -> int:
    """校验测量记录的哈希链。"""
    store = _measurement_store(args)
    print(f"verified {store.verify()} measurements")
    return 0

def cmd_measure_decide(args: argparse.Namespace) -> int:
    """记录一次包含可选项与理由的决策。"""
    store = _measurement_store(args)
    options = [opt.strip() for opt in args.option]
    event = store.decide(args.subject, options, args.chosen, args.rationale,
                         args.evidence, args.expected_outcome,
                         cost=args.cost, reversibility=args.reversibility,
                         deadline=args.deadline)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def cmd_measure_outcome(args: argparse.Namespace) -> int:
    """记录某次决策的观察结果。"""
    store = _measurement_store(args)
    event = store.record_outcome(args.decision_seq, args.subject, args.observed_outcome,
                                 args.matched, latency_sec=args.latency_sec)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def cmd_measure_stats(args: argparse.Namespace) -> int:
    """显示决策命中率与各类记录数。"""
    store = _measurement_store(args)
    stats = {"hit_rate": store.hit_rate(), "decisions": len(store.decisions()),
             "outcomes": len(store.outcomes()), "measurements": len(store.list_all())}
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def cmd_research_produce(args: argparse.Namespace) -> int:
    """在研究生产管线中登记一个研究问题。"""
    executor = CloudExecutor() if args.cloud else None
    pipeline = ResearchProduction(args.workspace, executor=executor)
    receipt = pipeline.register_question(args.slug, Path(args.question), args.venue)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def cmd_research_adversarial(args: argparse.Namespace) -> int:
    """对论断账本运行多轮对抗式评审。"""
    review = AdversarialReview(args.magpie_url)
    receipt = review.attack(Path(args.ledger), rounds=args.rounds,
                            models=args.model, output_dir=Path(args.output),
                            claim_ids=args.claim)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def cmd_research_rebuttal(args: argparse.Namespace) -> int:
    """把对抗评审的异议分类并生成反驳实验计划（不执行实验）。"""
    plan = build_rebuttal_plan(args.attack_output)
    written = write_rebuttal_plan(plan, Path(args.output))
    attached = None
    if args.workspace:
        if not args.slug:
            print("error: --slug is required when --workspace is set", file=sys.stderr)
            return 2
        pipeline = ResearchProduction(args.workspace)
        attached = pipeline.attach_rebuttal_plan(args.slug, plan)
    if args.as_json:
        payload = {**plan, **written}
        if attached:
            payload["attached_receipt"] = attached
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"wrote {written['rebuttal_plan_path']} · "
            f"executable={plan['executable_count']} "
            f"out_of_loop={plan['out_of_loop_count']} "
            f"unclassified={plan['unclassified_count']}"
        )
        if attached:
            print(f"attached {attached['plan_path']} ({attached['receipt_sha256'][:12]})")
    return 0


def cmd_research_autopilot(args: argparse.Namespace) -> int:
    """生成候选假设并写入 JSON 回执。"""
    from .research_factory.autopilot import generate_hypotheses, write_autopilot_report

    question = Path(args.question).read_text(encoding="utf-8")
    model_call = make_model_call(url=args.magpie_url, model=args.model)
    report = generate_hypotheses(question, model_call, n=args.n)
    written = write_autopilot_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · "
        f"candidates={len(report['candidates'])} "
        f"sha256={written['sha256'][:12]}"
    )
    return 0


def cmd_research_screen(args: argparse.Namespace) -> int:
    """对候选假设做代理评分与 top-k 筛选。"""
    from .research_factory.autopilot import (
        make_hypothesis_scorer,
        screen_hypotheses,
        write_autopilot_report,
    )

    payload = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    model_call = make_model_call(url=args.magpie_url, model=args.model)
    report = screen_hypotheses(
        candidates, make_hypothesis_scorer(model_call), top_k=args.top_k
    )
    written = write_autopilot_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · "
        f"status={report['status']} selected={','.join(report['selected']) or '-'}"
    )
    return 0


def cmd_research_review(args: argparse.Namespace) -> int:
    """运行机械检查 + 模型评分，产出审稿回执。"""
    from .research_factory.review_rubric import score_manuscript, write_review_report

    model_call = make_model_call(url=args.magpie_url, model=args.model)
    report = score_manuscript(Path(args.manuscript), Path(args.ledger), model_call)
    written = write_review_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · "
        f"status={report['status']} total={report['total']}"
    )
    return 0


def cmd_research_write(args: argparse.Namespace) -> int:
    """渲染数字可追溯的 LaTeX 草稿。"""
    from .adversarial_review import parse_claims
    from .research_factory.writer import render_draft, write_draft_receipt

    question = Path(args.question).read_text(encoding="utf-8")
    hypothesis = json.loads(Path(args.hypothesis).read_text(encoding="utf-8"))
    claims = parse_claims(Path(args.claims).read_text(encoding="utf-8"))
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    report = render_draft(
        title=args.title,
        question=question,
        hypothesis=hypothesis,
        claims=claims,
        results=results,
        venue=args.venue,
    )
    written = write_draft_receipt(report, Path(args.output))
    print(
        f"wrote {written['draft_path']} · "
        f"claims={report['claim_count']} numbers={len(report['numbers_used'])}"
    )
    return 0


def cmd_research_decide(args: argparse.Namespace) -> int:
    """聚合审稿、对抗评审与反驳计划，输出继续/停止/回退。"""
    from .research_factory.meta_review import decide, write_decision

    rubric = json.loads(Path(args.rubric).read_text(encoding="utf-8"))
    adversarial = None
    if args.adversarial:
        adversarial = json.loads(Path(args.adversarial).read_text(encoding="utf-8"))
    rebuttal = None
    if args.rebuttal:
        rebuttal = json.loads(Path(args.rebuttal).read_text(encoding="utf-8"))
    integrity = None
    if args.integrity:
        integrity = json.loads(Path(args.integrity).read_text(encoding="utf-8"))
    closure = None
    if args.closure:
        closure = json.loads(Path(args.closure).read_text(encoding="utf-8"))
    report = decide(
        rubric=rubric,
        adversarial=adversarial,
        rebuttal=rebuttal,
        integrity=integrity,
        closure=closure,
        previous_total=args.previous_total,
        accept_threshold=args.accept_threshold,
    )
    written = write_decision(report, Path(args.output))
    print(f"wrote {written['path']} · decision={report['decision']}")
    for reason in report["reasons"]:
        print(f"  - {reason}")
    return 0


def cmd_research_batch(args: argparse.Namespace) -> int:
    """批量运行假设生成与筛选；单项失败不影响其他项。"""
    from .research_factory.autopilot import run_batch

    items = json.loads(Path(args.items).read_text(encoding="utf-8"))
    model_call = make_model_call(url=args.magpie_url, model=args.model)
    summary = run_batch(
        items, model_call, n=args.n, top_k=args.top_k, output_dir=args.output_dir
    )
    print(
        f"wrote {summary['summary_path']} · "
        f"ok={summary['ok']} failed={summary['failed']}"
    )
    return 0


def cmd_research_calibrate(args: argparse.Namespace) -> int:
    """运行 rubric 负样本与人工评分对齐检查。"""
    from .research_factory.rubric_calibration import calibrate, write_calibration_report

    human_records = []
    if args.human_records:
        human_records = json.loads(
            Path(args.human_records).read_text(encoding="utf-8")
        )
    decision_records = []
    if args.decision_records:
        decision_records = json.loads(
            Path(args.decision_records).read_text(encoding="utf-8")
        )
    model_call = make_model_call(url=args.magpie_url, model=args.model)
    report = calibrate(
        model_call=model_call,
        human_records=human_records,
        decision_records=decision_records,
    )
    written = write_calibration_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · status={report['status']} "
        f"negatives={report['negative_samples']['caught']}/{report['negative_samples']['count']} "
        f"human_pairs={report['human_alignment']['pairs']}"
    )
    return 0


def cmd_research_integrity(args: argparse.Namespace) -> int:
    """运行确定性科研诚信检查。"""
    from .research_factory.research_integrity import audit_integrity, write_integrity_report

    report = audit_integrity(
        manuscript=args.manuscript,
        ledger=args.ledger,
        results=args.results,
        bibliography=args.bibliography,
        preregistration=args.preregistration,
        frozen_preregistration=args.frozen_preregistration,
        evaluator=args.evaluator,
        evaluator_sha256=args.evaluator_sha256,
        job=args.job,
    )
    written = write_integrity_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · status={report['status']} "
        f"release={report['release']} violations={report['violations']} "
        f"not_assessed={report['not_assessed']}"
    )
    return 0


def cmd_research_type_rubric(args: argparse.Namespace) -> int:
    """检查论文类型的结构性要求。"""
    from .research_factory.rubric_types import evaluate_type_rubric, write_type_rubric

    report = evaluate_type_rubric(args.manuscript, paper_type=args.paper_type)
    written = write_type_rubric(report, Path(args.output))
    print(
        f"wrote {written['path']} · type={report['paper_type']} "
        f"status={report['status']} {report['passed']}/{report['total']}"
    )
    return 0


def cmd_research_environment_check(args: argparse.Namespace) -> int:
    """校验可执行环境清单。"""
    from .research_factory.environment_manifest import (
        validate_environment,
        write_environment_validation,
    )

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = validate_environment(manifest, args.root)
    written = write_environment_validation(report, Path(args.output))
    print(
        f"wrote {written['path']} · status={report['status']} "
        f"failed={','.join(report['failed']) or '-'}"
    )
    return 0


def cmd_research_directions(args: argparse.Namespace) -> int:
    """按方向多样性排序论文家族。"""
    from .research_factory.direction_diversity import (
        rank_with_diversity,
        write_direction_allocation,
    )

    items = json.loads(Path(args.items).read_text(encoding="utf-8"))
    report = rank_with_diversity(
        items, args.capacity,
        exploration_bonus=args.bonus, open_cost=args.open_cost,
    )
    written = write_direction_allocation(report, Path(args.output))
    print(
        f"wrote {written['path']} · selected={','.join(x['family_id'] for x in report['selected'])} "
        f"directions={json.dumps(report['directions'], ensure_ascii=False)}"
    )
    return 0


def cmd_research_screen_plans(args: argparse.Namespace) -> int:
    """按预测结果排序计划，并标出必须真跑的项。"""
    from .research_factory.outcome_predictor import screen_plans, write_screen_report

    plans = json.loads(Path(args.plans).read_text(encoding="utf-8"))
    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    report = screen_plans(
        plans,
        lambda plan: predictions.get(str(plan.get("plan_id"))),
        metric=args.metric,
        top_k=args.top_k,
        confidence_threshold=args.confidence_threshold,
    )
    written = write_screen_report(report, Path(args.output))
    print(
        f"wrote {written['path']} · selected={','.join(report['selected'])} "
        f"must_run={','.join(report['must_run']) or '-'}"
    )
    return 0


def cmd_research_code(args: argparse.Namespace) -> int:
    """Generate and execute bounded research code with hidden tests."""
    if args.action == "generate":
        receipt = generate_code(
            args.task,
            lambda prompt: make_model_call(prompt, model=args.model, url=args.magpie_url),
        )
    elif args.action == "execute":
        receipt = execute_code(_load_json(args.code)["code"], _load_json(args.data))
    else:
        code_payload = _load_json(args.code)
        execution = _load_json(args.execution)
        module_path, function_name = args.tests.rsplit("::", 1)
        spec = importlib.util.spec_from_file_location("qone_hidden_tests", module_path)
        if spec is None or spec.loader is None:
            raise CodeLabError("hidden tests module cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tests = getattr(module, function_name)
        if not isinstance(tests, list):
            raise CodeLabError("tests must be a JSON list")
        receipt = run_hidden_tests(code_payload["code"], execution, tests)
    Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def cmd_research_project(args: argparse.Namespace) -> int:
    """Generate, materialise or verify a bounded multi-file research project."""
    if args.action == "generate":
        receipt = generate_project(
            args.task or "",
            make_model_call(model=args.model, url=args.magpie_url),
            profile=args.profile,
            attempts=args.attempts,
        )
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    elif args.action == "build":
        payload = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(files, dict):
            raise CodeLabError("project receipt must contain files")
        for path, content in files.items():
            if not isinstance(path, str) or not isinstance(content, str):
                raise CodeLabError("project receipt files must be string pairs")
        build_project(files, Path(args.output_dir))
        receipt = {"schema": "q-one-project-lab-build-v1", "output_dir": args.output_dir,
                   "files": sorted(files)}
    elif args.action == "package":
        payload = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(files, dict):
            raise CodeLabError("project receipt must contain files")
        hidden_hash = ""
        verdict_hash = ""
        if args.hidden_tests:
            hidden_hash = hashlib.sha256(Path(args.hidden_tests).read_bytes()).hexdigest()
        if args.verdict:
            verdict_hash = generate_project_receipt_hash(
                json.loads(Path(args.verdict).read_text(encoding="utf-8"))
            )
        if not args.output_dir or not args.paper_id:
            raise CodeLabError("package requires --output-dir and --paper-id")
        receipt = package_project(
            files,
            output_dir=Path(args.output_dir),
            paper_id=args.paper_id,
            task=payload.get("task", ""),
            manifest_sha256=payload.get("manifest_sha256", ""),
            hidden_tests_sha256=hidden_hash,
            verification_sha256=verdict_hash,
        )
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    else:
        payload = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(files, dict):
            raise CodeLabError("project receipt must contain files")
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        hidden = Path(args.hidden_tests).read_text(encoding="utf-8")
        receipt = verify_project(files, input_data=data, hidden_tests=hidden)
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}, ensure_ascii=False, indent=2))
    return 0


def cmd_research_optimize(args: argparse.Namespace) -> int:
    """按证据 ROI 对论文族排序。"""
    from .research_factory import optimize_portfolio
    portfolio = json.loads(Path(args.portfolio).read_text(encoding="utf-8"))
    pilots = json.loads(Path(args.pilots).read_text(encoding="utf-8")).get("pilots", [])
    allocation = optimize_portfolio(portfolio, pilots, capacity=args.capacity)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(allocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(allocation['ranked'])} families)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """解析参数并分派到对应子命令；捕获已知异常后返回退出码 2。"""
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except (LifeValidationError, StoreError, MeasurementError, ProductionError, AdversarialError, RebuttalError, AutopilotError, CodeLabError, ReviewRubricError, WriterError, MetaReviewError, CalibrationError, IntegrityError, TypeRubricError, EnvironmentError, DiversityError, PredictorError, CloudExecutionError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
