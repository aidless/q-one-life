import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.rubric_types import (
    TYPE_RUBRICS,
    TypeRubricError,
    evaluate_type_rubric,
    infer_paper_type,
    write_type_rubric,
)


class InferTests(unittest.TestCase):
    def test_benchmark_type(self):
        text = "We introduce a benchmark with train/dev/test splits and baselines."
        self.assertEqual(infer_paper_type(text), "benchmark")

    def test_theory_type(self):
        text = "Theorem 1. Proof. Under the assumption, the derivation holds."
        self.assertEqual(infer_paper_type(text), "theory")

    def test_empty_rejected(self):
        with self.assertRaises(TypeRubricError):
            infer_paper_type("   ")


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        path = self.root / "main.tex"
        path.write_text(text, encoding="utf-8")
        return path

    def test_complete_audit_paper_passes(self):
        path = self._write(
            r"\section*{Limitations} threat to validity. "
            r"Claim ledger and SHA-256 receipts support reproducibility. "
            r"Baseline comparison. \cite{k1}"
        )
        report = evaluate_type_rubric(path, paper_type="audit")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["passed"], report["total"])

    def test_incomplete_paper(self):
        path = self._write(r"We report a result.")
        report = evaluate_type_rubric(path, paper_type="empirical_ml")
        self.assertEqual(report["status"], "incomplete")
        self.assertLess(report["passed"], report["total"])

    def test_unknown_type_rejected(self):
        path = self._write("text")
        with self.assertRaises(TypeRubricError):
            evaluate_type_rubric(path, paper_type="unknown")

    def test_missing_file_rejected(self):
        with self.assertRaises(TypeRubricError):
            evaluate_type_rubric(self.root / "missing.tex")

    def test_write_report(self):
        path = self._write("claim ledger reproducibility baseline limitations")
        report = evaluate_type_rubric(path, paper_type="audit")
        written = write_type_rubric(report, self.root / "type.json")
        self.assertTrue(Path(written["path"]).is_file())
        self.assertEqual(len(written["sha256"]), 64)

    def test_all_types_have_checks(self):
        for name, spec in TYPE_RUBRICS.items():
            self.assertTrue(spec["checks"], name)


if __name__ == "__main__":
    unittest.main()
