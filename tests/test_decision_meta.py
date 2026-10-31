"""Decision cost/reversibility/deadline tests."""
import tempfile
import unittest
from pathlib import Path

from qone_life.measurement import MeasurementError, MeasurementStore


class DecisionCostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = MeasurementStore(Path(self.tmp.name) / "measurements.jsonl")

    def _decide(self, **overrides):
        base = {
            "subject": "upgrade-vm", "options": ["yes", "no"], "chosen": "yes",
            "rationale": "need compute", "evidence": "bench 3.5x", "expected_outcome": "faster",
        }
        base.update(overrides)
        return self.store.decide(**base)

    def test_decision_with_meta(self):
        e = self._decide(cost="2h", reversibility="reversible", deadline="2026-11-15T00:00:00Z")
        self.assertEqual(e["payload"]["cost"], "2h")
        self.assertEqual(e["payload"]["reversibility"], "reversible")
        self.assertEqual(e["payload"]["deadline"], "2026-11-15T00:00:00Z")

    def test_decision_without_meta(self):
        e = self._decide()
        self.assertNotIn("cost", e["payload"])
        self.assertNotIn("reversibility", e["payload"])
        self.assertNotIn("deadline", e["payload"])

    def test_invalid_reversibility_rejected(self):
        with self.assertRaises(MeasurementError):
            self._decide(reversibility="maybe")

    def test_chain_verifies_with_meta(self):
        self._decide(cost="2h", reversibility="irreversible", deadline="2026-11-15T00:00:00Z")
        self.assertEqual(self.store.verify(), 1)


if __name__ == "__main__":
    unittest.main()
