#!/usr/bin/env python3
"""为每个论文族生成一份「agent 提议、但未经人工批准」的处置清单。

重要边界：这里输出的处置只是可审计的提议，不会改变 final_human_disposition，
也不代表可发表或可上传；人工审核、作者/分类/许可证等门仍由人把关。
"""

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
    """返回当前 UTC 时间的 ISO 字符串（以 Z 结尾）。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _overlay_disposition(overlay: dict[str, Any] | None) -> tuple[str, str, str] | None:
    """把 pilot overlay 的状态映射成 (处置, 下一步动作, 原因)。

    返回 None 表示该族没有 overlay，交由通用 triage 建议决定。
    """
    if not overlay:
        return None

    status = str(overlay.get("status") or "unknown")
    package_state = str(overlay.get("package_state") or "not-started")

    # 已归档：保留为合并稿或协议存档，不再单独做包。
    if status == "archived":
        return (
            "archive",
            "retain_merged_or_protocol_deposit",
            "An archived pilot overlay already records this family as a merged or protocol deposit; do not create a standalone package.",
        )

    # 被阻塞：先恢复缺失的原始载体，才谈得上打包。
    if status == "blocked":
        return (
            "blocked",
            "restore_missing_raw_carriers",
            "A pilot overlay is blocked on missing or non-recomputable evidence; restore the named carriers before package work.",
        )

    # 仍在评审/修订/待实验阶段：一律是 repair，但下一步动作取决于包状态。
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

    # 其余未知状态：只做保守的 repair，并提示需要人工看一眼。
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
    """合并 triage 记录与 review packet，产出逐族的处置账本。

    先做一次族 id 对齐校验：triage 里的族与 packet 文件必须一一对应，
    对不上就立刻报错，避免悄悄漏掉某一族。
    """
    records = triage.get("projects", [])

    family_ids: set[str] = set()
    for record in records:
        family_id = record.get("family_id")
        if family_id:
            family_ids.add(str(family_id))
    packet_ids = set(packets)

    if family_ids != packet_ids:
        missing = sorted(family_ids - packet_ids)
        extra = sorted(packet_ids - family_ids)
        raise ValueError(f"packet/family mismatch: missing={missing}, extra={extra}")

    # 排序规则：先按优先级档位，再按生产优先级倒序，最后按族 id。
    def sort_key(item: dict[str, Any]) -> tuple[str, int, str]:
        band = str(item.get("priority_band") or "P9")
        priority = -int(item.get("production_priority") or 0)
        return (band, priority, str(item.get("family_id") or ""))

    entries: list[dict[str, Any]] = []
    for record in sorted(records, key=sort_key):
        family_id = str(record["family_id"])
        packet = packets[family_id]
        overlay = packet.get("overlay")
        source = packet.get("source_state", {})
        base = str(record.get("suggested_disposition") or "repair")
        override = _overlay_disposition(overlay)

        # 处置优先级：没有源文件 → blocked；有 overlay 覆盖 → 用覆盖结论；
        # 否则沿用 triage 的机器建议；机器建议无法识别时兜底为 repair。
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

        # overlay 相关字段在没有 overlay 时统一为 None，避免下游误判。
        overlay_path = None
        overlay_status = None
        package_state = None
        if overlay:
            overlay_path = overlay.get("path")
            overlay_status = overlay.get("status")
            package_state = overlay.get("package_state")

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
                "overlay_path": overlay_path,
                "overlay_status": overlay_status,
                "package_state": package_state,
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

    # 统计各处置与各优先级档位的族数（键按字典序输出，保证结果稳定）。
    counts: Counter[str] = Counter()
    bands: Counter[str] = Counter()
    for item in entries:
        counts[item["agent_proposed_disposition"]] += 1
        bands[str(item["priority_band"])] += 1

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
    """把处置账本渲染成人类可读的 Markdown（摘要表 + 逐族表）。"""
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

    # 按 (档位, 处置) 分组，便于统计每种组合涉及多少族。
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in payload["entries"]:
        key = (str(entry["priority_band"]), str(entry["agent_proposed_disposition"]))
        grouped.setdefault(key, []).append(entry)

    def group_sort_key(item: tuple[tuple[str, str], list[dict[str, Any]]]) -> tuple[int, tuple[str, str]]:
        return (-len(item[1]), item[0])

    for (band, disposition), items in sorted(grouped.items(), key=group_sort_key):
        next_actions: set[str] = set()
        for item in items:
            next_actions.add(str(item["agent_next_action"]))
        lines.append(
            f"| {band} | {disposition} | {', '.join(sorted(next_actions))} | {len(items)} |"
        )

    lines.extend(
        [
            "",
            "## Family ledger",
            "",
            "| Family | Band | Disposition | Next action | Overlay |",
            "|---|---|---|---|---|",
        ]
    )
    for entry in payload["entries"]:
        overlay_label = entry["overlay_status"] or "none"
        lines.append(
            "| {title} | {band} | {disposition} | {action} | {overlay} |".format(
                title=str(entry["title"]).replace("|", "\\|"),
                band=entry["priority_band"],
                disposition=entry["agent_proposed_disposition"],
                action=entry["agent_next_action"],
                overlay=overlay_label,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """读取 triage 与 review packet，写出 json/markdown/csv 三份产物。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--triage", required=True)
    parser.add_argument("--review-packets", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    triage_path = Path(args.triage).expanduser().resolve()
    packet_dir = Path(args.review_packets).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    triage = json.loads(triage_path.read_text(encoding="utf-8"))

    # packet 文件名（去掉 .json）就是族 id，逐个读入并建索引。
    packets: dict[str, dict[str, Any]] = {}
    for path in sorted(packet_dir.glob("qf-*.json")):
        packets[path.stem] = json.loads(path.read_text(encoding="utf-8"))

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

    # CSV 只导出关键列，列顺序固定，便于 diff 与外部工具读取。
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
            row = {}
            for key in fieldnames:
                row[key] = entry[key]
            writer.writerow(row)

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
