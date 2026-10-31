"""根据方向感知的打分，给出可执行的下一步建议。

不凭空给出数据支撑不了的推荐：对每个指标先看最新一次的方向归一化得分和它的方向，
再给出能把得分抬高（或压向目标）的具体调整幅度，并带上真实单位。
没有观测的指标不给建议（而不是建议“保持不变”）。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import MetricSpec, Observation
from .scoring import _normalized_by_direction


def suggest_improvements(
    observations: list[Observation],
    specs: tuple[MetricSpec, ...],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """为每个域给出下一步的具体改进建议。

    只考虑归一化得分低于 threshold 的指标；每个域取最差的那个，
    并附上该域所有待改进指标的明细。

    返回结构：
    {
      "domains": {域: {"suggestion": 文本或 None,
                       "priority_metric": 指标名或 None,
                       "score": 得分或 None,
                       "detail": [...]}},
      "count": 有可执行建议的域数量,
      "limitations": [...]
    }
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    # 先按 "域:指标" 建立索引，方便后面按指标查找规格与最新观测。
    specs_by_key: dict[str, MetricSpec] = {spec.key: spec for spec in specs}

    latest_by_key: dict[str, Observation] = {}
    for obs in observations:
        key = f"{obs.domain}:{obs.metric}"
        # 规格里没有这个指标就跳过，避免把无关观测算进来。
        if key not in specs_by_key:
            continue
        current = latest_by_key.get(key)
        if current is None or obs.observed_at >= current.observed_at:
            latest_by_key[key] = obs

    # 逐个指标判断是否需要改进，并按其所属域分组。
    per_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, obs in latest_by_key.items():
        spec = specs_by_key[key]
        normalized = _normalized_by_direction(
            obs.value, spec.minimum, spec.maximum, spec.direction, spec.target
        )
        if normalized < threshold:
            direction_word = {
                "higher": "提升",
                "lower": "降低",
                "target": "趋近目标",
            }[spec.direction]
            unit_suffix = f" {spec.unit}" if spec.unit else ""

            # 按方向给出具体的目标幅度：目标型距目标、降型压到 9 成、升型提到 1.1 倍。
            if spec.direction == "target" and spec.target is not None:
                action = f"{direction_word} {obs.value}{unit_suffix} → {spec.target}{unit_suffix}"
            elif spec.direction == "lower":
                action = f"{direction_word} 至 {obs.value * 0.9:.2f}{unit_suffix} 以下"
            else:
                action = f"{direction_word} 至 {obs.value * 1.1:.2f}{unit_suffix} 以上"

            per_domain[obs.domain].append(
                {
                    "metric": spec.metric,
                    "score": normalized,
                    "value": obs.value,
                    "direction": spec.direction,
                    "target": spec.target,
                    "unit": spec.unit,
                    "action": action,
                }
            )

    # 每个域保留得分最低（最该先做）的那条作为主建议。
    domains: dict[str, Any] = {}
    for domain, entries in per_domain.items():
        entries.sort(key=lambda e: e["score"])
        worst = entries[0]
        domains[domain] = {
            "suggestion": f"{worst['action']}（{worst['metric']}，当前 {worst['score']:.2f}）",
            "priority_metric": worst["metric"],
            "score": worst["score"],
            "detail": entries,
        }

    # 完全没有观测的指标写进限制说明，而不是被静默忽略。
    limitations: list[str] = []
    for spec in specs:
        key = f"{spec.domain}:{spec.metric}"
        if key not in latest_by_key:
            limitations.append(f"{key}: no observation yet, no suggestion")

    return {"domains": domains, "count": len(domains), "limitations": limitations}
