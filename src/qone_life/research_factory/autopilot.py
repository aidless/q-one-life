"""假设生成与筛选：ScientistTwo 式 idea generator 的本地可逆实现。

设计约束：
- 模型调用通过显式注入，不在模块内隐式联网；
- 模型输出视为不可信输入，必须通过结构校验；
- 缺失或超时记为 inconclusive，不静默降级为通过。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CANDIDATE_SCHEMA = "q-one-hypothesis-candidates-v1"
SCREENING_SCHEMA = "q-one-hypothesis-screening-v1"

REQUIRED_KEYS = (
    "null_hypothesis",
    "alternative_hypothesis",
    "falsification_condition",
    "novelty_rationale",
    "required_resources",
)

PROMPT_TEMPLATE = (
    "You are designing falsifiable research hypotheses for the following question.\n"
    "Question:\n{question}\n\n"
    "Produce exactly {n} distinct hypotheses as a JSON array. Each item must be an "
    "object with these non-empty string keys:\n"
    "- null_hypothesis\n"
    "- alternative_hypothesis\n"
    "- falsification_condition\n"
    "- novelty_rationale\n"
    "- required_resources\n"
    "Return only the JSON array, with no prose or code fences."
)

ModelCall = Callable[[str], str | None]
Scorer = Callable[[dict[str, Any]], float | None]


class AutopilotError(RuntimeError):
    """假设生成或筛选无法安全完成时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_json_array(text: str) -> list[Any] | None:
    """从模型输出中提取 JSON 数组；容忍 code fence 与前后说明文字。"""
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
    stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stripped[start:end + 1])
    except ValueError:
        return None
    return parsed if isinstance(parsed, list) else None


def _validate_candidate(item: Any, index: int) -> dict[str, Any]:
    """校验单条候选假设；任何缺字段直接整批拒绝。"""
    if not isinstance(item, dict):
        raise AutopilotError(f"candidate {index} is not an object")
    candidate: dict[str, Any] = {"candidate_id": f"H{index + 1:02d}"}
    for key in REQUIRED_KEYS:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AutopilotError(
                f"candidate {index} missing non-empty string field: {key}"
            )
        candidate[key] = value.strip()
    return candidate


def generate_hypotheses(
    question: str,
    model_call: ModelCall,
    *,
    n: int = 5,
) -> dict[str, Any]:
    """生成 n 条候选假设；无模型输出或结构不合法时 fail-closed。"""
    if n < 1:
        raise AutopilotError("n must be at least 1")
    if not callable(model_call):
        raise AutopilotError("model_call must be callable")
    text = question.strip()
    if not text:
        raise AutopilotError("question is empty")

    prompt = PROMPT_TEMPLATE.format(question=text, n=n)
    answer = model_call(prompt)
    if answer is None or not answer.strip():
        raise AutopilotError("model call returned no content")

    parsed = _extract_json_array(answer)
    if parsed is None:
        raise AutopilotError("model output is not a JSON array")
    if len(parsed) < n:
        raise AutopilotError(
            f"model returned {len(parsed)} candidates, expected at least {n}"
        )

    candidates = [_validate_candidate(item, index) for index, item in enumerate(parsed[:n])]
    return {
        "schema": CANDIDATE_SCHEMA,
        "generated_at": _now(),
        "question": text,
        "question_sha256": _sha256_text(text),
        "prompt_sha256": _sha256_text(prompt),
        "model_output_sha256": _sha256_text(answer),
        "requested": n,
        "candidates": candidates,
    }


def _coerce_score(value: Any, candidate_id: str) -> float | None:
    """把 scorer 返回值收敛为 [0,1]；无法解释的值记为 inconclusive。"""
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score != score or score < 0.0 or score > 1.0:
        raise AutopilotError(
            f"scorer returned out-of-range score for {candidate_id}: {value!r}"
        )
    return score


