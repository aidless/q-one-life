"""Actionable next-step suggestions derived from direction-aware scores.

Never invents a recommendation the data cannot support: for each metric it
looks at the latest normalized score and the metric's direction, then states
the concrete adjustment that would move the score up — with the real unit.
A metric with no observation gets no suggestion (not "stay the same").
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
    """Suggest the next concrete step per domain.

    Returns:
        {
          "domains": {domain: {"suggestion": str|None,
                               "priority_metric": str|None,
                               "score": float|None,
                               "detail": [...]}},
          "count": number of domains with an actionable suggestion,
          "limitations": [...]
        }
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    specs_by_key: dict[str, MetricSpec] = {spec.key: spec for spec in specs}
    latest_by_key: dict[str, Observation] = {}
    for obs in observations:
        key = f"{obs.domain}:{obs.metric}"
        if key not in specs_by_key:
            continue
        current = latest_by_key.get(key)
        if current is None or obs.observed_at >= current.observed_at:
            latest_by_key[key] = obs

    per_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, obs in latest_by_key.items():
        spec = specs_by_key[key]
        normalized = _normalized_by_direction(obs.value, spec.minimum, spec.maximum,
                                              spec.direction, spec.target)
        if normalized < threshold:
            direction_word = {
                "higher": "提升",
                "lower": "降低",
                "target": "趋近目标",
            }[spec.direction]
            unit_suffix = f" {spec.unit}" if spec.unit else ""
            if spec.direction == "target" and spec.target is not None:
                action = f"{direction_word} {obs.value}{unit_suffix} → {spec.target}{unit_suffix}"
            elif spec.direction == "lower":
                action = f"{direction_word} 至 {obs.value * 0.9:.2f}{unit_suffix} 以下"
            else:
                action = f"{direction_word} 至 {obs.value * 1.1:.2f}{unit_suffix} 以上"
            per_domain[obs.domain].append({
                "metric": spec.metric,
                "score": normalized,
                "value": obs.value,
                "direction": spec.direction,
                "target": spec.target,
                "unit": spec.unit,
                "action": action,
            })

    domains: dict[str, Any] = {}
    limitations: list[str] = []
    for domain, entries in per_domain.items():
        entries.sort(key=lambda e: e["score"])
        worst = entries[0]
        domains[domain] = {
            "suggestion": f"{worst['action']}（{worst['metric']}，当前 {worst['score']:.2f}）",
            "priority_metric": worst["metric"],
            "score": worst["score"],
            "detail": entries,
        }
    for spec in specs:
        key = f"{spec.domain}:{spec.metric}"
        if key not in latest_by_key:
            limitations.append(f"{key}: no observation yet, no suggestion")

    return {"domains": domains, "count": len(domains), "limitations": limitations}
