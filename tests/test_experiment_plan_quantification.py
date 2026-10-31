"""plan_experiment duration/power quantification tests."""
import unittest

from qone_life.measurement import MeasurementError, plan_experiment


class ExperimentPlanQuantificationTests(unittest.TestCase):
    def test_plan_with_duration_and_power(self):
        plan = plan_experiment(
            claim_id="c1",
            missing_evidence="no baseline run",
            proposed_experiment="run sweep",
            resource_requirement="local cpu",
            estimated_duration_sec=3600,
            statistical_power=0.8,
        )
        self.assertEqual(plan["estimated_duration_sec"], 3600)
        self.assertEqual(plan["statistical_power"], 0.8)
        self.assertEqual(plan["estimated_cost"], "local cpu")

    def test_plan_defaults_none(self):
        plan = plan_experiment("c2", "gap", "exp", "local")
        self.assertIsNone(plan["estimated_duration_sec"])
        self.assertIsNone(plan["statistical_power"])

    def test_negative_duration_rejected(self):
        with self.assertRaises(MeasurementError):
            plan_experiment("c3", "gap", "exp", "local", estimated_duration_sec=-5)

    def test_invalid_power_rejected(self):
        with self.assertRaises(MeasurementError):
            plan_experiment("c4", "gap", "exp", "local", statistical_power=1.5)

    def test_paid_resource_requires_approval(self):
        plan = plan_experiment("c5", "gap", "exp", "gpu hours")
        self.assertTrue(plan["approval_required"])
        self.assertFalse(plan["auto_executable"])


if __name__ == "__main__":
    unittest.main()
