"""草稿渲染：所有数字必须来自 results 回执，不允许手写。

占位符格式：``{{num:key}}``，其中 key 支持点号与数组索引（如
``accuracy``、``table[0].score``）。任何无法解析的占位符或裸数字都会
让渲染 fail-closed。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WRITER_SCHEMA = "q-one-draft-render-v1"
NUM_PATTERN = re.compile(r"\{\{num:([A-Za-z0-9_.\[\]-]+)\}\}")
BARE_DIGIT = re.compile(r"(?<![\w{.-])\d+(?:\.\d+)?(?![\w}])")


class WriterError(RuntimeError):
    """草稿渲染无法满足数字绑定约束时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def resolve_value(results: dict[str, Any], key: str) -> Any:
    """解析点号路径与数组索引。"""
    current: Any = results
    for part in key.split("."):
        match = re.match(r"^([A-Za-z0-9_-]+)(?:\[(\d+)\])?$", part)
        if not match:
            raise WriterError(f"invalid results key: {key}")
        name, index = match.group(1), match.group(2)
        if not isinstance(current, dict) or name not in current:
            raise WriterError(f"results key not found: {key}")
        current = current[name]
        if index is not None:
            position = int(index)
            if not isinstance(current, list) or position >= len(current):
                raise WriterError(f"results index out of range: {key}")
            current = current[position]
    if isinstance(current, (dict, list)):
        raise WriterError(f"results key does not resolve to a scalar: {key}")
    return current


def _substitute(text: str, results: dict[str, Any], used: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = resolve_value(results, key)
        used.append(key)
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value)

    return NUM_PATTERN.sub(replace, text)


def _check_no_bare_numbers(text: str, label: str) -> None:
    """拒绝占位符之外的手写数字，避免编造或漂移。"""
    stripped = NUM_PATTERN.sub("", text)
    match = BARE_DIGIT.search(stripped)
    if match:
        raise WriterError(
            f"{label} contains a bare number {match.group(0)!r}; "
            "use a {{num:key}} placeholder bound to results"
        )


def render_draft(
    *,
    title: str,
    question: str,
    hypothesis: dict[str, Any],
    claims: list[dict[str, str]],
    results: dict[str, Any],
    venue: str,
) -> dict[str, Any]:
    """渲染 LaTeX 草稿；返回文本与绑定回执。"""
    if not title.strip():
        raise WriterError("title is empty")
    if not question.strip():
        raise WriterError("question is empty")
    if not claims:
        raise WriterError("at least one claim is required")

    used: list[str] = []
    rendered_claims: list[str] = []
    for claim in claims:
        text = str(claim.get("text") or "")
        if not text.strip():
            raise WriterError("claim text is empty")
        _check_no_bare_numbers(text, f"claim {claim.get('claim_id', '?')}")
        rendered_claims.append(_substitute(text, results, used))

    null_hypothesis = str(hypothesis.get("null_hypothesis") or "").strip()
    alternative = str(hypothesis.get("alternative_hypothesis") or "").strip()
    falsification = str(hypothesis.get("falsification_condition") or "").strip()
    if not (null_hypothesis and alternative and falsification):
        raise WriterError("hypothesis is missing required fields")

    body = [
        r"\documentclass{article}",
        r"\usepackage{booktabs}",
        r"\begin{document}",
        rf"\title{{{title}}}",
        rf"\date{{Venue: {venue}}}",
        r"\maketitle",
        r"\begin{abstract}",
        _substitute(question, results, used),
        r"\end{abstract}",
        r"\section{Introduction}",
        _substitute(question, results, used),
        r"\section{Hypotheses}",
        rf"\textbf{{H0.}} {null_hypothesis}",
        rf"\textbf{{H1.}} {alternative}",
        rf"Falsification condition: {falsification}.",
        r"\section{Results}",
    ]
    for claim, text in zip(claims, rendered_claims):
        body.append(rf"\paragraph{{{claim.get('claim_id', '?')}.}} {text}")
    body.extend([
        r"\section{Limitations}",
        "This draft is generated from a claim ledger and a results receipt; "
        "it does not establish novelty or external validity.",
        r"\section*{Reproducibility}",
        "All numbers are bound to the results receipt by SHA-256.",
        r"\end{document}",
    ])
    text = "\n".join(body) + "\n"
    encoded = text.encode("utf-8")
    return {
        "schema": WRITER_SCHEMA,
        "generated_at": _now(),
        "venue": venue,
        "text": text,
        "draft_sha256": hashlib.sha256(encoded).hexdigest(),
        "numbers_used": sorted(set(used)),
        "results_sha256": hashlib.sha256(
            json.dumps(results, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "claim_count": len(claims),
        "note": "Draft text is generated; novelty is not claimed.",
    }


def write_draft_receipt(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """把草稿文本写入 .tex 并写一份 JSON 回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report["text"], encoding="utf-8")
    receipt_path = path.with_suffix(path.suffix + ".receipt.json")
    receipt_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "draft_path": str(path),
        "draft_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "receipt_path": str(receipt_path),
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }
