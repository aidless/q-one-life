from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "research"
    / "pilot-bench-noise-floor"
    / "experiments"
    / "producer-baseline-counterexample"
)


class ProducerBaselineCounterexampleTests(unittest.TestCase):
    def test_frozen_counterexample_reproduces_byte_identically(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "run-1.json"
            second = Path(folder) / "run-2.json"
            for output in (first, second):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(EXPERIMENT / "run_counterexample.py"),
                        "--preregistration",
                        str(EXPERIMENT / "preregistration.json"),
                        "--output",
                        str(output),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            receipt = json.loads(first.read_text(encoding="utf-8"))

        self.assertEqual(
            receipt["hypothesis_decision"],
            "reject_H0_in_declared_synthetic_condition",
        )
        self.assertTrue(receipt["all_expected_signatures_met"])
        conditions = {item["role"]: item for item in receipt["conditions"]}
        critical = conditions["critical_counterexample"]
        self.assertEqual(critical["producer_floor"], 1.0)
        self.assertFalse(critical["gate_readable"])
        self.assertEqual(critical["delete_one_stability"]["stable"], 700)
        self.assertEqual(critical["delete_one_stability"]["defined"], 700)
        self.assertEqual(
            critical["paired_comparison"]["first_only_correct"], 280
        )
        self.assertEqual(
            critical["paired_comparison"]["second_only_correct"], 0
        )
        self.assertEqual(conditions["positive_control"]["producer_floor"], 0.8)
        self.assertTrue(conditions["positive_control"]["gate_readable"])
        self.assertEqual(
            conditions["negative_control"]["observed_relation"],
            "first_lt_second",
        )

