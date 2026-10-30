#!/usr/bin/env python3
"""Generate one auditable review packet per paper family and a Top-20 queue."""

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
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized(value: str) -> str:
    value = value.replace("\\", " ")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", value.lower()).strip()


def source_state(path: Path, expected_hash: str | None) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "sha256": None, "matches_catalog": None}
    actual = sha256_file(path)
    return {
        "exists": True,
        "sha256": actual,
        "matches_catalog": expected_hash is None or actual == expected_hash,
    }


def overlay_matches(
    item: dict[str, Any], family_id: str | None, primary: Path
) -> bool:
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
    return any(primary.resolve() == candidate.resolve() for candidate in candidates)


def main() -> int:
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
    projects = {
        item["project_id"]: item
        for item in portfolio["projects"]
        if isinstance(item, dict) and item.get("project_id")
    }
    records = {
        item["project_id"]: item
        for item in [*portfolio["projects"], *portfolio.get("candidates", [])]
        if isinstance(item, dict) and item.get("project_id")
    }
    families = {
        item["family_id"]: item
        for item in portfolio["families"]
        if isinstance(item, dict) and item.get("family_id")
    }
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
        overlay = next(
            (
                item
                for item in overlays
                if overlay_matches(item, record.get("family_id"), primary)
            ),
            None,
        )
        overlay_summary = None
        if overlay:
            payload = overlay["project"]
            overlay_root = overlay["path"].parent
            plan_path = overlay_root / "reports" / "research-plan.json"
            plan = (
                json.loads(plan_path.read_text(encoding="utf-8"))
                if plan_path.is_file()
                else {}
            )
            overlay_summary = {
                "path": str(overlay["path"]),
                "status": payload.get("status"),
                "ledger_present": (overlay_root / "CLAIM_LEDGER.md").is_file(),
                "bibliography_present": any(
                    path.is_file()
                    for path in [
                        *overlay_root.rglob("*.bib"),
                        *overlay_root.rglob("*.bbl"),
                        *overlay_root.rglob("bibliography.tex"),
                    ]
                ),
                "evidence_present": (overlay_root / "evidence").is_dir(),
                "claims": len(payload.get("claims", [])),
                "claim_states": dict(
                    Counter(
                        claim.get("state")
                        for claim in payload.get("claims", [])
                        if isinstance(claim, dict)
                    )
                ),
                "package_state": payload.get("package", {}).get("state"),
                "package_blockers": payload.get("package", {}).get("blockers", []),
                "gate_receipts": len(payload.get("gate_receipts", [])),
                "plan_stages": {
                    item["stage"]: item["state"] for item in plan.get("stages", [])
                },
                "plan_actions": [
                    item["action_id"] for item in plan.get("next_actions", [])
                ],
            }
        variants = []
        for member in family.get("members", []):
            if not isinstance(member, dict):
                continue
            member_record = records.get(member.get("project_id"), {})
            primary_source = member_record.get("primary_source")
            if primary_source:
                variants.append(primary_source)
        signals = {
            "claim_ledger": bool(project.get("files", {}).get("claim_ledgers"))
            or bool(overlay_summary and overlay_summary["ledger_present"]),
            "bibliography": bool(project.get("files", {}).get("bibliographies"))
            or bool(overlay_summary and overlay_summary["bibliography_present"]),
            "compiled_pdf": bool(project.get("files", {}).get("pdfs")),
            "evidence_directory": bool(
                project.get("files", {}).get("evidence_directories")
            )
            or bool(overlay_summary and overlay_summary["evidence_present"]),
            "variants_to_reconcile": record.get("variants_to_reconcile", 0),
            "overlay_present": overlay is not None,
        }
        questions = {
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
        }.get(record["suggested_disposition"], [])
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
            "machine_recommendation": {
                "disposition": record.get("suggested_disposition"),
                "reason": record.get("suggestion_reason"),
                "next_action": record.get("suggested_next_action"),
                "authoritative": False,
            },
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
        if overlay_summary and overlay_summary["plan_actions"]:
            packet["machine_recommendation"]["next_action"] = (
                "overlay-plan:" + ",".join(overlay_summary["plan_actions"][:3])
            )
        packets.append(packet)
        packet_path = output_dir / f"{record['family_id']}.json"
        packet_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    ranked = sorted(
        packets,
        key=lambda item: (
            -int(item["production_priority"]),
            str(item["title"]),
            str(item["family_id"]),
        ),
    )
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
        lines.append(
            f"| {index} | {item['priority_band']} | "
            f"{item['machine_recommendation']['disposition']} | {title} | "
            f"{signals['variants_to_reconcile']} | "
            f"{'yes' if signals['claim_ledger'] else 'no'} | "
            f"{'yes' if signals['bibliography'] else 'no'} | "
            f"{'yes' if signals['evidence_directory'] else 'no'} | "
            f"{item['machine_recommendation']['next_action']} |"
        )
    (output_dir / "top20.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "paper_families": len(packets),
        "unreviewed": sum(
            1
            for item in packets
            if item["review_decision"]["final_disposition"] == "unreviewed"
        ),
        "suggested_dispositions": dict(
            sorted(
                Counter(
                    item["machine_recommendation"]["disposition"] for item in packets
                ).items()
            )
        ),
        "source_missing": sum(
            1 for item in packets if not item["source_state"]["exists"]
        ),
        "source_hash_mismatch": sum(
            1
            for item in packets
            if item["source_state"]["matches_catalog"] is False
        ),
        "overlays": len(
            {
                item["overlay"]["path"]
                for item in packets
                if item.get("overlay") and item["overlay"].get("path")
            }
        ),
        "overlay_attachments": sum(1 for item in packets if item["overlay"]),
    }
    index = {
        "schema": "q-one-review-packet-index-v1",
        "generated_at": generated_at,
        "inputs": [
            {"path": str(portfolio_path), "sha256": sha256_file(portfolio_path)},
            {"path": str(triage_path), "sha256": sha256_file(triage_path)},
        ],
        "summary": summary,
        "top20": str((output_dir / "top20.md").relative_to(output_dir.parent)),
        "packets": [
            {
                "family_id": item["family_id"],
                "path": f"{item['family_id']}.json",
                "sha256": sha256_file(output_dir / f"{item['family_id']}.json"),
                "final_disposition": item["review_decision"]["final_disposition"],
            }
            for item in ranked
        ],
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
