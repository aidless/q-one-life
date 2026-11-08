"""Free multi-model PaperBench judge panel.

This module never reads keys from disk. It uses an OpenAI-compatible local
gateway, a process-local placeholder key, and explicit per-model GO receipts.
A batch is `complete` only when every locked model returned a parseable score.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

SCHEMA = "qone-free-multimodel-judge-v1"
DEFAULT_BASE_URL = "http://127.0.0.1:3425/v1"
PLACEHOLDER_KEY = "local-gateway-nonempty-placeholder"
CANDIDATE_MODELS = (
    "opencode-zen-free/deepseek-v4.1-flash-free",
    "opencode-zen-free/crouton-alpha-free",
    "openrouter/recursive/flint-v1.0:free",
    "openrouter/xingchen-agi/xing4.0-29b-a4b:free",
    "openrouter/nvidia/nemotron-3.5-super-vl:free",
    "opencode-go/beam-free",
    "opencode-go/iceman-contributor-free",
    "workbuddy/hy4free",
    "workbuddy-ai/hy4free",
)
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_.-]{12,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|authorization)\s*[:=]\s*['\"][^'\"]{12,}['\"]", re.IGNORECASE),
)


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact(text: str) -> str:
    out = text
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


@dataclass(frozen=True)
class PanelConfig:
    model_ids: tuple[str, ...]
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 60.0
    retries: int = 3
    max_concurrency: int = 3
    official: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "model_ids": list(self.model_ids)}


@dataclass
class ModelResult:
    model_id: str
    leaf_id: str
    status: str
    score: float | None = None
    explanation: str = ""
    raw_response_sha256: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PanelReceipt:
    panel_id: str
    model_ids: tuple[str, ...]
    leaf_ids: tuple[str, ...]
    results: list[ModelResult]
    complete: bool
    blocked_reasons: list[str]
    official: bool = False
    judge_type: str = "free_multimodel"
    canonical_sha256: str = ""

    def body(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "panel_id": self.panel_id,
            "model_ids": list(self.model_ids),
            "leaf_ids": list(self.leaf_ids),
            "results": [row.to_dict() for row in self.results],
            "complete": self.complete,
            "blocked_reasons": self.blocked_reasons,
            "official": self.official,
            "judge_type": self.judge_type,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.body(), "canonical_sha256": self.canonical_sha256}


class JudgeParseError(RuntimeError):
    pass


def parse_judge_response(text: str) -> tuple[float, str]:
    """Accept strict JSON or a fenced JSON object with score/explanation."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        payload = json.loads(stripped)
    except ValueError as exc:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise JudgeParseError("response is not JSON") from exc
        try:
            payload = json.loads(match.group(0))
        except ValueError as inner:
            raise JudgeParseError("response has no JSON object") from inner
    if not isinstance(payload, dict):
        raise JudgeParseError("response JSON is not an object")
    score = payload.get("score")
    explanation = payload.get("explanation")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise JudgeParseError("score is missing or not numeric")
    score = float(score)
    if not 0.0 <= score <= 1.0:
        raise JudgeParseError("score outside [0, 1]")
    if not isinstance(explanation, str) or not explanation.strip():
        raise JudgeParseError("explanation is missing")
    return score, explanation.strip()


def build_messages(leaf_id: str, requirements: str, evidence: dict[str, Any]) -> list[dict[str, str]]:
    evidence_text = json.dumps(evidence, sort_keys=True, ensure_ascii=False)[:12000]
    prompt = (
        "You are grading one PaperBench rubric leaf. Return JSON only: "
        '{"score": <float 0..1>, "explanation": "<short evidence-grounded reason>"}.\n'
        f"leaf_id: {leaf_id}\nrequirements: {requirements}\n"
        f"evidence: {evidence_text}"
    )
    return [{"role": "user", "content": prompt}]


