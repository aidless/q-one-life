#!/usr/bin/env python3
"""为每个论文族生成一份可审计的 review packet，并给出 Top-20 复核队列。

重要边界：packet 只是复核材料，不改变任何族的最终处置（final_disposition
一律保持 unreviewed），也不代表可发表或可上传。
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qone_life.research import sha256_file


def now() -> str:
    """返回当前 UTC 时间的 ISO 字符串（以 Z 结尾）。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized(value: str) -> str:
    """把字符串压成「小写 + 只留字母数字与汉字」的比对键。"""
    value = value.replace("\\", " ")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", value.lower()).strip()


def source_state(path: Path, expected_hash: str | None) -> dict[str, Any]:
    """检查主源文件是否存在、哈希是否与目录登记一致。

    没有登记哈希时（expected_hash 为 None）视为一致，避免误报漂移。
    """
    if not path.is_file():
        return {"exists": False, "sha256": None, "matches_catalog": None}

    actual = sha256_file(path)
    # 先假设一致，只有登记了哈希且实际哈希不同时才判定为漂移。
    matches = True
    if expected_hash is not None:
        matches = actual == expected_hash
    return {"exists": True, "sha256": actual, "matches_catalog": matches}


def overlay_matches(
    item: dict[str, Any], family_id: str | None, primary: Path
) -> bool:
    """判断某个 overlay 项目是否属于当前族。

    两条判据：paper_id 与族 id 相同；或 overlay 的 origin（及 origin 下的
    稿件文件名）与主源路径解析后完全一致。
    """
    project = item["project"]

    if project.get("paper_id") == family_id:
        return True

    origin_value = str(project.get("origin") or "")
    if not origin_value:
        return False

    origin = Path(origin_value)
    manuscript_path = Path(str(project.get("manuscript", {}).get("path") or ""))

    candidates = [origin]
    if origin.is_dir() and manuscript_path.name:
        candidates.append(origin / manuscript_path.name)

    # 逐个候选路径比对（用显式循环，便于阅读；已加 noqa 说明这是刻意写法）。
    for candidate in candidates:  # noqa: SIM110
        if primary.resolve() == candidate.resolve():
            return True
    return False


def _build_overlay_summary(overlay: dict[str, Any]) -> dict[str, Any]:
    """把 overlay 项目压成 packet 里用得到的摘要字段。"""
    payload = overlay["project"]
    overlay_root = overlay["path"].parent

    # 若 overlay 目录里有 research-plan.json，就把阶段与动作一起摘出来；
    # 没有该文件时用空字典，后续 get("stages"/"next_actions") 自然为空。
    plan_path = overlay_root / "reports" / "research-plan.json"
    plan = {}
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

    # 参考文献可能以 .bib / .bbl / bibliography.tex 任一种形式存在。
    bibliography_present = False
    for pattern in ("*.bib", "*.bbl", "bibliography.tex"):
        for candidate in overlay_root.rglob(pattern):
            if candidate.is_file():
                bibliography_present = True
                break
        if bibliography_present:
            break

    claim_states: Counter[Any] = Counter()
    for claim in payload.get("claims", []):
        if isinstance(claim, dict):
            claim_states[claim.get("state")] += 1

    plan_stages: dict[str, Any] = {}
    for item in plan.get("stages", []):
        plan_stages[item["stage"]] = item["state"]

    plan_actions: list[Any] = []
    for item in plan.get("next_actions", []):
        plan_actions.append(item["action_id"])

    return {
        "path": str(overlay["path"]),
        "status": payload.get("status"),
        "ledger_present": (overlay_root / "CLAIM_LEDGER.md").is_file(),
        "bibliography_present": bibliography_present,
        "evidence_present": (overlay_root / "evidence").is_dir(),
        "claims": len(payload.get("claims", [])),
        "claim_states": dict(claim_states),
        "package_state": payload.get("package", {}).get("state"),
        "package_blockers": payload.get("package", {}).get("blockers", []),
        "gate_receipts": len(payload.get("gate_receipts", [])),
        "plan_stages": plan_stages,
        "plan_actions": plan_actions,
    }


