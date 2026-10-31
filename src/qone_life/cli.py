"""本机个人观察数据与评审报告的命令行入口。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .adversarial_review import AdversarialError, AdversarialReview
from .cloud_executor import CloudExecutionError, CloudExecutor
from .measurement import MeasurementError, MeasurementStore
from .models import LifeValidationError, Observation, load_metric_specs, utc_now
from .redaction import export_observations
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
    command.add_argument("--magpie-url", default="http://127.0.0.1:3425/v1/chat/completions")
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_adversarial)

    command = commands.add_parser("research-optimize", help="rank paper families by evidence ROI")
    command.add_argument("--portfolio", required=True)
    command.add_argument("--pilots", required=True)
    command.add_argument("--capacity", type=int, default=5)
    command.add_argument("--output", required=True)
    command.set_defaults(handler=cmd_research_optimize)

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
                            models=args.model, output_dir=Path(args.output))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
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
    except (LifeValidationError, StoreError, MeasurementError, ProductionError, AdversarialError, CloudExecutionError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
