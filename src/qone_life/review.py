"""回顾摘要：各维度彼此独立，并显式暴露数据缺失情况。"""

from __future__ import annotations

from typing import Any


def build_review(score_report: dict[str, Any]) -> dict[str, Any]:
    """根据打分报告生成回顾提示，指出需要注意的维度。

    对每个维度检查两件事：
    - 覆盖率小于 1：说明声明指标集中有一部分没有观测到；
    - 得分为空：说明没有任何落在区间内的观测。
    这两类情况都写入 attention，让使用者知道哪里数据不全，而不是替用户猜一个值。
    """
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
