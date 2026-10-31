"""经过校验的个人观测与用户自定义的指标规格。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from secrets import token_hex
from typing import Any


class LifeValidationError(ValueError):
    """本地观测或指标规格不合法时抛出。"""


def utc_now() -> str:
    """当前 UTC 时间，精确到秒、以 Z 结尾。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_observation_id() -> str:
    """生成一个新的观测 id，形如 O-20261031-ab12cd。"""
    return f"O-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(3)}"


@dataclass(frozen=True)
class Observation:
    """一条不可变的观测记录。"""

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
    confidence: float | None = None
    corrected_by: str | None = None

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> Observation:
        """从 dict 构造并逐项校验，任何不合法都抛 LifeValidationError。"""
        if not isinstance(raw, dict):
            raise LifeValidationError("observation must be an object")

        # 必填的文本字段：必须是非空字符串。
        required_text = ("domain", "metric", "observed_at", "source")
        for key in required_text:
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise LifeValidationError("domain, metric, observed_at, and source are required")

        value = raw.get("value")
        minimum = raw.get("minimum")
        maximum = raw.get("maximum")

        # 数值字段：先统一检查类型（排除布尔——Python 里 bool 是 int 的子类），
        # 再统一检查是否有限，保持与逐项校验一致的报错先后顺序。
        for item in (value, minimum, maximum):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise LifeValidationError("value, minimum, and maximum must be numbers")
        for item in (value, minimum, maximum):
            if not isfinite(float(item)):
                raise LifeValidationError("value, minimum, and maximum must be finite")

        # 区间必须非空，且取值落在区间内。
        if maximum <= minimum or value < minimum or value > maximum:
            raise LifeValidationError("value must be within a non-empty minimum/maximum range")

        observation_id = raw.get("observation_id") or new_observation_id()
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise LifeValidationError("observation_id must be a non-empty string")

        decision_id = raw.get("decision_id")
        if decision_id is not None and (not isinstance(decision_id, str) or not decision_id.strip()):
            raise LifeValidationError("decision_id must be a non-empty string when provided")

        confidence = raw.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise LifeValidationError("confidence must be between 0 and 1 when provided")
            if not (0 <= float(confidence) <= 1):
                raise LifeValidationError("confidence must be between 0 and 1 when provided")
            confidence = float(confidence)

        corrected_by = raw.get("corrected_by")
        if corrected_by is not None and (not isinstance(corrected_by, str) or not corrected_by.strip()):
            raise LifeValidationError("corrected_by must be a non-empty string when provided")

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
            confidence=confidence,
            corrected_by=corrected_by.strip() if corrected_by else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """导出为普通 dict（与 from_payload 的字段一一对应）。"""
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
            "confidence": self.confidence,
            "corrected_by": self.corrected_by,
        }


@dataclass(frozen=True)
class MetricSpec:
    """一条不可变的指标规格：定义取值区间、权重、方向等打分口径。"""

    domain: str
    metric: str
    minimum: float
    maximum: float
    weight: float = 1.0
    target_count: int = 1
    direction: str = "higher"
    unit: str = ""
    aggregation: str = "mean"
    target: float | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MetricSpec:
        """从 dict 构造并逐项校验指标规格。"""
        if not isinstance(raw, dict):
            raise LifeValidationError("metric specification must be an object")

        domain = raw.get("domain")
        metric = raw.get("metric")
        if not isinstance(domain, str) or not domain.strip():
            raise LifeValidationError("metric spec domain and metric are required")
        if not isinstance(metric, str) or not metric.strip():
            raise LifeValidationError("metric spec domain and metric are required")

        minimum = raw.get("minimum")
        maximum = raw.get("maximum")
        weight = raw.get("weight", 1.0)
        target_count = raw.get("target_count", 1)
        direction = raw.get("direction", "higher")
        unit = raw.get("unit", "")
        aggregation = raw.get("aggregation", "mean")

        # 边界与权重必须是数（同样排除布尔）。
        for item in (minimum, maximum, weight):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise LifeValidationError("metric bounds and weight must be numbers")

        if maximum <= minimum:
            raise LifeValidationError("metric spec bounds, weight, and target_count are invalid")
        if weight <= 0:
            raise LifeValidationError("metric spec bounds, weight, and target_count are invalid")
        if isinstance(target_count, bool) or not isinstance(target_count, int) or target_count < 1:
            raise LifeValidationError("metric spec bounds, weight, and target_count are invalid")

        if direction not in {"higher", "lower", "target"}:
            raise LifeValidationError("metric spec direction must be higher, lower, or target")
        if not isinstance(unit, str) or not isinstance(aggregation, str):
            raise LifeValidationError("metric spec unit and aggregation must be strings")

        target = raw.get("target")
        if direction == "target":
            # 目标型必须给出落在开区间内的目标值。
            if isinstance(target, bool) or not isinstance(target, (int, float)):
                raise LifeValidationError("target-direction metric spec requires a target within the bounds")
            if not (minimum < float(target) < maximum):
                raise LifeValidationError("target-direction metric spec requires a target within the bounds")
            target = float(target)
        elif target is not None:
            # 非目标型忽略传入的 target，统一置空。
            target = None

        return cls(
            domain.strip(),
            metric.strip(),
            float(minimum),
            float(maximum),
            float(weight),
            target_count,
            direction,
            unit.strip() if unit else "",
            aggregation,
            target,
        )

    @property
    def key(self) -> str:
        """指标的稳定唯一键：域:指标。"""
        return f"{self.domain}:{self.metric}"


def load_metric_specs(raw: Any) -> tuple[MetricSpec, ...]:
    """把原始列表转成指标规格元组，并校验 key 不重复。"""
    if not isinstance(raw, list) or not raw:
        raise LifeValidationError("metric specs must be a non-empty list")

    specs = tuple(MetricSpec.from_dict(item) for item in raw)
    unique_keys = {spec.key for spec in specs}
    if len(unique_keys) != len(specs):
        raise LifeValidationError("metric spec keys must be unique")
    return specs
