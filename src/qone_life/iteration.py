"""按天迭代：把观测按天聚合，计算逐日环比变化。

给"迭代"循环一个真实对象：记录若干天的观测后，可以回答"每个维度怎么移动了"，
而不只是静态的维度向量打分。这是最小且诚实的迭代形式：measurable 不出趋势时不虚构趋势，
并报告覆盖率，避免把"缺了一天"误读成"分数没变"。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import MetricSpec, Observation
from .scoring import _aggregate_scores


def _day_of(observed_at: str | None) -> date | None:
    """把观测时间解析成日期；无法解析时返回 None。"""
    if not observed_at:
        return None
    try:
        # 兼容带或不带时区后缀的 ISO 时间，统一归一化到日期。
        return datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _domain_score(rows: list[Observation], specs_by_key: dict[str, MetricSpec]) -> dict[str, Any]:
    """对某一天某个域的观测打分（方向感知）。"""
    by_key: dict[str, list[Observation]] = defaultdict(list)
    for row in rows:
        by_key[f"{row.domain}:{row.metric}"].append(row)

    metrics: dict[str, Any] = {}
    for key, spec in specs_by_key.items():
        # 当天只有一个域的观测，用它确定当前域；无观测时从 key 前缀推断。
        current_domain = rows[0].domain if rows else key.split(":")[0]
        if spec.domain != current_domain:
            continue
        in_range = [r for r in by_key.get(key, []) if spec.minimum <= r.value <= spec.maximum]
        if not in_range:
            continue
        metrics[spec.metric] = {
            "score": _aggregate_scores(in_range, spec),
            "n": len(in_range),
            "direction": spec.direction,
            "unit": spec.unit,
        }

    if not metrics:
        return {"score": None, "observed_metrics": 0, "metrics": {}}

    # 只用"当天有得分"的指标算加权平均，避免把缺失指标按 0 计。
    weight_total = 0.0
    weighted_sum = 0.0
    for m, value in metrics.items():
        weight = specs_by_key[f"{rows[0].domain}:{m}"].weight
        weighted_sum += value["score"] * weight
        weight_total += weight

    score = weighted_sum / weight_total if weight_total else None
    return {"score": score, "observed_metrics": len(metrics), "metrics": metrics}


def daily_iteration(
    observations: list[Observation],
    specs: tuple[MetricSpec, ...],
    window_days: int = 7,
) -> dict[str, Any]:
    """计算逐日、逐域得分及逐日环比变化。

    返回结构：
    {
      "window_days": N,
      "days": [ {"date": iso, "dimensions": {域: {score, observed_metrics,
                   "delta": float|None, "trend": "up"|"down"|"flat"|"none"}}} ... ],
      "latest": {域: {score, delta, trend, observed_metrics}},
      "observations": 观测总数,
      "limitations": [...]
    }
    """
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    specs_by_key: dict[str, MetricSpec] = {spec.key: spec for spec in specs}

    # 先按"天 → 域 → 观测列表"分组。
    by_day: dict[date, dict[str, list[Observation]]] = defaultdict(lambda: defaultdict(list))
    for obs in observations:
        day = _day_of(obs.observed_at)
        if day is not None:
            by_day[day][obs.domain].append(obs)

    # 有观测的最新一天作为窗口终点。
    active_days = sorted(by_day.keys())
    if not active_days:
        return {
            "window_days": window_days,
            "days": [],
            "latest": {},
            "observations": 0,
            "limitations": ["no observations with a parseable observed_at date"],
        }

    latest_day = active_days[-1]
    window_dates = []
    for offset in range(window_days - 1, -1, -1):
        window_dates.append(date.fromordinal(latest_day.toordinal() - offset))

    days_out: list[dict[str, Any]] = []
    previous_by_domain: dict[str, float] = {}

    for day in window_dates:
        dims: dict[str, Any] = {}
        for domain, domain_rows in by_day.get(day, {}).items():
            result = _domain_score(domain_rows, specs_by_key)

            # 环比：当天有得分且前一天也有得分时，才算 delta。
            delta = None
            prev = previous_by_domain.get(domain)
            if result["score"] is not None and prev is not None:
                delta = result["score"] - prev
            trend = _trend(delta)

            dims[domain] = {
                "score": result["score"],
                "observed_metrics": result["observed_metrics"],
                "delta": delta,
                "trend": trend,
                "metrics": result["metrics"],
            }
            if result["score"] is not None:
                previous_by_domain[domain] = result["score"]
        days_out.append({"date": day.isoformat(), "dimensions": dims})

    # 最新一天的得分单独抽出来，方便直接读取。
    latest_dims = days_out[-1]["dimensions"] if days_out else {}
    latest: dict[str, Any] = {}
    for domain, entry in latest_dims.items():
        latest[domain] = {
            "score": entry["score"],
            "delta": entry["delta"],
            "trend": entry["trend"],
            "observed_metrics": entry["observed_metrics"],
        }

    # 某天某域完全没有可打分观测时，写进限制说明，不当作"分数没变"。
    limitations = []
    for day_entry in days_out:
        empty = [d for d, v in day_entry["dimensions"].items() if v["score"] is None]
        if empty:
            limitations.append(f"{day_entry['date']}: no scored observations in {len(empty)} domain(s)")

    return {
        "window_days": window_days,
        "days": days_out,
        "latest": latest,
        "observations": len(observations),
        "limitations": limitations,
    }


def _trend(delta: float | None) -> str:
    """把环比数值映射成方向标签；阈值 0.001 用来吸收浮点噪声。"""
    if delta is None:
        return "none"
    if delta > 0.001:
        return "up"
    if delta < -0.001:
        return "down"
    return "flat"
