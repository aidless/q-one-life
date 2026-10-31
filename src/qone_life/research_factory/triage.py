"""研究组合的分诊（triage）模块。

这里的「优先级」只是**生产排期顺序**，不是论文质量、成熟度或录用概率的评分。
最终处置（final_disposition）始终由人决定，本模块只给出建议。
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ._helpers import (
    TRIAGE_SCHEMA,
    _has_file,
    _matched_pilots,
    _merged_file_signals,
    _now,
    _parse_timestamp,
    _priority_band,
    _suggested_disposition,
    _write_json,
)


def triage_portfolio(
    portfolio: dict[str, Any],
    *,
    pilots: Sequence[dict[str, Any]] = (),
    generated_at: str | None = None,
) -> dict[str, Any]:
    """按可观测的信号为下一批生产工作排序。

    产出的优先级只是排期顺序，不代表科学质量。源组合里的人工处置会被原样保留。
    """
    timestamp = generated_at or _now()
    generated = _parse_timestamp(timestamp) or datetime.now(timezone.utc)

    # 建立两张索引：家族号 -> 家族记录；项目号 -> 项目/候选记录。
    # 用显式循环而非字典推导，方便阅读，也保证「后出现的覆盖先出现的」这一顺序语义。
    family_by_project: dict[Any, dict[str, Any]] = {}
    for family in portfolio.get("families", []):
        canonical_id = family.get("canonical_project_id")
        if canonical_id:
            family_by_project[canonical_id] = family

    record_by_project: dict[Any, dict[str, Any]] = {}
    all_records = [*portfolio.get("projects", []), *portfolio.get("candidates", [])]
    for record in all_records:
        if not isinstance(record, dict):
            continue
        project_id = record.get("project_id")
        if project_id:
            record_by_project[project_id] = record

    records: list[dict[str, Any]] = []
    for project in portfolio.get("projects", []):
        family = family_by_project.get(project.get("project_id"), {})
        # 同一规范化标题下的成员里，除规范版本外还有几个待合并的变体。
        variant_count = max(0, len(family.get("members", [])) - 1)

        pilot_matches = _matched_pilots(project, pilots)
        pilot = pilot_matches[0] if pilot_matches else None
        overlay = record_by_project.get(project.get("metadata_project_id"))
        files = _merged_file_signals(
            project.get("files", {}),
            overlay.get("files") if overlay else None,
        )

        # 每个因子都在「观测依据」里写清来源，保证排序透明、可解释。
        factors: list[dict[str, Any]] = []

        if pilot is not None:
            factors.append(
                {
                    "code": "PINNED_PILOT",
                    "points": 200,
                    "observed": f"Matched pilot {pilot['id']} at phase {pilot.get('phase', 'P0')}.",
                }
            )
        if project.get("metadata_project_id"):
            factors.append(
                {
                    "code": "QONE_OVERLAY",
                    "points": 40,
                    "observed": f"Q-One overlay metadata: {project['metadata_project_id']}.",
                }
            )
        if _has_file(files, "claim_ledgers"):
            factors.append(
                {"code": "CLAIM_LEDGER", "points": 35, "observed": "Claim ledger is present."}
            )
        if _has_file(files, "bibliographies"):
            factors.append(
                {
                    "code": "BIBLIOGRAPHY",
                    "points": 20,
                    "observed": "At least one bibliography file is present.",
                }
            )
        if _has_file(files, "pdfs"):
            factors.append(
                {"code": "COMPILED_PDF", "points": 15, "observed": "At least one PDF is present."}
            )
        if _has_file(files, "evidence_directories"):
            factors.append(
                {
                    "code": "EVIDENCE_DIRECTORY",
                    "points": 20,
                    "observed": "At least one evidence directory is present.",
                }
            )
        if str(project.get("target") or "").lower() == "arxiv":
            factors.append(
                {
                    "code": "ARXIV_TARGET",
                    "points": 15,
                    "observed": "Explicit arXiv target is recorded.",
                }
            )
        if project.get("status") not in {None, "unknown"}:
            factors.append(
                {
                    "code": "EXPLICIT_STATUS",
                    "points": 10,
                    "observed": f"Explicit status: {project['status']}.",
                }
            )
        modified = _parse_timestamp(project.get("modified_at"))
        if modified is not None and modified >= generated - timedelta(days=30):
            factors.append(
                {
                    "code": "RECENT_30D",
                    "points": 10,
                    "observed": "Canonical source changed within the last 30 days.",
                }
            )
        if variant_count:
            factors.append(
                {
                    "code": "VERSION_RECONCILIATION",
                    "points": 5,
                    "observed": f"{variant_count} extra normalized-title source version(s) require review.",
                }
            )
        if project.get("project_type") == "legacy":
            factors.append(
                {
                    "code": "LEGACY_SOURCE",
                    "points": 0,
                    "observed": "Legacy source type; no points, review still required.",
                }
            )

        score = sum(int(factor["points"]) for factor in factors)
        disposition, reason = _suggested_disposition(
            project,
            pilot=pilot,
            variant_count=variant_count,
            generated=generated,
        )

        # 依据现有结构推断下一步动作，优先级从低到高逐级判断。
        claim_ledger = _has_file(files, "claim_ledgers")
        bibliography = _has_file(files, "bibliographies")
        pdf = _has_file(files, "pdfs")
        if not project.get("target"):
            next_action = "confirm_target_and_scope"
        elif not claim_ledger:
            next_action = "create_claim_ledger"
        elif not bibliography:
            next_action = "build_bibliography"
        elif not pdf:
            next_action = "compile_manuscript"
        else:
            next_action = "run_claim_and_package_audit"

        records.append(
            {
                "family_id": project.get("family_id") or family.get("family_id"),
                "project_id": project.get("project_id"),
                "title": project.get("title"),
                "primary_source": project.get("primary_source"),
                "project_type": project.get("project_type"),
                "target": project.get("target"),
                "status": project.get("status", "unknown"),
                "final_disposition": project.get("disposition", "unreviewed"),
                "suggested_disposition": disposition,
                "suggested_next_action": next_action,
                "suggestion_reason": reason,
                "human_review_required": True,
                "pilot_ids": [item["id"] for item in pilot_matches],
                "priority_band": _priority_band(score, pilot),
                "production_priority": score,
                "priority_factors": factors,
                "observable_inputs": {
                    "claim_ledger": claim_ledger,
                    "bibliography": bibliography,
                    "compiled_pdf": pdf,
                    "evidence_directory": _has_file(files, "evidence_directories"),
                },
                "variants_to_reconcile": variant_count,
            }
        )

    # 汇总各类计数，方便在报告里一眼看清分布。
    priority_counts = Counter(record["priority_band"] for record in records)
    suggestion_counts = Counter(record["suggested_disposition"] for record in records)
    action_counts = Counter(record["suggested_next_action"] for record in records)
    pilot_ids: set[str] = set()
    for record in records:
        for pilot_id in record.get("pilot_ids", []):
            pilot_ids.add(pilot_id)

    return {
        "schema": TRIAGE_SCHEMA,
        "generated_at": timestamp,
        "source_portfolio": {
            "generated_at": portfolio.get("generated_at"),
            "canonical_projects": portfolio.get("summary", {}).get("canonical_projects"),
        },
        "definitions": {
            "production_priority": (
                "A transparent orchestration ordering based on declared workflow signals. "
                "It is not paper quality, readiness, acceptance probability, or evidence strength."
            ),
            "suggested_disposition": (
                "A machine proposal only. The source portfolio's human disposition remains "
                "authoritative until explicitly reviewed."
            ),
        },
        "summary": {
            "paper_families": len(records),
            "priority_bands": dict(sorted(priority_counts.items())),
            "suggested_dispositions": dict(sorted(suggestion_counts.items())),
            "next_actions": dict(sorted(action_counts.items())),
            "matched_pilots": sorted(pilot_ids),
            "final_dispositions_unchanged": dict(
                sorted(Counter(record["final_disposition"] for record in records).items())
            ),
            "global_readiness_score": None,
            "note": "No global readiness or quality score is produced.",
        },
        "projects": sorted(
            records,
            key=lambda item: (
                -int(item["production_priority"]),
                str(item["title"]),
                str(item["project_id"]),
            ),
        ),
    }


def render_triage_markdown(report: dict[str, Any]) -> str:
    """把分诊报告渲染成便于人读的 Markdown。"""
    summary = report["summary"]
    lines = [
        "# Q-One research triage",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "The priority below orders production work only. It is not a paper-quality or",
        "readiness score. Final disposition remains human-owned.",
        "",
        "## Summary",
        "",
        f"- Paper families: {summary['paper_families']}",
        f"- Priority bands: `{json.dumps(summary['priority_bands'], sort_keys=True)}`",
        "- Suggested dispositions: "
        f"`{json.dumps(summary['suggested_dispositions'], sort_keys=True)}`",
        f"- Global readiness score: `{summary['global_readiness_score']}`",
        "",
        "## Queue",
        "",
        "| Band | Priority | Pilot(s) | Suggested | Next action | Title |",
        "|---|---:|---|---|---|---|",
    ]
    for project in report["projects"]:
        # 标题里的竖线需要转义，否则会破坏 Markdown 表格。
        title = str(project["title"]).replace("|", "\\|")
        pilots = ", ".join(project.get("pilot_ids", [])) or "-"
        lines.append(
            f"| {project['priority_band']} | {project['production_priority']} | "
            f"{pilots} | {project['suggested_disposition']} | "
            f"{project['suggested_next_action']} | {title} |"
        )
    lines.extend(
        [
            "",
            "The JSON companion records each scoring factor and the unchanged final disposition.",
            "",
        ]
    )
    return "\n".join(lines)


def render_triage_csv(report: dict[str, Any]) -> str:
    """把分诊报告渲染成 CSV 文本。"""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "family_id",
            "title",
            "priority_band",
            "production_priority",
            "pilot_ids",
            "suggested_disposition",
            "suggested_next_action",
            "final_disposition",
            "primary_source",
        ]
    )
    for project in report["projects"]:
        writer.writerow(
            [
                project.get("family_id") or "",
                project["title"],
                project["priority_band"],
                project["production_priority"],
                ";".join(project.get("pilot_ids", [])),
                project["suggested_disposition"],
                project["suggested_next_action"],
                project["final_disposition"],
                project["primary_source"],
            ]
        )
    return output.getvalue()


def write_triage(
    report: dict[str, Any],
    output: str | Path,
    *,
    markdown: str | Path | None = None,
    csv_path: str | Path | None = None,
) -> None:
    """写出分诊报告：JSON 必写，Markdown 与 CSV 按需写出。"""
    _write_json(output, report)

    if markdown is not None:
        target = Path(markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_markdown(report), encoding="utf-8")

    if csv_path is not None:
        target = Path(csv_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_csv(report), encoding="utf-8")
