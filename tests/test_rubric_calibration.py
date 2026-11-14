import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.rubric_calibration import (
    calibrate,
    evaluate_human_alignment,
    evaluate_negative_samples,
    evaluate_reward_hacking_negatives,
    negative_samples,
    reward_hacking_samples,
    write_calibration_report,
)


def _model(prompt):
    return '{"score": 4, "justification": "ok"}'


class NegativeSampleTests(unittest.TestCase):
    def test_three_samples_exist(self):
        self.assertEqual(len(negative_samples()), 3)

    def test_all_negative_samples_caught(self):
        report = evaluate_negative_samples(_model)
        self.assertTrue(report["passed"])
        self.assertEqual(report["caught"], 3)
        for item in report["results"]:
            self.assertIsNone(item["total"])


class HumanAlignmentTests(unittest.TestCase):
    def test_no_labels_is_missing_not_zero(self):
        result = evaluate_human_alignment([])
        self.assertEqual(result["status"], "human_labels_missing")
        self.assertFalse(result["passed"])
        self.assertEqual(result["pearson_r"], None)

    def test_small_sample_insufficient(self):
        records = [{"rubric_total": 4.0, "human_score": 4.0} for _ in range(5)]
        result = evaluate_human_alignment(records)
        self.assertEqual(result["status"], "insufficient")
        self.assertFalse(result["passed"])

    def test_20_perfect_pairs_calibrated(self):
        records = [
            {"rubric_total": 3.0 + 0.1 * index, "human_score": 3.0 + 0.1 * index}
            for index in range(20)
        ]
        result = evaluate_human_alignment(records)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["pearson_r"], 1.0, places=6)

    def test_negative_correlation_fails(self):
        records = [
            {"rubric_total": 3.0 + 0.1 * index, "human_score": 5.0 - 0.1 * index}
            for index in range(20)
        ]
        result = evaluate_human_alignment(records)
        self.assertFalse(result["passed"])

    def test_missing_labels_not_counted_as_pairs(self):
        records = [{"rubric_total": 4.0, "human_score": None} for _ in range(5)]
        result = evaluate_human_alignment(records)
        self.assertEqual(result["pairs"], 0)
        self.assertEqual(result["missing"], 5)


class CalibrateTests(unittest.TestCase):
    def test_partial_without_human_scores(self):
        report = calibrate(model_call=_model)
        self.assertEqual(report["status"], "partial")
        self.assertTrue(report["negative_samples"]["passed"])
        self.assertEqual(report["human_alignment"]["status"], "human_labels_missing")

    def test_calibrated_with_human_scores(self):
        records = [
            {"rubric_total": 3.0 + 0.1 * index, "human_score": 3.0 + 0.1 * index}
            for index in range(20)
        ]
        report = calibrate(model_call=_model, human_records=records)
        self.assertEqual(report["status"], "calibrated")

    def test_decision_consistency(self):
        decisions = [
            {"rubric_total": 4.5, "decision": "stop"},
            {"rubric_total": 3.0, "decision": "continue"},
            {"rubric_total": 4.5, "decision": "continue"},
        ]
        report = calibrate(model_call=_model, decision_records=decisions)
        self.assertEqual(report["decision_consistency"]["consistent"], 2)
        self.assertEqual(report["decision_consistency"]["checked"], 3)

    def test_write_report(self):
        report = calibrate(model_call=_model)
        with tempfile.TemporaryDirectory() as tmp:
            written = write_calibration_report(report, Path(tmp) / "calibration.json")
            self.assertTrue(Path(written["path"]).is_file())
            self.assertEqual(len(written["sha256"]), 64)

    def test_reward_hacking_samples_caught(self):
        report = evaluate_reward_hacking_negatives()
        self.assertEqual(report["count"], 5)
        self.assertEqual(report["caught"], 5)
        self.assertTrue(report["passed"])
        self.assertEqual(
            {item["riv_type"] for item in report["results"]},
            {"ET", "RF", "SR", "CF", "CV"},
        )

    def test_calibrate_includes_reward_hacking(self):
        report = calibrate(model_call=_model)
        self.assertEqual(report["reward_hacking_negatives"]["caught"], 5)
        self.assertEqual(report["status"], "partial")

    def test_sample_list_has_five(self):
        self.assertEqual(len(reward_hacking_samples()), 5)


if __name__ == "__main__":
    unittest.main()
