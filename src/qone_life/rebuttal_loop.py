"""Rebuttal 闭环：把对抗评审的异议转成可执行的反驳实验计划。

设计依据 AppliedScientist (arXiv:2609.14738)：迭代修订对"执行类"缺陷
有效（85.3%），对"想法/新颖性"缺陷几乎无效（11.1%）。因此本模块先对
每条异议做分类，只对可执行类生成反驳实验，想法类显式标记为闭环外。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXECUTION_KEYWORDS = (
    "implementation", "code", "run", "script", "dataset", "sample size",
    "seed", "baseline", "ablation", "metric", "reproduce", "missing",
    "error", "bug", "compute", "timeout", "config", "version", "evaluat",
    "benchmark", "table", "number", "statistic", "significan", "power",
    "regression", "test", "pipeline", "artifact", "reproduc",
)

CLASS_EXECUTABLE = "executable"
CLASS_OUT_OF_LOOP = "out_of_loop"
CLASS_UNCLASSIFIED = "unclassified"


class RebuttalError(RuntimeError):
    """反驳计划无法生成时抛出的异常。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def classify_objection(text: str) -> str:
    """把一条异议归类为可执行、闭环外或未分类。"""
    normalized = text.lower()
    if any(keyword in normalized for keyword in EXECUTION_KEYWORDS):
        return CLASS_EXECUTABLE
    idea_markers = (
        "novelty", "novel", "significance", "significant contribution",
        "original", "impact", "why this matters", "overclaim",
    )
    if any(marker in normalized for marker in idea_markers):
        return CLASS_OUT_OF_LOOP
    return CLASS_UNCLASSIFIED


def _extract_objections(attack_output: Path) -> list[dict[str, Any]]:
    """从对抗评审输出目录收集逐 claim 的异议，带 claim_id。"""
    summary_path = attack_output / "summary.json"
    if not summary_path.is_file():
        raise RebuttalError(f"adversarial summary missing: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    objections: list[dict[str, Any]] = []
    for claim in summary.get("claims", []):
        claim_id = claim.get("claim_id")
        claim_receipt = attack_output / f"{claim_id}.json"
        if not claim_receipt.is_file():
            continue
        receipt = json.loads(claim_receipt.read_text(encoding="utf-8"))
        for entry in receipt.get("objections", []):
            objections.append({
                "claim_id": claim_id,
                "claim_text": receipt.get("claim_text", ""),
                "objection": entry.get("text", ""),
                "count": entry.get("count", 0),
                "kinds": entry.get("kinds", []),
                "models": entry.get("models", []),
            })
    return objections


def draft_experiment(objection: dict[str, Any]) -> dict[str, str]:
    """把一条可执行异议草拟成一个反驳实验（不含任何实测数值）。"""
    claim_id = objection["claim_id"]
    check = (
        f"Design and run a targeted check that refutes objection on "
        f"{claim_id}: {objection['objection']}"
    )
    accept = (
        f"Objection on {claim_id} is resolved only if the check reproduces "
        f"the reported result and the objection's concrete failure mode "
        f"does not appear."
    )
    reject = (
        f"Objection on {claim_id} stands if the check reproduces the "
        f"failure mode described in the objection."
    )
    return {
        "experiment": check,
        "acceptance_criteria": accept,
        "rejection_criteria": reject,
    }


def build_rebuttal_plan(attack_output: str | Path) -> dict[str, Any]:
    """读取对抗评审输出，生成分类后的反驳计划（不执行任何实验）。"""
    attack_output = Path(attack_output).expanduser().resolve()
    objections = _extract_objections(attack_output)
    if not objections:
        raise RebuttalError("no objections found to rebut")

    classified: list[dict[str, Any]] = []
    counts = {CLASS_EXECUTABLE: 0, CLASS_OUT_OF_LOOP: 0, CLASS_UNCLASSIFIED: 0}
    for item in objections:
        cls = classify_objection(item["objection"])
        counts[cls] += 1
        entry = {**item, "class": cls}
        if cls == CLASS_EXECUTABLE:
            entry["experiment"] = draft_experiment(item)
        classified.append(entry)

    executable = [c for c in classified if c["class"] == CLASS_EXECUTABLE]
    if not executable:
        raise RebuttalError(
            "no executable objections: rebuttal loop cannot run any check"
        )

    return {
        "schema": "q-one-rebuttal-plan-v1",
        "generated_at": _now(),
        "attack_output": str(attack_output),
        "attack_output_sha256": hashlib.sha256(
            (attack_output / "summary.json").read_bytes()
        ).hexdigest(),
        "objections": classified,
        "counts": counts,
        "executable_count": counts[CLASS_EXECUTABLE],
        "out_of_loop_count": counts[CLASS_OUT_OF_LOOP],
        "unclassified_count": counts[CLASS_UNCLASSIFIED],
        "note": (
            "Per AppliedScientist (arXiv:2609.14738), only execution-class "
            "objections enter the rebuttal loop. Idea/novelty objections "
            "are recorded as out_of_loop and are not claimed as resolvable."
        ),
    }


def write_rebuttal_plan(plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """把反驳计划写成 Markdown，并返回文件路径。"""
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# REBUTTAL_PLAN.md",
        "",
        f"Generated: {plan['generated_at']}",
        f"Attack output: {plan['attack_output']}",
        "",
        f"Executable: {plan['executable_count']} · "
        f"Out-of-loop: {plan['out_of_loop_count']} · "
        f"Unclassified: {plan['unclassified_count']}",
        "",
        "| Claim | Class | Objection | Rebuttal check |",
        "|---|---|---|---|",
    ]
    for item in plan["objections"]:
        check = ""
        if "experiment" in item:
            check = item["experiment"]["experiment"]
        lines.append(
            f"| {item['claim_id']} | {item['class']} | "
            f"{item['objection'][:120]} | {check[:160]} |"
        )
    lines.append("")
    lines.append(plan["note"])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "rebuttal_plan_path": str(output_path),
        "rebuttal_plan_sha256": hashlib.sha256(
            output_path.read_bytes()
        ).hexdigest(),
    }


def plan_to_registrations(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """把可执行异议转成实验登记字段。

    资源需求固定含 "cloud"，使 ``plan_experiment`` 置
    ``approval_required=True``，从而云端执行必须人工批准。
    """
    registrations: list[dict[str, Any]] = []
    for item in plan.get("objections", []):
        if item.get("class") != CLASS_EXECUTABLE:
            continue
        experiment = item.get("experiment") or {}
        registrations.append({
            "claim_id": item["claim_id"],
            "objection": item["objection"],
            "missing_evidence": item["objection"],
            "proposed_experiment": experiment.get("experiment", ""),
            "acceptance_criteria": experiment.get("acceptance_criteria", ""),
            "rejection_criteria": experiment.get("rejection_criteria", ""),
            "resource_requirement": "cloud",
            "approval_required": True,
        })
    return registrations


def render_plan_json(plan: dict[str, Any]) -> str:
    """渲染计划的稳定 JSON 表示，供回执哈希使用。"""
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
