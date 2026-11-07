import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.meta_review import (
    DECISION_CONTINUE,
    DECISION_ROLLBACK,
    DECISION_STOP,
    DECISION_WITHHOLD,
    MetaReviewError,
    decide,
    write_decision,
)


def _rubric(total=4.2, all_passed=True):
    return {
        "schema": "q-one-review-rubric-v1",
        "mechanical": {
            "all_passed": all_passed,
            "checks": [
                {"check_id": "claims_present", "passed": all_passed},
                {"check_id": "no_blocked_claims", "passed": all_passed},
            ],
        },
        "total": total,
    }


class DecideTests(unittest.TestCase):
    def test_mechanical_failure_rolls_back(self):
        report = decide(rubric=_rubric(total=None, all_passed=False))
        self.assertEqual(report["decision"], DECISION_ROLLBACK)

    def test_missing_total_continues(self):
        report = decide(rubric=_rubric(total=None))
        self.assertEqual(report["decision"], DECISION_CONTINUE)

    def test_regression_rolls_back(self):
        report = decide(rubric=_rubric(total=3.5), previous_total=4.0)
        self.assertEqual(report["decision"], DECISION_ROLLBACK)

    def test_high_score_clean_stops(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={"objected": 0, "inconclusive": 0},
        )
        self.assertEqual(report["decision"], DECISION_STOP)

    def test_open_objection_continues(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={"objected": 1, "inconclusive": 0},
        )
        self.assertEqual(report["decision"], DECISION_CONTINUE)

    def test_uncovered_objection_notes_gap(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={"objected": 2, "inconclusive": 0},
            rebuttal={"objections": [
                {"claim_id": "C01", "class": "executable"},
            ]},
        )
        self.assertEqual(report["decision"], DECISION_CONTINUE)
        self.assertTrue(any("only 1 executable" in reason for reason in report["reasons"]))

    def test_out_of_loop_noted(self):
        report = decide(
            rubric=_rubric(total=4.5),
            rebuttal={"objections": [
                {"claim_id": "C02", "class": "out_of_loop"},
            ]},
        )
        self.assertTrue(any("out of loop" in reason for reason in report["reasons"]))

    def test_missing_rubric_raises(self):
        with self.assertRaises(MetaReviewError):
            decide(rubric={})

    def test_write_decision(self):
        report = decide(rubric=_rubric())
        with tempfile.TemporaryDirectory() as tmp:
            written = write_decision(report, Path(tmp) / "decision.json")
            self.assertTrue(Path(written["path"]).is_file())
            self.assertEqual(len(written["sha256"]), 64)

    def test_integrity_violation_withholds(self):
        report = decide(
            rubric=_rubric(total=4.5),
            integrity={"status": "violation", "findings": [
                {"type": "RF", "state": "violation"},
            ]},
        )
        self.assertEqual(report["decision"], DECISION_WITHHOLD)

    def test_integrity_incomplete_blocks_stop(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={"objected": 0, "inconclusive": 0},
            integrity={"status": "incomplete", "not_assessed": 8},
        )
        self.assertEqual(report["decision"], DECISION_CONTINUE)
        self.assertEqual(report["integrity_status"], "incomplete")

    def test_integrity_passed_allows_stop(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={"objected": 0, "inconclusive": 0},
            integrity={"status": "passed", "not_assessed": 0},
        )
        self.assertEqual(report["decision"], DECISION_STOP)

    def test_closure_reduces_objected(self):
        report = decide(
            rubric=_rubric(total=4.5),
            adversarial={
                "objected": 2, "inconclusive": 0,
                "claims": [
                    {"claim_id": "C01", "verdict": "objected"},
                    {"claim_id": "C02", "verdict": "objected"},
                ],
            },
            closure={"results": [{"claim_id": "C01", "status": "closed"}]},
        )
        self.assertEqual(report["objected"], 1)
        self.assertEqual(report["closed_claims"], ["C01"])
        self.assertEqual(report["decision"], DECISION_CONTINUE)


if __name__ == "__main__":
    unittest.main()
