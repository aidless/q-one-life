import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.review_rubric import (
    ReviewRubricError,
    parse_claim_ledger,
    run_mechanical_checks,
    score_manuscript,
    write_review_report,
)

LEDGER = """# CLAIM_LEDGER.md

| ID | Claim | Evidence | State |
|---|---|---|---|
| C01 | A | evidence/a.json | verified |
| C02 | B | evidence/b.json | verified |
"""

MANUSCRIPT = r"""
\section*{Limitations}
We discuss threats to validity.
Code availability: our artifacts are reproducible.
See \cite{ref1} and \cite{ref2}.
"""


class LedgerTests(unittest.TestCase):
    def test_counts_states(self):
        counts = parse_claim_ledger(LEDGER)
        self.assertEqual(counts["verified"], 2)
        self.assertEqual(counts["blocked"], 0)

    def test_empty_ledger(self):
        counts = parse_claim_ledger("# empty")
        self.assertEqual(sum(counts.values()), 0)

    def test_six_column_ledger_uses_header_state_index(self):
        ledger = (
            "| ID | Claim | Evidence | Numeric values | Verification | Status |\n"
            "|---|---|---|---|---|---|\n"
            "| C01 | A | e | 1 | rerun | verified |\n"
            "| C02 | B | e | - | rerun | blocked |\n"
        )
        counts = parse_claim_ledger(ledger)
        self.assertEqual(counts["verified"], 1)
        self.assertEqual(counts["blocked"], 1)


class MechanicalTests(unittest.TestCase):
    def test_all_checks_pass(self):
        result = run_mechanical_checks(MANUSCRIPT, LEDGER)
        self.assertTrue(result["all_passed"])
        self.assertEqual(result["total_claims"], 2)

    def test_blocked_claim_fails(self):
        ledger = LEDGER + "| C03 | C | evidence/c.json | blocked |\n"
        result = run_mechanical_checks(MANUSCRIPT, ledger)
        self.assertFalse(result["all_passed"])
        check = {item["check_id"]: item for item in result["checks"]}
        self.assertFalse(check["no_blocked_claims"]["passed"])


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manuscript = self.root / "main.tex"
        self.manuscript.write_text(MANUSCRIPT, encoding="utf-8")
        self.ledger = self.root / "CLAIM_LEDGER.md"
        self.ledger.write_text(LEDGER, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _answers(self, values):
        iterator = iter(values)
        return lambda prompt: next(iterator, None)

    def test_full_score_computed(self):
        model = self._answers([
            json.dumps({"score": 4, "justification": "new"}),
            json.dumps({"score": 5, "justification": "rigorous"}),
            json.dumps({"score": 3, "justification": "clear"}),
        ])
        report = score_manuscript(self.manuscript, self.ledger, model)
        self.assertEqual(report["status"], "scored")
        self.assertAlmostEqual(report["total"], 4 * 0.3 + 5 * 0.4 + 3 * 0.3)

    def test_missing_dimension_blocks_total(self):
        model = self._answers([
            json.dumps({"score": 4, "justification": "new"}),
            None,
            json.dumps({"score": 3, "justification": "clear"}),
        ])
        report = score_manuscript(self.manuscript, self.ledger, model)
        self.assertEqual(report["status"], "inconclusive")
        self.assertIsNone(report["total"])
        states = [item["state"] for item in report["dimensions"]]
        self.assertIn("inconclusive", states)

    def test_invalid_score_value_is_inconclusive(self):
        model = self._answers([
            json.dumps({"score": 9, "justification": "bad"}),
            json.dumps({"score": 4, "justification": "ok"}),
            json.dumps({"score": 3, "justification": "ok"}),
        ])
        report = score_manuscript(self.manuscript, self.ledger, model)
        self.assertEqual(report["status"], "inconclusive")
        self.assertIsNone(report["total"])

    def test_mechanical_failure_blocks_total(self):
        bad_ledger = self.root / "bad.md"
        bad_ledger.write_text("| ID | Claim | Evidence | State |\n|---|---|---|---|\n| C01 | x | y | blocked |\n", encoding="utf-8")
        model = self._answers([
            json.dumps({"score": 5, "justification": "x"}),
            json.dumps({"score": 5, "justification": "x"}),
            json.dumps({"score": 5, "justification": "x"}),
        ])
        report = score_manuscript(self.manuscript, bad_ledger, model)
        self.assertIsNone(report["total"])
        self.assertFalse(report["mechanical"]["all_passed"])

    def test_weights_must_sum_to_one(self):
        with self.assertRaises(ReviewRubricError):
            score_manuscript(
                self.manuscript, self.ledger, lambda prompt: None,
                weights={"novelty": 1.0, "rigor": 1.0, "clarity": 1.0},
            )

    def test_missing_manuscript_raises(self):
        with self.assertRaises(ReviewRubricError):
            score_manuscript(self.root / "missing.tex", self.ledger, lambda p: None)

    def test_write_report_returns_hash(self):
        model = self._answers([
            json.dumps({"score": 4, "justification": "x"}),
            json.dumps({"score": 4, "justification": "x"}),
            json.dumps({"score": 4, "justification": "x"}),
        ])
        report = score_manuscript(self.manuscript, self.ledger, model)
        out = self.root / "review.json"
        written = write_review_report(report, out)
        self.assertTrue(out.is_file())
        self.assertEqual(len(written["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
