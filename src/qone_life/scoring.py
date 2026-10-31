"""带显式覆盖率与缺失标记的维度向量打分。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import MetricSpec, Observation


def _normalized(value: float, minimum: float, maximum: float) -> float:
    """把数值线性归一化到 0~1（不做截断）。"""
    return (value - minimum) / (maximum - minimum)


def _normalized_by_direction(
    value: float, minimum: float, maximum: float, direction: str, target: float | None
) -> float:
    """按指标方向做归一化。

    - higher：越大越好，直接用线性归一化；
    - lower：越小越好，取反（1 - 归一化值）；
    - target：越靠近目标越好，按到目标点的距离折算，最近为 1、最远为 0。
    """
    base = _normalized(value, minimum, maximum)
    if direction == "lower":
        return 1 - base
    if direction == "target":
        if target is None:
            return base
        distance = max(target - minimum, maximum - target)
        return max(0.0, 1 - abs(value - target) / distance)
    return base


# 指标规格可声明的聚合方式。这是真实的归约语义，而不是装饰性标签：
# 同一条指标的多次观测（比如跨天）要折叠成一个分值时，用哪种方式由它决定。
AGGREGATIONS = ("mean", "latest", "max", "min")


def _aggregate_scores(rows: list, spec: MetricSpec) -> float:
    """把某指标落在区间内的多次观测折叠成一个归一化得分。

    aggregation 语义：
      * mean   —— 各次观测归一化得分的平均值（默认）；
      * latest —— 按 observed_at（再按 seq）取最新的一次；
      * max    —— 观测到的最高归一化得分；
      * min    —— 观测到的最低归一化得分。
    """
    if spec.aggregation not in AGGREGATIONS:
        # 防御：未知聚合方式直接报错，而不是静默算出一个错的数。
        raise ValueError(f"unsupported aggregation {spec.aggregation!r}")

    if spec.aggregation == "mean":
        total = 0.0
        for row in rows:
            total += _normalized_by_direction(
                row.value, spec.minimum, spec.maximum, spec.direction, spec.target
            )
        return total / len(rows)

    if spec.aggregation == "latest":
        best = max(
            rows,
            key=lambda row: (row.observed_at or "", getattr(row, "seq", 0)),
        )
        return _normalized_by_direction(
            best.value, spec.minimum, spec.maximum, spec.direction, spec.target
        )

    # max / min：先算出每一条的归一化得分，再取最高或最低。
    scores = []
    for row in rows:
        scores.append(
            _normalized_by_direction(
                row.value, spec.minimum, spec.maximum, spec.direction, spec.target
            )
        )
    if spec.aggregation == "max":
        return max(scores)
    return min(scores)


def score_observations(
    observations: list[Observation],
    specs: tuple[MetricSpec, ...],
) -> dict[str, Any]:
    """对观测按指标规格打分，返回按域分组的维度向量。

    每个指标只统计落在 [minimum, maximum] 内的观测；区间外的观测计入限制说明，
    不参与打分。没有区间内观测的指标得分为 None（保持未知，不猜值）。
    """
    by_key: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        by_key[f"{observation.domain}:{observation.metric}"].append(observation)

    dimensions: dict[str, dict[str, Any]] = {}
    limitations: list[str] = []

    for spec in specs:
        key = spec.key
        rows = by_key.get(key, [])

        # 先筛出区间内的观测，并记录被排除的区间外观测数量。
        in_range = []
        for row in rows:
            if spec.minimum <= row.value <= spec.maximum:
                in_range.append(row)
        out_of_range = len(rows) - len(in_range)
        if out_of_range:
            limitations.append(f"{key}: {out_of_range} observation(s) outside the metric spec")

        # 取区间内观测里最新的时间戳作为该指标的观测时间（无观测则为 None）。
        latest_observed_at = None
        for row in in_range:
            if latest_observed_at is None or row.observed_at > latest_observed_at:
                latest_observed_at = row.observed_at

        metric_result: dict[str, Any] = {
            "score": None,
            "n": len(in_range),
            "target_count": spec.target_count,
            "coverage": min(1.0, len(in_range) / spec.target_count),
            "observed_at": latest_observed_at,
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

    # 计算每个域的加权平均分（只对有得分的指标加权）与覆盖率。
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
