import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.outcome_predictor import (
    PredictorError,
    screen_plans,
    write_screen_report,
)


PLANS = [
    {"plan_id": "p1", "lr": 1e-3},
    {"plan_id": "p2", "lr": 1e-4},
    {"plan_id": "p3", "lr": 1e-5},
]


class ScreenTests(unittest.TestCase):
    def test_selects_top_predicted(self):
        predictions = {
            "p1": {"predicted": {"score": 0.8}, "confidence": 0.9},
            "p2": {"predicted": {"score": 0.95}, "confidence": 0.9},
            "p3": {"predicted": {"score": 0.7}, "confidence": 0.9},
        }
        report = screen_plans(PLANS, lambda plan: predictions[plan["plan_id"]], top_k=2)
        self.assertEqual(report["selected"], ["p2", "p1"])
        self.assertEqual(report["must_run"], [])
        self.assertEqual(report["trusted_prediction"], ["p2", "p1"])

    def test_low_confidence_goes_to_must_run(self):
        predictions = {
            "p1": {"predicted": {"score": 0.8}, "confidence": 0.3},
            "p2": {"predicted": {"score": 0.95}, "confidence": 0.9},
            "p3": {"predicted": {"score": 0.7}, "confidence": 0.9},
        }
        report = screen_plans(PLANS, lambda plan: predictions[plan["plan_id"]], top_k=2)
        self.assertIn("p1", report["must_run"])
        self.assertNotIn("p1", report["trusted_prediction"])

    def test_unpredicted_is_not_zero(self):
        predictions = {
            "p1": {"predicted": {"score": 0.8}, "confidence": 0.9},
            "p2": None,
            "p3": {"predicted": {"score": 0.7}, "confidence": 0.9},
        }
        report = screen_plans(PLANS, lambda plan: predictions[plan["plan_id"]], top_k=3)
        self.assertEqual(report["unpredicted"], 1)
        self.assertIn("p2", report["must_run"])

    def test_missing_metric_is_unpredicted(self):
        report = screen_plans(
            PLANS,
            lambda plan: {"predicted": {"other": 1.0}, "confidence": 0.9},
            top_k=2,
        )
        self.assertEqual(report["unpredicted"], 3)

    def test_bad_confidence_rejected(self):
        with self.assertRaises(PredictorError):
            screen_plans(
                PLANS,
                lambda plan: {"predicted": {"score": 1.0}, "confidence": 1.5},
                top_k=1,
            )

    def test_requires_plan_id(self):
        with self.assertRaises(PredictorError):
            screen_plans([{}], lambda plan: None, top_k=1)

    def test_write_report(self):
        report = screen_plans(
            PLANS,
            lambda plan: {"predicted": {"score": 1.0}, "confidence": 0.9},
            top_k=1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            written = write_screen_report(report, Path(tmp) / "s.json")
            self.assertTrue(Path(written["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