class OpenAICompatibleClient:
    """Minimal chat.completions client; injectable for unit tests."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def complete(self, model_id: str, messages: list[dict[str, str]], timeout_s: float) -> dict[str, Any]:
        import httpx

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {PLACEHOLDER_KEY}"},
            json={"model": model_id, "messages": messages, "temperature": 0.0},
            timeout=timeout_s,
        )
        response.raise_for_status()
        return response.json()


def extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise JudgeParseError("response has no choices")
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise JudgeParseError("response message has no text content")
    return content


def grade_batch(
    config: PanelConfig,
    leaves: list[dict[str, Any]],
    *,
    client: Any | None = None,
    go_receipts: dict[str, dict[str, Any]] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> PanelReceipt:
    if len(config.model_ids) != 3:
        raise ValueError("locked panel must contain exactly three models")
    if any(model_id not in CANDIDATE_MODELS for model_id in config.model_ids):
        raise ValueError("panel contains a model outside the fixed candidate queue")
    go_receipts = go_receipts or {}
    missing_go = [model_id for model_id in config.model_ids
                  if go_receipts.get(model_id, {}).get("go") is not True]
    if missing_go:
        receipt = PanelReceipt(
            panel_id="pre-go-" + canonical_sha256(config.to_dict())[:12],
            model_ids=config.model_ids,
            leaf_ids=tuple(str(leaf.get("leaf_id", "")) for leaf in leaves),
            results=[],
            complete=False,
            blocked_reasons=[f"missing_user_go:{model_id}" for model_id in missing_go],
        )
        receipt.canonical_sha256 = canonical_sha256(receipt.body())
        return receipt

    active = client or OpenAICompatibleClient(config.base_url, config.timeout_s)
    results: list[ModelResult] = []
    blocked: list[str] = []
    for leaf in leaves:
        leaf_id = str(leaf.get("leaf_id") or "")
        messages = build_messages(leaf_id, str(leaf.get("requirements") or ""),
                                  leaf.get("evidence") or {})
        for model_id in config.model_ids:
            attempts = 0
            last_error = ""
            raw_hash = ""
            usage: dict[str, Any] = {}
            score: float | None = None
            explanation = ""
            for attempt in range(config.retries):
                attempts += 1
                try:
                    payload = active.complete(model_id, messages, config.timeout_s)
                    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
                    raw_hash = sha256_text(raw)
                    usage = payload.get("usage") or {}
                    score, explanation = parse_judge_response(extract_content(payload))
                    last_error = ""
                    break
                except Exception as exc:
                    last_error = redact(f"{type(exc).__name__}: {exc}")[:300]
                    if attempt + 1 < config.retries:
                        sleep(min(2.0 ** attempt, 4.0))
            status = "scored" if score is not None else "blocked"
            if status != "scored":
                blocked.append(f"{model_id}:{leaf_id}:{last_error}")
            results.append(ModelResult(
                model_id=model_id,
                leaf_id=leaf_id,
                status=status,
                score=score,
                explanation=explanation,
                raw_response_sha256=raw_hash,
                usage=usage if isinstance(usage, dict) else {},
                attempts=attempts,
                error=last_error,
            ))
    expected = len(leaves) * len(config.model_ids)
    complete = len(results) == expected and all(row.status == "scored" for row in results)
    receipt = PanelReceipt(
        panel_id=canonical_sha256({**config.to_dict(),
                                   "leaf_ids": [str(leaf.get("leaf_id", "")) for leaf in leaves]})[:16],
        model_ids=config.model_ids,
        leaf_ids=tuple(str(leaf.get("leaf_id", "")) for leaf in leaves),
        results=results,
        complete=complete,
        blocked_reasons=blocked,
        official=config.official,
    )
    receipt.canonical_sha256 = canonical_sha256(receipt.body())
    return receipt


def probe_candidates(
    leaf: dict[str, Any],
    *,
    client: Any | None = None,
    candidates: tuple[str, ...] = CANDIDATE_MODELS,
    timeout_s: float = 60.0,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Find the first three candidates that return a parseable structured score."""
    active = client or OpenAICompatibleClient(DEFAULT_BASE_URL, timeout_s)
    passed: list[str] = []
    details: list[dict[str, Any]] = []
    messages = build_messages(str(leaf.get("leaf_id") or ""),
                              str(leaf.get("requirements") or ""),
                              leaf.get("evidence") or {})
    for model_id in candidates:
        attempts = 0
        state = "blocked"
        error = ""
        raw_hash = ""
        for attempt in range(retries):
            attempts += 1
            try:
                payload = active.complete(model_id, messages, timeout_s)
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))
                score, explanation = parse_judge_response(extract_content(payload))
                state = "passed"
                error = ""
                details.append({"model_id": model_id, "state": state, "attempts": attempts,
                                "score": score, "explanation_sha256": sha256_text(explanation),
                                "raw_response_sha256": raw_hash})
                passed.append(model_id)
                break
            except Exception as exc:
                error = redact(f"{type(exc).__name__}: {exc}")[:300]
                if attempt + 1 < retries:
                    sleep(min(2.0 ** attempt, 4.0))
        if state != "passed":
            details.append({"model_id": model_id, "state": state, "attempts": attempts,
                            "error": error, "raw_response_sha256": raw_hash})
        if len(passed) == 3:
            break
    locked = tuple(passed[:3]) if len(passed) >= 3 else ()
    report = {
        "schema": "qone-free-judge-panel-probe-v1",
        "base_url": DEFAULT_BASE_URL,
        "official": False,
        "candidate_queue": list(candidates),
        "lock_rule": "first_three_passed",
        "passed": passed,
        "locked_model_ids": list(locked),
        "complete": len(locked) == 3,
        "details": details,
        "user_go_required": True,
    }
    report["canonical_sha256"] = canonical_sha256(report)
    return report


def write_receipt(path: Path, receipt: PanelReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def load_config(path: Path) -> PanelConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("official") is not False:
        raise ValueError("free judge panel must have official=false")
    return PanelConfig(
        model_ids=tuple(payload["model_ids"]),
        base_url=payload.get("base_url", DEFAULT_BASE_URL),
        timeout_s=float(payload.get("timeout_s", 60.0)),
        retries=int(payload.get("retries", 3)),
        max_concurrency=int(payload.get("max_concurrency", 3)),
        official=False,
    )
