"""Daily iteration: aggregate observations per day, compute day-over-day deltas.

Gives the "iterate" loop a real entity: after recording observations for a
window of days, you can ask *how did each domain move* — not just the static
dimension-vector score. This is the minimal honest form of iteration: it does
not fabricate a trend where none is measurable, and it reports coverage so a
missing day is never silently read as "score stayed the same".
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from .models import MetricSpec, Observation
from .scoring import _aggregate_scores


def _day_of(observed_at: str | None) -> date | None:
    if not observed_at:
        return None
    try:
        # Accept ISO with or without timezone suffix; normalize to date.
        return datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _domain_score(rows: list[Observation], specs_by_key: dict[str, MetricSpec]) -> dict[str, Any]:
    """Score one domain over the given day's observations (direction-aware)."""
    by_key: dict[str, list[Observation]] = defaultdict(list)
    for row in rows:
        by_key[f"{row.domain}:{row.metric}"].append(row)

    metrics: dict[str, Any] = {}
    for key, spec in specs_by_key.items():
        if spec.domain != (rows[0].domain if rows else key.split(":")[0]):
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
    weight_total = sum(
        spec.weight
        for spec in specs_by_key.values()
        if spec.domain == rows[0].domain and spec.metric in metrics
    )
    score = sum(
        metrics[m]["score"] * specs_by_key[f"{rows[0].domain}:{m}"].weight
        for m in metrics
    ) / weight_total if weight_total else None
    return {"score": score, "observed_metrics": len(metrics), "metrics": metrics}


def daily_iteration(
    observations: list[Observation],
    specs: tuple[MetricSpec, ...],
    window_days: int = 7,
) -> dict[str, Any]:
    """Compute per-day per-domain scores and day-over-day deltas.

    Returns:
        {
          "window_days": N,
          "days": [ {"date": iso, "dimensions": {domain: {score, observed_metrics,
                       "delta": float|None, "trend": "up"|"down"|"flat"|"none"}}} ... ],
          "latest": {domain: {score, delta, trend, observed_metrics}},
          "observations": count,
          "limitations": [...]
        }
    """
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    specs_by_key: dict[str, MetricSpec] = {spec.key: spec for spec in specs}

    by_day: dict[date, dict[str, list[Observation]]] = defaultdict(lambda: defaultdict(list))
    for obs in observations:
        day = _day_of(obs.observed_at)
        if day is not None:
            by_day[day][obs.domain].append(obs)

    # The most recent day that has any observation anchors the window.
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
    window_dates = [latest_day.toordinal() - offset for offset in range(window_days - 1, -1, -1)]
    window_dates = [date.fromordinal(ordinal) for ordinal in window_dates]

    days_out: list[dict[str, Any]] = []
    previous_by_domain: dict[str, float] = {}

    for day in window_dates:
        dims: dict[str, Any] = {}
        for domain, domain_rows in by_day.get(day, {}).items():
            result = _domain_score(domain_rows, specs_by_key)
            prev = previous_by_domain.get(domain)
            delta = None
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

    latest_dims = days_out[-1]["dimensions"] if days_out else {}
    latest: dict[str, Any] = {}
    for domain, entry in latest_dims.items():
        latest[domain] = {
            "score": entry["score"],
            "delta": entry["delta"],
            "trend": entry["trend"],
            "observed_metrics": entry["observed_metrics"],
        }

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
    if delta is None:
        return "none"
    if delta > 0.001:
        return "up"
    if delta < -0.001:
        return "down"
    return "flat"
