"""自动审稿 rubric：机械检查 + 注入式模型评分。

机械检查在本地可复算；模型评分通过显式注入的 model_call 获取。
任何一项模型评分缺失都记为 inconclusive，且不计算总分。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

RUBRIC_SCHEMA = "q-one-review-rubric-v1"

DEFAULT_WEIGHTS = {
    "novelty": 0.3,
    "rigor": 0.4,
    "clarity": 0.3,
}

DIMENSION_PROMPT = (
    "Score the manuscript on the dimension '{dimension}' from 1 to 5, where 1 is "
    "poor and 5 is excellent. Base the score only on the text below.\n\n"
    "Manuscript:\n{manuscript}\n\n"
    "Return JSON only: {{\"score\": <integer 1-5>, \"justification\": \"<one sentence>\"}}"
)

ModelCall = Callable[[str], str | None]


class ReviewRubricError(RuntimeError):
    """rubric 输入或输出无法安全解析时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_claim_ledger(text: str) -> dict[str, int]:
    """统计 Markdown 论断账本中各状态的数量。

    按表头定位 State 列，兼容 4 列与 6 列等不同账本格式。
    """
    counts = {"verified": 0, "candidate": 0, "inconclusive": 0, "blocked": 0}
    state_index: int | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if state_index is None:
            lowered = [cell.lower() for cell in cells]
            for name in ("state", "status"):
                if name in lowered:
                    state_index = lowered.index(name)
                    break
            continue
        if not re.fullmatch(r"C\d+", cells[0]):
            continue
        if state_index >= len(cells):
            continue
        state = cells[state_index].lower()
        if state in counts:
            counts[state] += 1
    return counts


def run_mechanical_checks(manuscript: str, ledger: str) -> dict[str, Any]:
    """执行可本地复算的机械检查。"""
    counts = parse_claim_ledger(ledger)
    total_claims = sum(counts.values())
    verified_ratio = counts["verified"] / total_claims if total_claims else 0.0

    checks = [
        {
            "check_id": "claims_present",
            "passed": total_claims > 0,
            "detail": f"{total_claims} claims parsed from ledger",
        },
        {
            "check_id": "no_blocked_claims",
            "passed": counts["blocked"] == 0,
            "detail": f"{counts['blocked']} blocked claims",
        },
        {
            "check_id": "verified_ratio",
            "passed": verified_ratio >= 0.5,
            "detail": f"verified ratio {verified_ratio:.2f}",
        },
        {
            "check_id": "limitations_section",
            "passed": bool(re.search(r"\b(limitations?|threats to validity)\b", manuscript, re.I)),
            "detail": "limitations section present",
        },
        {
            "check_id": "reproducibility_statement",
            "passed": bool(
                re.search(
                    r"\b(reproducib\w*|code availability|artifact availability|open.?source)\b",
                    manuscript,
                    re.I,
                )
            ),
            "detail": "reproducibility or artifact statement present",
        },
        {
            "check_id": "citations_present",
            "passed": bool(re.search(r"\\cite\{|\\citep\{|\\citet\{", manuscript)),
            "detail": "LaTeX citation commands present",
        },
    ]
    return {
        "claim_counts": counts,
        "total_claims": total_claims,
        "verified_ratio": round(verified_ratio, 4),
        "checks": checks,
        "all_passed": all(item["passed"] for item in checks),
    }


def _parse_score(text: str) -> tuple[int, str] | None:
    """解析模型返回的 score/justification；失败返回 None。"""
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
    stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        payload = json.loads(stripped[start:end + 1])
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        score = int(payload.get("score"))
    except (TypeError, ValueError):
        return None
    if score < 1 or score > 5:
        return None
    justification = payload.get("justification")
    if not isinstance(justification, str) or not justification.strip():
        return None
    return score, justification.strip()


def score_manuscript(
    manuscript_path: str | Path,
    ledger_path: str | Path,
    model_call: ModelCall,
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """生成审稿回执；机械检查不全过或评分缺失时不计算总分。"""
    manuscript_file = Path(manuscript_path).expanduser().resolve()
    ledger_file = Path(ledger_path).expanduser().resolve()
    if not manuscript_file.is_file():
        raise ReviewRubricError(f"manuscript is missing: {manuscript_file}")
    if not ledger_file.is_file():
        raise ReviewRubricError(f"claim ledger is missing: {ledger_file}")
    if not callable(model_call):
        raise ReviewRubricError("model_call must be callable")

    manuscript_bytes = manuscript_file.read_bytes()
    ledger_bytes = ledger_file.read_bytes()
    manuscript = manuscript_bytes.decode("utf-8", errors="replace")
    ledger = ledger_bytes.decode("utf-8", errors="replace")

    mechanical = run_mechanical_checks(manuscript, ledger)

    resolved_weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(resolved_weights) != set(DEFAULT_WEIGHTS):
        raise ReviewRubricError(
            f"weights must cover exactly {sorted(DEFAULT_WEIGHTS)}"
        )
    if abs(sum(resolved_weights.values()) - 1.0) > 1e-6:
        raise ReviewRubricError("weights must sum to 1.0")

    dimensions: list[dict[str, Any]] = []
    for dimension in DEFAULT_WEIGHTS:
        prompt = DIMENSION_PROMPT.format(dimension=dimension, manuscript=manuscript)
        answer = model_call(prompt)
        parsed = _parse_score(answer) if answer else None
        if parsed is None:
            dimensions.append({
                "dimension": dimension,
                "weight": resolved_weights[dimension],
                "score": None,
                "state": "inconclusive",
                "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
            })
            continue
        score, justification = parsed
        dimensions.append({
            "dimension": dimension,
            "weight": resolved_weights[dimension],
            "score": score,
            "state": "scored",
            "justification": justification,
            "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
        })

    all_scored = all(item["state"] == "scored" for item in dimensions)
    total = None
    if all_scored and mechanical["all_passed"]:
        total = sum(item["score"] * item["weight"] for item in dimensions)
        total = round(total, 4)

    return {
        "schema": RUBRIC_SCHEMA,
        "generated_at": _now(),
        "manuscript_path": str(manuscript_file),
        "manuscript_sha256": _sha256_bytes(manuscript_bytes),
        "ledger_path": str(ledger_file),
        "ledger_sha256": _sha256_bytes(ledger_bytes),
        "mechanical": mechanical,
        "dimensions": dimensions,
        "all_dimensions_scored": all_scored,
        "total": total,
        "status": "scored" if total is not None else "inconclusive",
        "note": (
            "总分只在机械检查全过且三个维度均有评分时计算；"
            "该分数不是录用结论。"
        ),
    }


def write_review_report(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """把审稿回执写入 JSON 文件并回填哈希。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
