"""Dimension-vector scoring with explicit coverage and missingness."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import MetricSpec, Observation


def _normalized(value: float, minimum: float, maximum: float) -> float:
    return (value - minimum) / (maximum - minimum)


def score_observations(
    observations: list[Observation],
    specs: tuple[MetricSpec, ...],
) -> dict[str, Any]:
    by_key: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        by_key[f"{observation.domain}:{observation.metric}"].append(observation)

    dimensions: dict[str, dict[str, Any]] = {}
    limitations: list[str] = []
    for spec in specs:
        key = spec.key
        rows = by_key.get(key, [])
        in_range = [row for row in rows if spec.minimum <= row.value <= spec.maximum]
        out_of_range = len(rows) - len(in_range)
        if out_of_range:
            limitations.append(f"{key}: {out_of_range} observation(s) outside the metric spec")
        metric_result: dict[str, Any] = {
            "score": None,
            "n": len(in_range),
            "target_count": spec.target_count,
            "coverage": min(1.0, len(in_range) / spec.target_count),
            "observed_at": max((row.observed_at for row in in_range), default=None),
        }
        if in_range:
            values = [_normalized(row.value, spec.minimum, spec.maximum) for row in in_range]
            metric_result["score"] = sum(values) / len(values)
        domain = dimensions.setdefault(
            spec.domain,
            {"score": None, "observed_metrics": 0, "expected_metrics": 0, "coverage": 0.0, "metrics": {}},
        )
        domain["metrics"][spec.metric] = metric_result
        domain["expected_metrics"] += 1
        domain["observed_metrics"] += bool(in_range)

    for domain_name, domain in dimensions.items():
        metric_scores = []
        weight_total = 0.0
        for spec in specs:
            if spec.domain != domain_name:
                continue
            metric_score = domain["metrics"][spec.metric]["score"]
            if metric_score is not None:
                metric_scores.append((metric_score, spec.weight))
                weight_total += spec.weight
        if metric_scores:
            domain["score"] = sum(score * weight for score, weight in metric_scores) / weight_total
        domain["coverage"] = domain["observed_metrics"] / domain["expected_metrics"]

    return {
        "score_type": "dimension_vector",
        "dimensions": dimensions,
        "global_score": None,
        "observations": len(observations),
        "limitations": limitations
        + [
            "scores are normalized user-defined dimensions, not a measure of human worth",
            "no global score is produced; dimensions remain separate",
        ],
    }
