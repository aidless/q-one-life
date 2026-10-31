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
    """Rank the next production work by transparent signals.

    The returned priority is an orchestration order, not a scientific-quality
    score. The source portfolio's human disposition is copied unchanged.
    """

    timestamp = generated_at or _now()
    generated = _parse_timestamp(timestamp) or datetime.now(timezone.utc)
    family_by_project = {
        family.get("canonical_project_id"): family
        for family in portfolio.get("families", [])
        if family.get("canonical_project_id")
    }
    record_by_project = {
        record.get("project_id"): record
        for record in [*portfolio.get("projects", []), *portfolio.get("candidates", [])]
        if isinstance(record, dict) and record.get("project_id")
    }
    records: list[dict[str, Any]] = []
    for project in portfolio.get("projects", []):
        family = family_by_project.get(project.get("project_id"), {})
        variant_count = max(0, len(family.get("members", [])) - 1)
        pilot_matches = _matched_pilots(project, pilots)
        pilot = pilot_matches[0] if pilot_matches else None
        overlay = record_by_project.get(project.get("metadata_project_id"))
        files = _merged_file_signals(
            project.get("files", {}),
            overlay.get("files") if overlay else None,
        )
        factors: list[dict[str, Any]] = []

        if pilot is not None:
            factors.append(
                {
                    "code": "PINNED_PILOT",
                    "points": 200,
                    "observed": (
                        f"Matched pilot {pilot['id']} at phase {pilot.get('phase', 'P0')}."
                    ),
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
                    "observed": (
                        f"{variant_count} extra normalized-title source version(s) require "
                        "review."
                    ),
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

    priority_counts = Counter(record["priority_band"] for record in records)
    suggestion_counts = Counter(record["suggested_disposition"] for record in records)
    action_counts = Counter(record["suggested_next_action"] for record in records)
    pilot_ids = {
        pilot_id
        for record in records
        for pilot_id in record.get("pilot_ids", [])
    }
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
        (
            "- Suggested dispositions: "
            f"`{json.dumps(summary['suggested_dispositions'], sort_keys=True)}`"
        ),
        f"- Global readiness score: `{summary['global_readiness_score']}`",
        "",
        "## Queue",
        "",
        "| Band | Priority | Pilot(s) | Suggested | Next action | Title |",
        "|---|---:|---|---|---|---|",
    ]
    for project in report["projects"]:
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
    _write_json(output, report)
    if markdown is not None:
        target = Path(markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_markdown(report), encoding="utf-8")
    if csv_path is not None:
        target = Path(csv_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_csv(report), encoding="utf-8")
