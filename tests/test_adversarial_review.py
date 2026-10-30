import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qone_life.adversarial_review import (
    AdversarialError,
    AdversarialReview,
    parse_claims,
)

LEDGER = """| ID | Claim | Evidence | State |
|---|---|---|---|
| C01 | The sample has 30 tasks. | evidence/a.json | verified |
| C02 | Score exposure changes picks. | evidence/b.json | candidate |
"""


class ParseTests(unittest.TestCase):
    def test_parse_claims(self):
        claims = parse_claims(LEDGER)
        self.assertEqual([c["claim_id"] for c in claims], ["C01", "C02"])
        self.assertEqual(claims[0]["text"], "The sample has 30 tasks.")

    def test_no_claims(self):
        self.assertEqual(parse_claims("# empty"), [])


class AttackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "CLAIM_LEDGER.md"
        self.ledger.write_text(LEDGER, encoding="utf-8")
        self.out = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def test_zero_rounds_rejected(self):
        with self.assertRaises(AdversarialError):
            AdversarialReview().attack(self.ledger, rounds=0, models=["m"], output_dir=self.out)

    def test_no_models_rejected(self):
        with self.assertRaises(AdversarialError):
            AdversarialReview().attack(self.ledger, rounds=1, models=[], output_dir=self.out)

    def test_unreachable_gateway_is_inconclusive(self):
        review = AdversarialReview("http://127.0.0.1:9/v1/chat/completions", timeout=1)
        summary = review.attack(self.ledger, rounds=1, models=["m"], output_dir=self.out)
        self.assertEqual(summary["inconclusive"], 2)
        self.assertEqual(summary["clean"], 0)
        self.assertEqual(summary["objected"], 0)

    def test_objections_counted_and_ordered(self):
        answers = iter(["A counterexample: X", "NO_BOUNDARY_RISK", "NO_ALTERNATIVE"])

        def fake_ask(model, prompt):
            return next(answers, None)

        review = AdversarialReview()
        with patch.object(review, "_ask", side_effect=fake_ask):
            summary = review.attack(self.ledger, rounds=1, models=["m"], output_dir=self.out)
        self.assertEqual(summary["claims"][0]["verdict"], "objected")
        receipt = json.loads((self.out / "C01.json").read_text(encoding="utf-8"))
        self.assertEqual(len(receipt["objections"]), 1)
        self.assertEqual(receipt["objections"][0]["count"], 1)

    def test_clean_markers_produce_clean_verdict(self):
        review = AdversarialReview()
        with patch.object(review, "_ask", return_value="NO_COUNTEREXAMPLE"):
            summary = review.attack(self.ledger, rounds=1, models=["m"], output_dir=self.out)
        self.assertEqual(summary["clean"], 2)

    def test_summary_written(self):
        review = AdversarialReview()
        with patch.object(review, "_ask", return_value=None):
            review.attack(self.ledger, rounds=1, models=["m"], output_dir=self.out)
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["schema"], "q-one-adversarial-summary-v1")


if __name__ == "__main__":
    unittest.main()
