"""Tests for daily iteration: per-day aggregation, deltas, and trends."""

from __future__ import annotations

from datetime import date

import pytest

from qone_life.iteration import _day_of, _trend, daily_iteration
from qone_life.models import MetricSpec, Observation
from qone_life.scoring import _aggregate_scores


def obs(
    domain: str,
    metric: str,
    value: float,
    day: date,
    minimum: float = 0,
    maximum: float = 10,
    source: str = "test",
) -> Observation:
    return Observation(
        observation_id=f"O-{domain}-{metric}-{value}-{day.isoformat()}",
        domain=domain,
        metric=metric,
        value=value,
        minimum=minimum,
        maximum=maximum,
        observed_at=f"{day.isoformat()}T12:00:00Z",
        source=source,
    )


SPECS = (
    MetricSpec(
        domain="health", metric="steps", minimum=0, maximum=20000,
        weight=1.0, target_count=1, direction="higher", unit="steps",
        aggregation="mean",
    ),
    MetricSpec(
        domain="emotion", metric="mood", minimum=1, maximum=5,
        weight=1.0, target_count=1, direction="higher", unit="score",
        aggregation="latest",
    ),
)


def test_day_of_parses_iso_with_z():
    assert _day_of("2026-11-01T08:00:00Z") == date(2026, 11, 1)


def test_day_of_handles_none_and_garbage():
    assert _day_of(None) is None
    assert _day_of("not-a-date") is None


def test_aggregation_mean_is_default():
    """Multiple observations collapse to their normalized average."""
    rows = [obs("health", "steps", 5000, date(2026, 11, 1)),
            obs("health", "steps", 15000, date(2026, 11, 2))]
    spec = SPECS[0]
    assert _aggregate_scores(rows, spec) == pytest.approx(0.5)


def test_aggregation_latest_picks_most_recent():
    rows = [obs("emotion", "mood", 2, date(2026, 11, 1)),
            obs("emotion", "mood", 4, date(2026, 11, 3)),
            obs("emotion", "mood", 3, date(2026, 11, 2))]
    spec = SPECS[1]
    # latest by observed_at → 4/5 = 0.8
    assert _aggregate_scores(rows, spec) == pytest.approx(0.75)


def test_aggregation_max_min():
    rows = [obs("health", "steps", 5000, date(2026, 11, 1)),
            obs("health", "steps", 15000, date(2026, 11, 2))]
    spec = MetricSpec(
        domain="health", metric="steps", minimum=0, maximum=20000,
        direction="higher", aggregation="max",
    )
    assert _aggregate_scores(rows, spec) == pytest.approx(0.75)
    spec = MetricSpec(
        domain="health", metric="steps", minimum=0, maximum=20000,
        direction="higher", aggregation="min",
    )
    assert _aggregate_scores(rows, spec) == pytest.approx(0.25)


def test_aggregation_unknown_raises():
    spec = MetricSpec(
        domain="health", metric="steps", minimum=0, maximum=20000,
        direction="higher", aggregation="median",  # not supported
    )
    rows = [obs("health", "steps", 5000, date(2026, 11, 1))]
    with pytest.raises(ValueError):
        _aggregate_scores(rows, spec)


def test_trend_threshold():
    assert _trend(None) == "none"
    assert _trend(0.0) == "flat"
    assert _trend(0.0005) == "flat"
    assert _trend(0.002) == "up"
    assert _trend(-0.002) == "down"


def test_daily_iteration_empty_observations():
    result = daily_iteration([], SPECS, window_days=7)
    assert result["observations"] == 0
    assert result["days"] == []
    assert result["latest"] == {}
    assert any("no observations" in lim for lim in result["limitations"])


def test_daily_iteration_delta_and_trend():
    """Two days of health observations produce an up trend and correct delta."""
    days = [date(2026, 11, 1), date(2026, 11, 2)]
    observations = [
        obs("health", "steps", 5000, days[0]),
        obs("health", "steps", 15000, days[1]),
    ]
    result = daily_iteration(observations, SPECS, window_days=3)
    assert result["observations"] == 2
    # window anchored to latest day → last entry is day 2
    last = result["days"][-1]
    assert last["date"] == "2026-11-02"
    health = last["dimensions"]["health"]
    assert health["score"] == pytest.approx(0.75)
    assert health["delta"] == pytest.approx(0.5)
    assert health["trend"] == "up"
    # latest mirrors the final day
    assert result["latest"]["health"]["trend"] == "up"


def test_daily_iteration_window_days_must_be_positive():
    with pytest.raises(ValueError):
        daily_iteration([], SPECS, window_days=0)


def test_daily_iteration_respects_direction():
    """A lower-direction metric scores high when the value is low."""
    lower_specs = (
        MetricSpec(
            domain="environment", metric="pm25", minimum=0, maximum=500,
            direction="lower", aggregation="mean",
        ),
    )
    days = [date(2026, 11, 1), date(2026, 11, 2)]
    observations = [
        obs("environment", "pm25", 100, days[0]),
        obs("environment", "pm25", 400, days[1]),
    ]
    result = daily_iteration(observations, lower_specs, window_days=2)
    last = result["days"][-1]
    env = last["dimensions"]["environment"]
    # 1 - 400/500 = 0.2
    assert env["score"] == pytest.approx(0.2)
    # day1 = 0.8, day2 = 0.2 → delta = -0.6 → down
    assert env["delta"] == pytest.approx(-0.6)
    assert env["trend"] == "down"
