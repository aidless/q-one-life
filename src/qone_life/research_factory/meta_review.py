"""元评审：把审稿分数、对抗评审与反驳计划聚合成下一步决策。

决策语义：
- stop：当前稿达到阈值且无未处理异议，交人工审阅；
- continue：还需要一轮修订或实验；
- rollback：当前稿相对上一稿退化，或机械检查失败。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

META_SCHEMA = "q-one-meta-review-v1"

DECISION_STOP = "stop"
DECISION_CONTINUE = "continue"
DECISION_ROLLBACK = "rollback"
DECISION_WITHHOLD = "withhold"


class MetaReviewError(RuntimeError):
    """输入不足以做出安全决策时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def decide(
    *,
    rubric: dict[str, Any],
    adversarial: dict[str, Any] | None = None,
    rebuttal: dict[str, Any] | None = None,
    integrity: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    previous_total: float | None = None,
    accept_threshold: float = 4.0,
) -> dict[str, Any]:
    """返回决策与理由；不接受缺失的 rubric。"""
    if not isinstance(rubric, dict) or "mechanical" not in rubric:
        raise MetaReviewError("rubric report is missing mechanical checks")

    reasons: list[str] = []
    decision = DECISION_CONTINUE

    mechanical = rubric.get("mechanical") or {}
    total = rubric.get("total")

    if not mechanical.get("all_passed", False):
        failed = [
            item.get("check_id")
            for item in mechanical.get("checks", [])
            if not item.get("passed")
        ]
        reasons.append(f"mechanical checks failed: {', '.join(failed) or 'unknown'}")
        decision = DECISION_ROLLBACK
    elif total is None:
        reasons.append("rubric has no total: some dimensions are inconclusive")
        decision = DECISION_CONTINUE
    elif previous_total is not None and total < previous_total:
        reasons.append(
            f"total regressed from {previous_total:.4f} to {float(total):.4f}"
        )
        decision = DECISION_ROLLBACK
    else:
        reasons.append(f"rubric total {float(total):.4f}")

    objected = 0
    inconclusive = 0
    objected_claims: set[str] = set()
    if adversarial is not None:
        objected = int(adversarial.get("objected", 0) or 0)
        inconclusive = int(adversarial.get("inconclusive", 0) or 0)
        for item in adversarial.get("claims", []):
            if item.get("verdict") == "objected":
                objected_claims.add(str(item.get("claim_id")))
        if objected:
            reasons.append(f"{objected} claims still objected")
        if inconclusive:
            reasons.append(f"{inconclusive} claims inconclusive")

    closed_claims: set[str] = set()
    if closure is not None:
        closed_claims = {
            str(item.get("claim_id"))
            for item in closure.get("results", [])
            if item.get("status") == "closed"
        }
        if closed_claims:
            reasons.append(
                f"{len(closed_claims)} objections closed by recorded fields"
            )
            if objected_claims:
                objected = len(objected_claims - closed_claims)
                reasons.append(f"{objected} claims remain objected after closure")

    executable_claims: set[str] = set()
    out_of_loop = 0
    if rebuttal is not None:
        for item in rebuttal.get("objections", []):
            if item.get("class") == "executable":
                executable_claims.add(str(item.get("claim_id")))
            elif item.get("class") == "out_of_loop":
                out_of_loop += 1
        if out_of_loop:
            reasons.append(
                f"{out_of_loop} novelty/idea objections are out of loop and "
                "cannot be auto-resolved"
            )

    unresolved = objected > len(executable_claims)
    if unresolved and decision != DECISION_ROLLBACK:
        reasons.append(
            f"only {len(executable_claims)} executable rebuttals cover {objected} objections"
        )
        decision = DECISION_CONTINUE

    integrity_status = None
    if integrity is not None:
        integrity_status = integrity.get("status")
        if integrity_status == "violation":
            names = [
                item.get("type")
                for item in integrity.get("findings", [])
                if item.get("state") == "violation"
            ]
            reasons.append(f"research-integrity violation: {', '.join(str(n) for n in names)}")
            decision = DECISION_WITHHOLD
        elif integrity_status == "incomplete":
            reasons.append(
                f"{integrity.get('not_assessed', 0)} integrity checks not assessed"
            )
            if decision == DECISION_STOP:
                decision = DECISION_CONTINUE

    if (
        decision == DECISION_CONTINUE
        and total is not None
        and float(total) >= accept_threshold
        and objected == 0
        and inconclusive == 0
        and (integrity_status is None or integrity_status == "passed")
    ):
        decision = DECISION_STOP
        reasons.append(
            f"total {float(total):.4f} >= threshold {accept_threshold:.4f} and no open objections"
        )

    return {
        "schema": META_SCHEMA,
        "generated_at": _now(),
        "decision": decision,
        "reasons": reasons,
        "accept_threshold": accept_threshold,
        "previous_total": previous_total,
        "current_total": total,
        "objected": objected,
        "inconclusive": inconclusive,
        "integrity_status": integrity_status,
        "closed_claims": sorted(closed_claims),
        "executable_rebuttals": sorted(executable_claims),
        "inputs": {
            "rubric_sha256": _hash_payload(rubric),
            "adversarial_sha256": _hash_payload(adversarial) if adversarial else None,
            "rebuttal_sha256": _hash_payload(rebuttal) if rebuttal else None,
        },
        "note": "stop 只表示交人工审阅，不是录用结论。",
    }


def write_decision(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """写入决策回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
