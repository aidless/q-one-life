#!/usr/bin/env python3
"""Generate an auditable agent-proposed disposition for every paper family."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qone_life.research import sha256_file


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _overlay_disposition(overlay: dict[str, Any] | None) -> tuple[str, str, str] | None:
    if not overlay:
        return None
    status = str(overlay.get("status") or "unknown")
    package_state = str(overlay.get("package_state") or "not-started")
    if status == "archived":
        return (
            "archive",
            "retain_merged_or_protocol_deposit",
            "An archived pilot overlay already records this family as a merged or protocol deposit; do not create a standalone package.",
        )
    if status == "blocked":
        return (
            "blocked",
            "restore_missing_raw_carriers",
            "A pilot overlay is blocked on missing or non-recomputable evidence; restore the named carriers before package work.",
        )
    if status in {"review_pending", "revision", "experiment_pending", "blocked"}:
        if package_state in {"compiled", "ready"}:
            return (
                "repair",
                "close_overlay_review_and_metadata_gates",
                "An internal candidate package exists, but scientific review, construct validity or metadata gates remain open.",
            )
        return (
            "repair",
            "execute_overlay_evidence_plan",
            "A pilot overlay exists but its evidence or package gates are not closed.",
        )
    return (
        "repair",
        "inspect_overlay_state",
        f"Overlay status `{status}` is not mapped to an automatic package disposition.",
    )


def build_agent_dispositions(
    triage: dict[str, Any],
    packets: dict[str, dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    records = triage.get("projects", [])
    family_ids = {str(record.get("family_id")) for record in records if record.get("family_id")}
    packet_ids = set(packets)
    if family_ids != packet_ids:
        missing = sorted(family_ids - packet_ids)
        extra = sorted(packet_ids - family_ids)
        raise ValueError(f"packet/family mismatch: missing={missing}, extra={extra}")

    entries: list[dict[str, Any]] = []
    for record in sorted(
        records,
        key=lambda item: (
            str(item.get("priority_band") or "P9"),
            -int(item.get("production_priority") or 0),
            str(item.get("family_id") or ""),
        ),
    ):
        family_id = str(record["family_id"])
        packet = packets[family_id]
        overlay = packet.get("overlay")
        source = packet.get("source_state", {})
        base = str(record.get("suggested_disposition") or "repair")
        override = _overlay_disposition(overlay)
        if not source.get("exists"):
            disposition = "blocked"
            next_action = "restore_canonical_source"
            reason = "No retained source exists for this family."
        elif override:
            disposition, next_action, reason = override
        elif base in {"merge", "repair", "archive", "blocked"}:
            disposition = base
            if disposition == "merge":
                next_action = "select_canonical_source_and_reconcile_variants"
                reason = str(
                    packet.get("machine_recommendation", {}).get("reason")
                    or record.get("suggestion_reason")
                    or "Multiple source versions require reconciliation."
                )
            elif disposition == "archive":
                next_action = "retain_historical_record"
                reason = str(record.get("suggestion_reason") or "Family is a historical record.")
            else:
                next_action = "run_evidence_gate_and_create_overlay"
                reason = str(
                    record.get("suggestion_reason")
                    or "Evidence and package gates require an overlay."
                )
        else:
            disposition = "repair"
            next_action = "run_evidence_gate_and_create_overlay"
            reason = "Unknown triage suggestion defaults to a bounded evidence-gated repair."

        signals = packet.get("signals", {})
        entries.append(
            {
                "family_id": family_id,
                "project_id": record.get("project_id"),
                "title": record.get("title"),
                "priority_band": record.get("priority_band"),
                "production_priority": record.get("production_priority"),
                "primary_source": record.get("primary_source"),
                "source_sha256": source.get("sha256"),
                "source_matches_catalog": source.get("matches_catalog"),
                "variant_count": signals.get("variants_to_reconcile", 0),
                "claim_ledger_present": bool(signals.get("claim_ledger")),
                "bibliography_present": bool(signals.get("bibliography")),
                "evidence_present": bool(signals.get("evidence_directory")),
                "overlay_present": overlay is not None,
                "overlay_path": overlay.get("path") if overlay else None,
                "overlay_status": overlay.get("status") if overlay else None,
                "package_state": overlay.get("package_state") if overlay else None,
                "agent_proposed_disposition": disposition,
                "agent_next_action": next_action,
                "agent_reason": reason,
                "machine_suggested_disposition": base,
                "final_human_disposition": "unreviewed",
                "human_review_required": True,
                "publication_ready": False,
                "upload_authorized": False,
                "authority": "agent-proposed, not human publication approval",
                "packet_path": f"artifacts/research-factory/v2/review-packets/{family_id}.json",
            }
        )

    counts = Counter(item["agent_proposed_disposition"] for item in entries)
    bands = Counter(str(item["priority_band"]) for item in entries)
    return {
        "schema": "q-one-agent-disposition-ledger-v1",
        "generated_at": generated_at or now(),
        "summary": {
            "families": len(entries),
            "priority_bands": dict(sorted(bands.items())),
            "agent_proposed_dispositions": dict(sorted(counts.items())),
            "final_human_dispositions": {"unreviewed": len(entries)},
            "publication_ready": 0,
            "upload_authorized": 0,
        },
        "policy": [
            "A matched pilot overlay overrides the generic triage recommendation.",
            "Archived overlays become archive; blocked overlays become blocked.",
            "Compiled overlays stay repair until independent review and metadata gates close.",
            "Unmatched merge families require canonical-source and variant reconciliation.",
            "No agent-proposed disposition changes the final human disposition.",
        ],
        "entries": entries,
        "notes": [
            "This is a disposition inventory, not a quality score.",
            "Agent-proposed dispositions are reversible and auditable.",
            "Upload, author, license and publication actions remain user gates.",
        ],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Research Factory agent disposition ledger",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "Authority: `agent-proposed, not human publication approval`.",
        "",
        "## Summary",
        "",
        f"- Families: {summary['families']}",
        f"- Priority bands: `{json.dumps(summary['priority_bands'], sort_keys=True)}`",
        f"- Agent dispositions: `{json.dumps(summary['agent_proposed_dispositions'], sort_keys=True)}`",
        f"- Final human dispositions: `{json.dumps(summary['final_human_dispositions'], sort_keys=True)}`",
        "- Publication-ready: 0",
        "- Upload-authorized: 0",
        "",
        "## Disposition matrix",
        "",
        "| Band | Agent disposition | Next action | Families |",
        "|---|---|---|---:|",
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in payload["entries"]:
        key = (str(entry["priority_band"]), str(entry["agent_proposed_disposition"]))
        grouped.setdefault(key, []).append(entry)
    for (band, disposition), items in sorted(
        grouped.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        next_actions = sorted({str(item["agent_next_action"]) for item in items})
        lines.append(
            f"| {band} | {disposition} | {', '.join(next_actions)} | {len(items)} |"
        )
    lines.extend(["", "## Family ledger", "", "| Family | Band | Disposition | Next action | Overlay |", "|---|---|---|---|---|"])
    for entry in payload["entries"]:
        lines.append(
            "| {title} | {band} | {disposition} | {action} | {overlay} |".format(
                title=str(entry["title"]).replace("|", "\\|"),
                band=entry["priority_band"],
                disposition=entry["agent_proposed_disposition"],
                action=entry["agent_next_action"],
                overlay=entry["overlay_status"] or "none",
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--triage", required=True)
    parser.add_argument("--review-packets", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    triage_path = Path(args.triage).expanduser().resolve()
    packet_dir = Path(args.review_packets).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    packets = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(packet_dir.glob("qf-*.json"))
    }
    payload = build_agent_dispositions(triage, packets)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "agent-dispositions.json"
    md_path = output_dir / "agent-dispositions.md"
    csv_path = output_dir / "agent-dispositions.csv"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    fieldnames = [
        "family_id",
        "title",
        "priority_band",
        "agent_proposed_disposition",
        "agent_next_action",
        "final_human_disposition",
        "overlay_status",
        "publication_ready",
        "upload_authorized",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in payload["entries"]:
            writer.writerow({key: entry[key] for key in fieldnames})
    print(
        json.dumps(
            {
                **payload["summary"],
                "inputs": {
                    "triage": {"path": str(triage_path), "sha256": sha256_file(triage_path)},
                    "review_packets": {
                        "path": str(packet_dir),
                        "files": len(packets),
                    },
                },
                "outputs": [
                    {"path": str(json_path), "sha256": sha256_file(json_path)},
                    {"path": str(md_path), "sha256": sha256_file(md_path)},
                    {"path": str(csv_path), "sha256": sha256_file(csv_path)},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
