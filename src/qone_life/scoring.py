"""Dimension-vector scoring with explicit coverage and missingness."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import MetricSpec, Observation


def _normalized(value: float, minimum: float, maximum: float) -> float:
    return (value - minimum) / (maximum - minimum)


def _normalized_by_direction(
    value: float, minimum: float, maximum: float, direction: str, target: float | None
) -> float:
    base = _normalized(value, minimum, maximum)
    if direction == "lower":
        return 1 - base
    if direction == "target":
        if target is None:
            return base
        distance = max(target - minimum, maximum - target)
        return max(0.0, 1 - abs(value - target) / distance)
    return base


# Aggregations a metric spec may declare. These are real reduction semantics,
# not decorative labels: the chosen aggregation determines how multiple
# observations of one metric (e.g. across days) collapse into a single score.
AGGREGATIONS = ("mean", "latest", "max", "min")


def _aggregate_scores(rows: list, spec: MetricSpec) -> float:
    """Collapse one metric's in-range observations into a single normalized score.

    ``aggregation`` semantics:
      * mean   — average of the per-observation normalized scores (default)
      * latest — the most recent observation (by observed_at, then seq order)
      * max    — best normalized score observed
      * min    — worst normalized score observed
    """
    if spec.aggregation not in AGGREGATIONS:
        # Defensive: unknown aggregation degrades to mean rather than silently
        # producing a wrong number.
        raise ValueError(f"unsupported aggregation {spec.aggregation!r}")
    if spec.aggregation == "mean":
        return sum(
            _normalized_by_direction(row.value, spec.minimum, spec.maximum, spec.direction, spec.target)
            for row in rows
        ) / len(rows)
    if spec.aggregation == "latest":
        best = max(
            rows,
            key=lambda row: (row.observed_at or "", getattr(row, "seq", 0)),
        )
        return _normalized_by_direction(best.value, spec.minimum, spec.maximum, spec.direction, spec.target)
    scores = [
        _normalized_by_direction(row.value, spec.minimum, spec.maximum, spec.direction, spec.target)
        for row in rows
    ]
    return max(scores) if spec.aggregation == "max" else min(scores)


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
            "direction": spec.direction,
            "unit": spec.unit,
            "aggregation": spec.aggregation,
        }
        if in_range:
            metric_result["score"] = _aggregate_scores(in_range, spec)
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
