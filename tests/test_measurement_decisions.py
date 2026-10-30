import tempfile
import unittest
from pathlib import Path

from qone_life.measurement import MeasurementError, MeasurementStore


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MeasurementStore(Path(self.tmp.name) / "measurements.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_decision_then_outcome_then_hit_rate(self):
        decision = self.store.decide(
            "pick-next-paper", ["paper2", "noise-floor"], "paper2",
            "closest to publishable", "claim ledger 11/14", "finish in 3 days",
        )
        self.store.record_outcome(decision["seq"], "pick-next-paper", "finished", True)
        stats = self.store.hit_rate()
        self.assertEqual(stats["value"], 1.0)
        self.assertEqual(stats["n"], 1)

    def test_chosen_must_be_an_option(self):
        with self.assertRaises(MeasurementError):
            self.store.decide("s", ["a", "b"], "c", "r", "e", "o")

    def test_empty_options_rejected(self):
        with self.assertRaises(MeasurementError):
            self.store.decide("s", [], "a", "r", "e", "o")

    def test_outcome_requires_existing_decision(self):
        with self.assertRaises(MeasurementError):
            self.store.record_outcome(99, "s", "observed", True)

    def test_hit_rate_unknown_when_no_outcomes(self):
        stats = self.store.hit_rate()
        self.assertEqual(stats["value"], "unknown")
        self.assertEqual(stats["n"], 0)

    def test_mixed_outcomes(self):
        d1 = self.store.decide("s", ["a", "b"], "a", "r", "e", "o")
        d2 = self.store.decide("t", ["c", "d"], "c", "r", "e", "o")
        self.store.record_outcome(d1["seq"], "s", "ok", True)
        self.store.record_outcome(d2["seq"], "t", "bad", False)
        stats = self.store.hit_rate()
        self.assertEqual(stats["matched"], 1)
        self.assertEqual(stats["n"], 2)

    def test_chain_verifies(self):
        self.store.decide("s", ["a", "b"], "a", "r", "e", "o")
        self.assertEqual(self.store.verify(), 1)

    def test_tampered_chain_fails(self):
        self.store.decide("s", ["a", "b"], "a", "r", "e", "o")
        path = Path(self.tmp.name) / "measurements.jsonl"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('"chosen":"a"', '"chosen":"b"'), encoding="utf-8")
        with self.assertRaises(MeasurementError):
            self.store.verify()


if __name__ == "__main__":
    unittest.main()