def screen_hypotheses(
    candidates: list[dict[str, Any]],
    scorer: Scorer,
    *,
    top_k: int = 2,
) -> dict[str, Any]:
    """在代理评分上筛选候选；inconclusive 不当作 0 分。"""
    if not candidates:
        raise AutopilotError("no candidates to screen")
    if top_k < 1:
        raise AutopilotError("top_k must be at least 1")
    if not callable(scorer):
        raise AutopilotError("scorer must be callable")

    evaluated: list[dict[str, Any]] = []
    inconclusive = 0
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "?")
        score = _coerce_score(scorer(candidate), candidate_id)
        if score is None:
            inconclusive += 1
        evaluated.append({
            "candidate_id": candidate_id,
            "score": score,
            "state": "inconclusive" if score is None else "scored",
        })

    status = "ok"
    if inconclusive * 2 > len(evaluated):
        status = "blocked"

    ranked = sorted(
        [item for item in evaluated if item["score"] is not None],
        key=lambda item: (-item["score"], item["candidate_id"]),
    )
    selected = [item["candidate_id"] for item in ranked[:top_k]]
    return {
        "schema": SCREENING_SCHEMA,
        "generated_at": _now(),
        "status": status,
        "top_k": top_k,
        "evaluated": evaluated,
        "ranked": ranked,
        "selected": selected,
        "inconclusive": inconclusive,
        "note": (
            "inconclusive 表示评分不可得，不是 0 分；"
            "超过半数不可得时整批 blocked。"
        ),
    }


def write_autopilot_report(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """把生成或筛选回执写入 JSON 文件并回填哈希。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


SCORE_PROMPT = (
    "Rate the following research hypothesis on a 0-1 scale for how likely it is "
    "to produce a falsifiable, cheap-to-screen result. Return JSON only: "
    "{{\"score\": <number 0-1>, \"reason\": \"<one sentence>\"}}\n\n"
    "Hypothesis:\n{candidate}\n"
)


def make_hypothesis_scorer(model_call: ModelCall) -> Scorer:
    """用同一个 model_call 构造一个返回 0-1 代理分的 scorer。"""
    if not callable(model_call):
        raise AutopilotError("model_call must be callable")

    def scorer(candidate: dict[str, Any]) -> float | None:
        payload = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
        answer = model_call(SCORE_PROMPT.format(candidate=payload))
        if not answer:
            return None
        stripped = re.sub(r"^```(?:json)?\s*", "", answer.strip())
        stripped = re.sub(r"\s*```$", "", stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(stripped[start:end + 1])
        except ValueError:
            return None
        if not isinstance(parsed, dict):
            return None
        try:
            return float(parsed.get("score"))
        except (TypeError, ValueError):
            return None

    return scorer


def run_batch(
    items: list[dict[str, Any]],
    model_call: ModelCall,
    *,
    n: int = 5,
    top_k: int = 2,
    output_dir: str | Path,
) -> dict[str, Any]:
    """逐项运行生成+筛选；单项失败只标记该项，不影响其他项。"""
    if not items:
        raise AutopilotError("batch is empty")
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    scorer = make_hypothesis_scorer(model_call)

    results: list[dict[str, Any]] = []
    for item in items:
        slug = str(item.get("slug") or "").strip()
        question_path = item.get("question")
        if not slug or not question_path:
            results.append({
                "slug": slug or "?",
                "status": "failed",
                "error": "slug and question are required",
            })
            continue
        try:
            question = Path(question_path).expanduser().read_text(encoding="utf-8")
            candidates = generate_hypotheses(question, model_call, n=n)
            screening = screen_hypotheses(candidates["candidates"], scorer, top_k=top_k)
            item_dir = directory / slug
            candidates_written = write_autopilot_report(
                candidates, item_dir / "hypotheses.json"
            )
            screening_written = write_autopilot_report(
                screening, item_dir / "screening.json"
            )
            results.append({
                "slug": slug,
                "status": screening["status"],
                "selected": screening["selected"],
                "candidates_sha256": candidates_written["sha256"],
                "screening_sha256": screening_written["sha256"],
            })
        except (AutopilotError, OSError) as exc:
            results.append({"slug": slug, "status": "failed", "error": str(exc)})

    summary = {
        "schema": "q-one-autopilot-batch-v1",
        "generated_at": _now(),
        "count": len(results),
        "ok": sum(1 for item in results if item["status"] != "failed"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "results": results,
    }
    summary_path = directory / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        **summary,
        "summary_path": str(summary_path),
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    }