def main() -> int:
    """读取 portfolio/triage/overlays，写出逐族 packet、Top-20 与索引。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", required=True)
    parser.add_argument("--triage", required=True)
    parser.add_argument("--overlays-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    portfolio_path = Path(args.portfolio).expanduser().resolve()
    triage_path = Path(args.triage).expanduser().resolve()
    overlays_root = Path(args.overlays_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    triage = json.loads(triage_path.read_text(encoding="utf-8"))

    # 三个索引都以 project_id / family_id 为键，跳过非 dict 或缺键的条目。
    projects: dict[str, dict[str, Any]] = {}
    for item in portfolio["projects"]:
        if isinstance(item, dict) and item.get("project_id"):
            projects[item["project_id"]] = item

    records: dict[str, dict[str, Any]] = {}
    for item in [*portfolio["projects"], *portfolio.get("candidates", [])]:
        if isinstance(item, dict) and item.get("project_id"):
            records[item["project_id"]] = item

    families: dict[str, dict[str, Any]] = {}
    for item in portfolio["families"]:
        if isinstance(item, dict) and item.get("family_id"):
            families[item["family_id"]] = item

    # 扫描 overlay 根目录，只保留 schema 匹配的 project.json；
    # 读不了或不是合法 JSON 的条目直接跳过，不影响其它族。
    overlays: list[dict[str, Any]] = []
    for path in overlays_root.rglob("project.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("schema") == "q-one-research-project-v1":
            overlays.append({"path": path, "project": payload})

    generated_at = now()
    packets: list[dict[str, Any]] = []
    for record in triage["projects"]:
        project = projects.get(record["project_id"], {})
        family = families.get(record.get("family_id"), {})
        primary = Path(str(record.get("primary_source") or ""))
        expected_hash = project.get("primary_sha256")
        # 在 overlay 列表里找第一个属于本族的条目（没有就保持 None）。
        overlay = None
        for item in overlays:
            if overlay_matches(item, record.get("family_id"), primary):
                overlay = item
                break

        overlay_summary = None
        if overlay:
            overlay_summary = _build_overlay_summary(overlay)

        # 同族其它成员的源文件路径，供人工比对哪个是正本。
        variants: list[Any] = []
        for member in family.get("members", []):
            if not isinstance(member, dict):
                continue
            member_record = records.get(member.get("project_id"), {})
            primary_source = member_record.get("primary_source")
            if primary_source:
                variants.append(primary_source)

        # 四类证据信号：工程文件里有的，或 overlay 里已经有的，都算「有」。
        project_files = project.get("files", {})
        claim_ledger = bool(project_files.get("claim_ledgers"))
        if overlay_summary and overlay_summary["ledger_present"]:
            claim_ledger = True

        bibliography = bool(project_files.get("bibliographies"))
        if overlay_summary and overlay_summary["bibliography_present"]:
            bibliography = True

        evidence_directory = bool(project_files.get("evidence_directories"))
        if overlay_summary and overlay_summary["evidence_present"]:
            evidence_directory = True

        signals = {
            "claim_ledger": claim_ledger,
            "bibliography": bibliography,
            "compiled_pdf": bool(project_files.get("pdfs")),
            "evidence_directory": evidence_directory,
            "variants_to_reconcile": record.get("variants_to_reconcile", 0),
            "overlay_present": overlay is not None,
        }

        # 按机器建议给出对应的复核问题清单；未知建议给空清单。
        all_questions = {
            "merge": [
                "Which member is the canonical scientific source?",
                "Is every materially different result, figure, or claim represented in the canonical source?",
                "Can superseded copies be archived without losing unique evidence?",
            ],
            "archive": [
                "Does the source contain a unique result worth preserving?",
                "Is the stale or abandoned status documented?",
                "Should the family remain as a negative-result or historical record?",
            ],
            "repair": [
                "What is the paper's one-sentence bounded claim?",
                "Which claims have evidence fields and reproducible commands?",
                "What independent method/statistics review is still missing?",
            ],
        }
        questions = all_questions.get(record["suggested_disposition"], [])

        machine_recommendation = {
            "disposition": record.get("suggested_disposition"),
            "reason": record.get("suggestion_reason"),
            "next_action": record.get("suggested_next_action"),
            "authoritative": False,
        }
        # overlay 里有计划动作时，用前三个动作覆盖下一步动作，便于直接执行。
        if overlay_summary and overlay_summary["plan_actions"]:
            first_actions = overlay_summary["plan_actions"][:3]
            machine_recommendation["next_action"] = "overlay-plan:" + ",".join(first_actions)

        packet = {
            "schema": "q-one-paper-review-packet-v1",
            "generated_at": generated_at,
            "family_id": record.get("family_id"),
            "project_id": record.get("project_id"),
            "title": record.get("title"),
            "primary_source": record.get("primary_source"),
            "source_state": source_state(primary, expected_hash),
            "target": record.get("target"),
            "recorded_status": record.get("status"),
            "project_type": record.get("project_type"),
            "production_priority": record.get("production_priority"),
            "priority_band": record.get("priority_band"),
            "priority_factors": record.get("priority_factors", []),
            "pilot_ids": record.get("pilot_ids", []),
            "signals": signals,
            "variant_sources": variants,
            "machine_recommendation": machine_recommendation,
            "overlay": overlay_summary,
            "review_questions": questions,
            "required_for_arxiv_ready": [
                "A canonical source and exact source identity are recorded.",
                "Every material claim is registered with evidence fields and status.",
                "Numerical claims are recomputed from frozen inputs.",
                "Citations are resolved and the bibliography is mechanically valid.",
                "Independent method/statistics review is closed against the current hash.",
                "A clean-room compile and deterministic candidate package exist.",
                "Author, category, abstract, license and upload authorization are user-confirmed.",
            ],
            "review_decision": {
                "final_disposition": record.get("final_disposition", "unreviewed"),
                "reviewer": None,
                "reviewed_at": None,
                "reason": None,
            },
            "notes": [
                "This packet supports review; it does not assign a final disposition.",
                "Machine priority is not paper quality or acceptance probability.",
            ],
        }
        packets.append(packet)

        packet_path = output_dir / f"{record['family_id']}.json"
        packet_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # Top-20：按生产优先级倒序，再按标题与族 id 稳定排序。
    def rank_key(item: dict[str, Any]) -> tuple[int, str, str]:
        return (
            -int(item["production_priority"]),
            str(item["title"]),
            str(item["family_id"]),
        )

    ranked = sorted(packets, key=rank_key)
    top20 = ranked[:20]

    lines = [
        "# Research Factory Top-20 review queue",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Machine recommendation only. Every final disposition remains `unreviewed`.",
        "",
        "| # | Band | Suggested | Title | Variants | Ledger | Bib | Evidence | First action |",
        "|---:|---|---|---|---:|---:|---:|---:|---|",
    ]
    for index, item in enumerate(top20, 1):
        title = str(item["title"]).replace("|", "\\|")
        signals = item["signals"]
        ledger_text = "yes" if signals["claim_ledger"] else "no"
        bib_text = "yes" if signals["bibliography"] else "no"
        evidence_text = "yes" if signals["evidence_directory"] else "no"
        lines.append(
            f"| {index} | {item['priority_band']} | "
            f"{item['machine_recommendation']['disposition']} | {title} | "
            f"{signals['variants_to_reconcile']} | "
            f"{ledger_text} | "
            f"{bib_text} | "
            f"{evidence_text} | "
            f"{item['machine_recommendation']['next_action']} |"
        )
    (output_dir / "top20.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 汇总统计：各类处置计数、缺源/哈希不符、overlay 覆盖情况。
    unreviewed = 0
    source_missing = 0
    source_hash_mismatch = 0
    overlay_attachments = 0
    disposition_counts: Counter[Any] = Counter()
    overlay_paths: set[str] = set()

    for item in packets:
        if item["review_decision"]["final_disposition"] == "unreviewed":
            unreviewed += 1
        if not item["source_state"]["exists"]:
            source_missing += 1
        if item["source_state"]["matches_catalog"] is False:
            source_hash_mismatch += 1
        disposition_counts[item["machine_recommendation"]["disposition"]] += 1
        if item["overlay"]:
            overlay_attachments += 1
            overlay_path = item["overlay"].get("path")
            if overlay_path:
                overlay_paths.add(overlay_path)

    summary = {
        "paper_families": len(packets),
        "unreviewed": unreviewed,
        "suggested_dispositions": dict(sorted(disposition_counts.items())),
        "source_missing": source_missing,
        "source_hash_mismatch": source_hash_mismatch,
        "overlays": len(overlay_paths),
        "overlay_attachments": overlay_attachments,
    }

    # 索引里逐个记录 packet 的哈希与最终处置，便于外部核对。
    packet_entries = []
    for item in ranked:
        family_id = item["family_id"]
        packet_entries.append(
            {
                "family_id": family_id,
                "path": f"{family_id}.json",
                "sha256": sha256_file(output_dir / f"{family_id}.json"),
                "final_disposition": item["review_decision"]["final_disposition"],
            }
        )

    index = {
        "schema": "q-one-review-packet-index-v1",
        "generated_at": generated_at,
        "inputs": [
            {"path": str(portfolio_path), "sha256": sha256_file(portfolio_path)},
            {"path": str(triage_path), "sha256": sha256_file(triage_path)},
        ],
        "summary": summary,
        "top20": str((output_dir / "top20.md").relative_to(output_dir.parent)),
        "packets": packet_entries,
        "notes": [
            "No packet changes the source manifest or paper disposition.",
            "Source hashes are checked against the portfolio catalog when present.",
        ],
    }
    (output_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
