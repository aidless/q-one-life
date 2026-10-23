"""Validated personal observations and user-defined metric specifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from secrets import token_hex
from typing import Any


class LifeValidationError(ValueError):
    """Raised when a local observation or metric specification is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_observation_id() -> str:
    return f"O-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(3)}"


@dataclass(frozen=True)
class Observation:
    observation_id: str
    domain: str
    metric: str
    value: float
    minimum: float
    maximum: float
    observed_at: str
    source: str
    note: str = ""
    decision_id: str | None = None

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "Observation":
        if not isinstance(raw, dict):
            raise LifeValidationError("observation must be an object")
        required_text = ("domain", "metric", "observed_at", "source")
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required_text):
            raise LifeValidationError("domain, metric, observed_at, and source are required")
        value = raw.get("value")
        minimum = raw.get("minimum")
        maximum = raw.get("maximum")
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in (value, minimum, maximum)):
            raise LifeValidationError("value, minimum, and maximum must be numbers")
        if not all(isfinite(float(item)) for item in (value, minimum, maximum)):
            raise LifeValidationError("value, minimum, and maximum must be finite")
        if maximum <= minimum or value < minimum or value > maximum:
            raise LifeValidationError("value must be within a non-empty minimum/maximum range")
        observation_id = raw.get("observation_id") or new_observation_id()
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise LifeValidationError("observation_id must be a non-empty string")
        decision_id = raw.get("decision_id")
        if decision_id is not None and (not isinstance(decision_id, str) or not decision_id.strip()):
            raise LifeValidationError("decision_id must be a non-empty string when provided")
        return cls(
            observation_id=observation_id,
            domain=raw["domain"].strip(),
            metric=raw["metric"].strip(),
            value=float(value),
            minimum=float(minimum),
            maximum=float(maximum),
            observed_at=raw["observed_at"].strip(),
            source=raw["source"].strip(),
            note=str(raw.get("note", "")),
            decision_id=decision_id.strip() if decision_id else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "domain": self.domain,
            "metric": self.metric,
            "value": self.value,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "observed_at": self.observed_at,
            "source": self.source,
            "note": self.note,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class MetricSpec:
    domain: str
    metric: str
    minimum: float
    maximum: float
    weight: float = 1.0
    target_count: int = 1

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MetricSpec":
        if not isinstance(raw, dict):
            raise LifeValidationError("metric specification must be an object")
        domain = raw.get("domain")
        metric = raw.get("metric")
        if not isinstance(domain, str) or not domain.strip() or not isinstance(metric, str) or not metric.strip():
            raise LifeValidationError("metric spec domain and metric are required")
        minimum = raw.get("minimum")
        maximum = raw.get("maximum")
        weight = raw.get("weight", 1.0)
        target_count = raw.get("target_count", 1)
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in (minimum, maximum, weight)):
            raise LifeValidationError("metric bounds and weight must be numbers")
        if maximum <= minimum or weight <= 0 or isinstance(target_count, bool) or not isinstance(target_count, int) or target_count < 1:
            raise LifeValidationError("metric spec bounds, weight, and target_count are invalid")
        return cls(domain.strip(), metric.strip(), float(minimum), float(maximum), float(weight), target_count)

    @property
    def key(self) -> str:
        return f"{self.domain}:{self.metric}"


def load_metric_specs(raw: Any) -> tuple[MetricSpec, ...]:
    if not isinstance(raw, list) or not raw:
        raise LifeValidationError("metric specs must be a non-empty list")
    specs = tuple(MetricSpec.from_dict(item) for item in raw)
    if len({spec.key for spec in specs}) != len(specs):
        raise LifeValidationError("metric spec keys must be unique")
    return specs
