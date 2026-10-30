import json
import tempfile
import unittest
from pathlib import Path

from qone_evidence import (
    LedgerError,
    bind_evidence,
    register_claim,
    render_report,
    verify_ledger,
)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger.json"
        self.evidence = self.root / "evidence.json"
        self.evidence.write_text(json.dumps({"n_tasks": 30}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_register_bind_verify_roundtrip(self):
        register_claim(self.ledger, "C01", "Thirty tasks.", state="verified")
        bind_evidence(self.ledger, "C01", self.evidence, field="n_tasks")
        result = verify_ledger(self.ledger)
        self.assertEqual(result["result"], "passed")
        self.assertEqual(result["evidence_checked"], 1)

    def test_duplicate_claim_rejected(self):
        register_claim(self.ledger, "C01", "first")
        with self.assertRaises(LedgerError):
            register_claim(self.ledger, "C01", "second")

    def test_verified_without_evidence_fails(self):
        register_claim(self.ledger, "C01", "no evidence", state="verified")
        result = verify_ledger(self.ledger)
        self.assertEqual(result["result"], "failed")

    def test_hash_drift_detected(self):
        register_claim(self.ledger, "C01", "claim", state="verified")
        bind_evidence(self.ledger, "C01", self.evidence)
        self.evidence.write_text(json.dumps({"n_tasks": 31}), encoding="utf-8")
        result = verify_ledger(self.ledger)
        self.assertEqual(result["result"], "failed")
        self.assertIn("hash drift", " ".join(result["errors"]))

    def test_missing_evidence_file_detected(self):
        register_claim(self.ledger, "C01", "claim", state="verified")
        bind_evidence(self.ledger, "C01", self.evidence)
        self.evidence.unlink()
        result = verify_ledger(self.ledger)
        self.assertEqual(result["result"], "failed")

    def test_render_report(self):
        register_claim(self.ledger, "C01", "claim")
        text = render_report(self.ledger)
        self.assertIn("C01", text)
        self.assertIn("| ID | Claim |", text)

    def test_unknown_claim_binding_rejected(self):
        with self.assertRaises(LedgerError):
            bind_evidence(self.ledger, "C99", self.evidence)


if __name__ == "__main__":
    unittest.main()
