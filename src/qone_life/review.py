"""Review summaries that keep dimensions separate and expose missingness."""

from __future__ import annotations

from typing import Any


def build_review(score_report: dict[str, Any]) -> dict[str, Any]:
    attention: list[str] = []
    for domain, result in score_report.get("dimensions", {}).items():
        if result.get("coverage", 0) < 1:
            attention.append(f"{domain}: missing observations for part of the declared metric set")
        if result.get("score") is None:
            attention.append(f"{domain}: no in-range observation is available")
    if not score_report.get("observations"):
        attention.append("no observations recorded")
    return {
        "kind": "review_prompt",
        "dimensions": score_report.get("dimensions", {}),
        "attention": attention,
        "questions": [
            "Which metric was easiest to observe consistently?",
            "Which metric definition needs revision before the next review window?",
            "Which missing or partial observations should remain unknown instead of being guessed?",
        ],
        "limitations": score_report.get("limitations", []),
    }
