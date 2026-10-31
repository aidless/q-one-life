"""Tests for direction-aware next-step suggestions."""

from __future__ import annotations

from datetime import date

import pytest

from qone_life.models import MetricSpec, Observation
from qone_life.suggestion import suggest_improvements


def obs(domain: str, metric: str, value: float, day: date, minimum: float = 0,
        maximum: float = 10) -> Observation:
    return Observation(
        observation_id=f"O-{domain}-{metric}-{value}",
        domain=domain, metric=metric, value=value,
        minimum=minimum, maximum=maximum,
        observed_at=f"{day.isoformat()}T12:00:00Z", source="test",
    )


SPECS = (
    MetricSpec(domain="health", metric="steps", minimum=0, maximum=20000,
               direction="higher", unit="steps"),
    MetricSpec(domain="health", metric="stress", minimum=1, maximum=10,
               direction="lower", unit="score"),
    MetricSpec(domain="emotion", metric="mood", minimum=1, maximum=5,
               direction="higher", unit="score"),
    MetricSpec(domain="environment", metric="heart_rate", minimum=40, maximum=100,
               direction="target", target=65, unit="bpm"),
)


def test_no_observations_gives_empty():
    result = suggest_improvements([], SPECS)
    assert result["count"] == 0
    assert result["domains"] == {}
    # all four metrics lack observations → four limitations
    assert len(result["limitations"]) == 4


def test_higher_metric_below_threshold_suggests_increase():
    observations = [obs("health", "steps", 5000, date(2026, 11, 1))]
    result = suggest_improvements(observations, SPECS, threshold=0.5)
    assert result["count"] == 1
    health = result["domains"]["health"]
    assert health["priority_metric"] == "steps"
    # normalized 5000/20000 = 0.25 < 0.5
    assert health["score"] == pytest.approx(0.25)
    assert "提升" in health["suggestion"]
    assert "steps" in health["suggestion"]


def test_lower_metric_below_threshold_suggests_decrease():
    # stress=9 → normalized 0.1 < 0.5, direction lower
    observations = [obs("health", "stress", 9, date(2026, 11, 1), minimum=1, maximum=10)]
    result = suggest_improvements(observations, SPECS, threshold=0.5)
    health = result["domains"]["health"]
    assert "降低" in health["suggestion"]
    assert health["priority_metric"] == "stress"


def test_high_score_metric_gets_no_suggestion():
    observations = [obs("health", "steps", 19000, date(2026, 11, 1))]
    result = suggest_improvements(observations, SPECS, threshold=0.5)
    # steps normalized 0.95 ≥ 0.5 → no health suggestion
    assert result["count"] == 0


def test_target_metric_suggests_move_toward_target():
    # heart_rate=70, target=65 → distance 5/35 ≈ 0.857 ≥ 0.5 → no suggestion
    obs_high = [obs("environment", "heart_rate", 70, date(2026, 11, 1), minimum=40, maximum=100)]
    result = suggest_improvements(obs_high, SPECS, threshold=0.5)
    assert result["count"] == 0
    # heart_rate=90 → distance 25/35 ≈ 0.286 < 0.5 → suggestion
    obs_low = [obs("environment", "heart_rate", 90, date(2026, 11, 1), minimum=40, maximum=100)]
    result = suggest_improvements(obs_low, SPECS, threshold=0.5)
    assert result["count"] == 1
    assert result["domains"]["environment"]["priority_metric"] == "heart_rate"
    assert "65" in result["domains"]["environment"]["suggestion"]


def test_latest_observation_wins():
    observations = [
        obs("health", "steps", 5000, date(2026, 11, 1)),
        obs("health", "steps", 19000, date(2026, 11, 2)),
    ]
    result = suggest_improvements(observations, SPECS, threshold=0.5)
    assert result["count"] == 0  # latest is high


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        suggest_improvements([], SPECS, threshold=1.5)
    with pytest.raises(ValueError):
        suggest_improvements([], SPECS, threshold=-0.1)


def test_unknown_metric_ignored():
    observations = [obs("health", "nonsense", 1, date(2026, 11, 1))]
    result = suggest_improvements(observations, SPECS)
    assert result["count"] == 0
    assert len(result["limitations"]) == 4  # all real metrics lack observations
