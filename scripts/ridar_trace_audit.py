"""Audit RIDAR RIV-Gold traces against the labels and our implemented checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RIVT = {
    "novelty_gaming": "NG",
    "novelty_verification_evasion": "NVE",
    "citation_fabrication": "CF",
    "citation_misrepresentation": "CM",
    "resource_constraint_violation": "CV",
    "result_fabrication": "RF",
    "selective_reporting": "SR",
    "experiment_design_gaming": "EDG",
    "outcome_dependent_design_change": "ODDC",
    "exploit_test_cases": "TCE",
    "evaluator_gaming": "EG",
    "evaluator_tampering": "ET",
    "scientific_reporting_manipulation": "SRM",
    "contribution_inflation": "CI",
}

# research_integrity.py implements these six at the artifact level
# (manuscript / claim ledger / preregistration / job / evaluator file).
IMPLEMENTED_ARTIFACT = {"CF", "CV", "RF", "SR", "ODDC", "ET"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    annotations = [json.loads(line) for line in
                   (args.root / "raw/ridar-hf/riv-gold/annotations.jsonl").read_text().splitlines()
                   if line.strip()]
    traces = {}
    for path in sorted((args.root / "raw/ridar-full").rglob("trace.jsonl")):
        traces[path.parent.name] = path

    rows: list[dict[str, Any]] = []
    category_acts: dict[str, int] = {}
    category_spans: dict[str, int] = {}
    category_trajectories: dict[str, int] = {}
    missing = []
    for annotation in annotations:
        identifier = annotation["id"]
        path = traces.get(identifier)
        if path is None:
            missing.append(identifier)
            continue
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        categories, acts, spans, out_of_range = [], 0, 0, 0
        for name, behavior in (annotation.get("behaviors") or {}).items():
            categories.append(name)
            category_trajectories[name] = category_trajectories.get(name, 0) + 1
            for act in behavior.get("acts") or []:
                acts += 1
                category_acts[name] = category_acts.get(name, 0) + 1
                for evidence in act.get("evidence") or []:
                    spans += 1
                    category_spans[name] = category_spans.get(name, 0) + 1
                    start, end = evidence.get("start"), evidence.get("end")
                    if not isinstance(start, int) or not isinstance(end, int) \
                            or start < 1 or end < start or end > len(records):
                        out_of_range += 1
        rows.append({
            "trajectory": identifier, "records": len(records), "categories": sorted(categories),
            "acts": acts, "evidence_spans": spans, "spans_out_of_range": out_of_range,
        })

    table = []
    for name, code in RIVT.items():
        table.append({
            "category": name, "code": code,
            "trajectories": category_trajectories.get(name, 0),
            "acts": category_acts.get(name, 0),
            "evidence_spans": category_spans.get(name, 0),
            "implemented_artifact_level": code in IMPLEMENTED_ARTIFACT,
            "implemented_trace_level": False,
        })
    present = [item for item in table if item["trajectories"]]
    report = {
        "schema": "qone-ridar-trace-audit-v1",
        "generated_at": utc_now(),
        "labels": "RIV-Gold annotations.jsonl",
        "traces": "raw/ridar-full/<run>/trace.jsonl",
        "trajectory_count": len(rows),
        "unmatched_annotations": missing,
        "records_total": sum(row["records"] for row in rows),
        "acts_total": sum(row["acts"] for row in rows),
        "evidence_spans_total": sum(row["evidence_spans"] for row in rows),
        "spans_out_of_range_total": sum(row["spans_out_of_range"] for row in rows),
        "category_table": table,
        "coverage": {
            "categories_in_taxonomy": len(RIVT),
            "categories_present_in_data": len(present),
            "categories_absent": [name for name, _ in RIVT.items()
                                  if name not in {item["category"] for item in present}],
            "implemented_artifact_level": len(IMPLEMENTED_ARTIFACT),
            "implemented_trace_level": 0,
        },
        "claim_limit": (
            "The six implemented checks consume manuscripts, ledgers, preregistrations, job "
            "specs or evaluator files. None consumes agent traces, so this audit measures "
            "label structure and check scope, not detector accuracy."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "audit.json").write_text(json.dumps(report, indent=1) + "\n")

    lines = [
        "| RIVT | 代码 | 轨迹数 | acts | spans | 工件级检查 | 轨迹级检查 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for item in sorted(table, key=lambda value: (-value["trajectories"], value["code"])):
        lines.append(
            f"| {item['category']} | {item['code']} | {item['trajectories']} | {item['acts']} | "
            f"{item['evidence_spans']} | "
            f"{'是' if item['implemented_artifact_level'] else '否'} | 否 |"
        )
    (args.out / "coverage-table.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: report[key] for key in (
        "trajectory_count", "records_total", "acts_total", "evidence_spans_total",
        "spans_out_of_range_total", "coverage")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
