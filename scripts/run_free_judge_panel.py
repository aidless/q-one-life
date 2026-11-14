#!/usr/bin/env python3
"""CLI for free multi-model PaperBench judge panel.

Commands:
- probe: test fixed free-model candidates on one hidden leaf, lock first 3.
- go: record an explicit per-model GO receipt (never stores keys).
- grade: grade one leaf batch only when all 3 locked models have GO.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qone_life.research_factory.free_judge_panel import (  # noqa: E402
    CANDIDATE_MODELS,
    grade_batch,
    load_config,
    probe_candidates,
    write_receipt,
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_probe(args) -> int:
    leaf = read_json(args.leaf)
    report = probe_candidates(leaf, timeout_s=args.timeout_s, retries=args.retries)
    write_json(args.output, report)
    print(json.dumps({"complete": report["complete"],
                      "locked_model_ids": report["locked_model_ids"]}))
    return 0 if report["complete"] else 3


def cmd_go(args) -> int:
    path = Path(args.go_file)
    payload = read_json(path) if path.is_file() else {"schema": "qone-free-judge-go-v1", "receipts": {}}
    payload.setdefault("schema", "qone-free-judge-go-v1")
    payload.setdefault("receipts", {})
    payload["receipts"][args.model_id] = {
        "go": True,
        "batch": args.batch,
        "budget": args.budget,
        "official": False,
        "note": "explicit user GO; no key value stored",
    }
    write_json(path, payload)
    print(json.dumps({"model_id": args.model_id, "go": True, "batch": args.batch}))
    return 0


def cmd_grade(args) -> int:
    config = load_config(args.config)
    leaves_payload = read_json(args.leaves)
    if isinstance(leaves_payload, dict):
        leaves = leaves_payload.get("leaves")
        if leaves is None:
            leaves = [leaves_payload]
    else:
        leaves = leaves_payload
    go_payload = read_json(args.go_file) if Path(args.go_file).is_file() else {"receipts": {}}
    receipts = go_payload.get("receipts") or {}
    receipt = grade_batch(config, leaves, go_receipts=receipts)
    write_receipt(args.output, receipt)
    print(json.dumps({"complete": receipt.complete,
                      "blocked_reasons": receipt.blocked_reasons[:3]}))
    return 0 if receipt.complete else 3


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe")
    probe.add_argument("--leaf", type=Path, required=True)
    probe.add_argument("--output", type=Path, required=True)
    probe.add_argument("--timeout-s", type=float, default=60.0)
    probe.add_argument("--retries", type=int, default=3)
    probe.set_defaults(func=cmd_probe)

    go = sub.add_parser("go")
    go.add_argument("--go-file", type=Path, required=True)
    go.add_argument("--model-id", required=True, choices=list(CANDIDATE_MODELS))
    go.add_argument("--batch", required=True)
    go.add_argument("--budget", required=True)
    go.set_defaults(func=cmd_go)

    grade = sub.add_parser("grade")
    grade.add_argument("--config", type=Path, required=True)
    grade.add_argument("--leaves", type=Path, required=True)
    grade.add_argument("--go-file", type=Path, required=True)
    grade.add_argument("--output", type=Path, required=True)
    grade.set_defaults(func=cmd_grade)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
