"""Outcome latency tests."""
import tempfile
import unittest
from pathlib import Path

from qone_life.measurement import MeasurementError, MeasurementStore


class OutcomeLatencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = MeasurementStore(Path(self.tmp.name) / "measurements.jsonl")
        self.store.decide(
            subject="upgrade-vm", options=["yes", "no"], chosen="yes",
            rationale="need compute", evidence="bench 3.5x", expected_outcome="faster",
        )

    def test_outcome_with_latency(self):
        e = self.store.record_outcome(1, "upgrade-vm", "faster", True, latency_sec=7200)
        self.assertEqual(e["payload"]["latency_sec"], 7200)
        self.assertTrue(e["payload"]["matched"])

    def test_outcome_without_latency(self):
        e = self.store.record_outcome(1, "upgrade-vm", "faster", True)
        self.assertNotIn("latency_sec", e["payload"])

    def test_negative_latency_rejected(self):
        with self.assertRaises(MeasurementError):
            self.store.record_outcome(1, "upgrade-vm", "faster", True, latency_sec=-1)

    def test_chain_verifies_with_latency(self):
        self.store.record_outcome(1, "upgrade-vm", "faster", True, latency_sec=60)
        self.assertEqual(self.store.verify(), 2)


if __name__ == "__main__":
    unittest.main()
