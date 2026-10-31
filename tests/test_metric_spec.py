"""MetricSpec model and direction-aware scoring unit tests."""
import unittest

from qone_life.models import LifeValidationError, MetricSpec, Observation, load_metric_specs
from qone_life.scoring import score_observations


def make_observation(value: float, domain: str = "energy", metric: str = "sleep_quality",
                     observed_at: str = "2026-01-01T00:00:00Z") -> Observation:
    return Observation.from_payload({
        "domain": domain, "metric": metric, "value": value,
        "minimum": 0, "maximum": 10, "observed_at": observed_at, "source": "unit-test",
    })


class MetricSpecModelTests(unittest.TestCase):
    def test_defaults_higher_mean(self):
        spec = MetricSpec.from_dict({"domain": "energy", "metric": "sleep_quality",
                                     "minimum": 0, "maximum": 10})
        self.assertEqual(spec.direction, "higher")
        self.assertEqual(spec.unit, "")
        self.assertEqual(spec.aggregation, "mean")
        self.assertIsNone(spec.target)

    def test_explicit_direction_unit_aggregation(self):
        spec = MetricSpec.from_dict({"domain": "finance", "metric": "spend", "minimum": 0,
                                     "maximum": 1000, "direction": "lower", "unit": "CNY",
                                     "aggregation": "mean"})
        self.assertEqual(spec.direction, "lower")
        self.assertEqual(spec.unit, "CNY")
        self.assertEqual(spec.aggregation, "mean")

    def test_target_direction_requires_target_in_bounds(self):
        with self.assertRaises(LifeValidationError):
            MetricSpec.from_dict({"domain": "emotion", "metric": "mood", "minimum": 0,
                                  "maximum": 10, "direction": "target"})
        spec = MetricSpec.from_dict({"domain": "emotion", "metric": "mood", "minimum": 0,
                                     "maximum": 10, "direction": "target", "target": 5})
        self.assertEqual(spec.target, 5.0)

    def test_target_outside_bounds_rejected(self):
        with self.assertRaises(LifeValidationError):
            MetricSpec.from_dict({"domain": "emotion", "metric": "mood", "minimum": 0,
                                  "maximum": 10, "direction": "target", "target": 11})

    def test_invalid_direction_rejected(self):
        with self.assertRaises(LifeValidationError):
            MetricSpec.from_dict({"domain": "energy", "metric": "sleep_quality",
                                  "minimum": 0, "maximum": 10, "direction": "sideways"})

    def test_non_target_direction_ignores_target(self):
        spec = MetricSpec.from_dict({"domain": "energy", "metric": "sleep_quality",
                                     "minimum": 0, "maximum": 10, "target": 5})
        self.assertIsNone(spec.target)

    def test_load_metric_specs_unique_keys(self):
        with self.assertRaises(LifeValidationError):
            load_metric_specs([
                {"domain": "energy", "metric": "sleep_quality", "minimum": 0, "maximum": 10},
                {"domain": "energy", "metric": "sleep_quality", "minimum": 0, "maximum": 10},
            ])


class DirectionAwareScoringTests(unittest.TestCase):
    def test_higher_normalized(self):
        specs = (MetricSpec.from_dict({"domain": "energy", "metric": "m", "minimum": 0,
                                       "maximum": 10, "direction": "higher"}),)
        report = score_observations([make_observation(8, "energy", "m")], specs)
        score = report["dimensions"]["energy"]["metrics"]["m"]["score"]
        self.assertAlmostEqual(score, 0.8)

    def test_lower_inverts_normalization(self):
        specs = (MetricSpec.from_dict({"domain": "finance", "metric": "spend", "minimum": 0,
                                       "maximum": 10, "direction": "lower"}),)
        report = score_observations([make_observation(2, "finance", "spend")], specs)
        score = report["dimensions"]["finance"]["metrics"]["spend"]["score"]
        self.assertAlmostEqual(score, 0.8)

    def test_target_distance_scoring(self):
        specs = (MetricSpec.from_dict({"domain": "emotion", "metric": "mood", "minimum": 0,
                                       "maximum": 10, "direction": "target", "target": 5}),)
        report = score_observations([make_observation(5, "emotion", "mood")], specs)
        score = report["dimensions"]["emotion"]["metrics"]["mood"]["score"]
        self.assertAlmostEqual(score, 1.0)

    def test_target_distance_half_scale(self):
        # target=5, range 0-10 => distance=5; value=0 => 1 - |0-5|/5 = 0
        specs = (MetricSpec.from_dict({"domain": "emotion", "metric": "mood", "minimum": 0,
                                       "maximum": 10, "direction": "target", "target": 5}),)
        report = score_observations([make_observation(0, "emotion", "mood")], specs)
        score = report["dimensions"]["emotion"]["metrics"]["mood"]["score"]
        self.assertAlmostEqual(score, 0.0)

    def test_reports_direction_unit_aggregation(self):
        specs = (MetricSpec.from_dict({"domain": "finance", "metric": "spend", "minimum": 0,
                                       "maximum": 10, "direction": "lower", "unit": "CNY",
                                       "aggregation": "mean"}),)
        report = score_observations([make_observation(5, "finance", "spend")], specs)
        m = report["dimensions"]["finance"]["metrics"]["spend"]
        self.assertEqual(m["direction"], "lower")
        self.assertEqual(m["unit"], "CNY")
        self.assertEqual(m["aggregation"], "mean")


if __name__ == "__main__":
    unittest.main()
