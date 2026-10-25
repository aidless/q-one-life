"""CLI for local personal observations and review reports."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .models import LifeValidationError, Observation, load_metric_specs, utc_now
from .redaction import export_observations
from .review import build_review
from .scoring import score_observations
from .store import LifeStore, StoreError


def _store(args: argparse.Namespace) -> LifeStore:
    root = Path(args.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return LifeStore(root / "events.jsonl")


def _load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _report(args: argparse.Namespace) -> dict[str, Any]:
    specs = load_metric_specs(_load_json(args.spec_file))
    return score_observations(_store(args).observations(), specs)


def cmd_init(args: argparse.Namespace) -> int:
    store = _store(args)
    print(f"initialized {store.path} ({store.verify()} events)")
    return 0


def cmd_add_observation(args: argparse.Namespace) -> int:
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
    report = _report(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    print(json.dumps(build_review(_report(args)), ensure_ascii=False, indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    payload = export_observations(_store(args).observations(), redacted=args.redacted)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    print(f"verified {_store(args).verify()} events")
    return 0


def cmd_serve(args):
    import uvicorn
    from .web import create_app
    uvicorn.run(create_app(args.home), host=args.host, port=args.port, workers=1)
    return 0


def cmd_system_import(args):
    from .repository import Repository
    from .system import SystemService
    directory=Path(args.home or os.environ.get('QONE_HOME',Path.home()/'.local/share/q-one'))
    service=SystemService(Repository(directory))
    result=service.save(_load_json(args.file),args.parent_revision)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


def cmd_system_inspect(args):
    from .repository import Repository
    from .system import SystemService
    from .repository import now
    directory=Path(args.home or os.environ.get('QONE_HOME',Path.home()/'.local/share/q-one'))
    service=SystemService(Repository(directory))
    if args.calibration_shadow and not args.replay:
        raise LifeValidationError('--calibration-shadow需要同时使用--replay')
    if args.replay:
        candidate={'method':'prequential_aci','step_size':0.01,'window':64,'min_samples':10} if args.calibration_shadow else None
        result=service.replay(candidate)
    else:
        result=service.evaluate(args.as_of or now(),available_minutes=args.available_minutes)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
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
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except (LifeValidationError, StoreError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
