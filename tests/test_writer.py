import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.writer import (
    WriterError,
    render_draft,
    resolve_value,
    write_draft_receipt,
)

HYPOTHESIS = {
    "null_hypothesis": "H0",
    "alternative_hypothesis": "H1",
    "falsification_condition": "any mismatch",
}

RESULTS = {"accuracy": 0.9234, "table": [{"score": 7}, {"score": 9}], "n": 30}


class ResolveTests(unittest.TestCase):
    def test_simple_key(self):
        self.assertEqual(resolve_value(RESULTS, "accuracy"), 0.9234)

    def test_array_index(self):
        self.assertEqual(resolve_value(RESULTS, "table[1].score"), 9)

    def test_missing_key(self):
        with self.assertRaises(WriterError):
            resolve_value(RESULTS, "missing")

    def test_index_out_of_range(self):
        with self.assertRaises(WriterError):
            resolve_value(RESULTS, "table[5].score")


class RenderTests(unittest.TestCase):
    def _claims(self, text: str) -> list[dict]:
        return [{"claim_id": "C01", "text": text, "evidence": "e"}]

    def test_substitutes_numbers(self):
        report = render_draft(
            title="T", question="Q", hypothesis=HYPOTHESIS,
            claims=self._claims("Accuracy is {{num:accuracy}} on {{num:n}} tasks."),
            results=RESULTS, venue="arxiv",
        )
        self.assertIn("0.9234", report["text"])
        self.assertIn("30", report["text"])
        self.assertEqual(report["numbers_used"], ["accuracy", "n"])

    def test_missing_key_fails(self):
        with self.assertRaises(WriterError):
            render_draft(
                title="T", question="Q", hypothesis=HYPOTHESIS,
                claims=self._claims("Value {{num:missing}}"),
                results=RESULTS, venue="arxiv",
            )

    def test_bare_number_rejected(self):
        with self.assertRaises(WriterError):
            render_draft(
                title="T", question="Q", hypothesis=HYPOTHESIS,
                claims=self._claims("Accuracy is 0.92."),
                results=RESULTS, venue="arxiv",
            )

    def test_missing_hypothesis_field_fails(self):
        with self.assertRaises(WriterError):
            render_draft(
                title="T", question="Q",
                hypothesis={"null_hypothesis": "H0"},
                claims=self._claims("Ok"), results=RESULTS, venue="arxiv",
            )

    def test_receipt_written(self):
        report = render_draft(
            title="T", question="Q", hypothesis=HYPOTHESIS,
            claims=self._claims("Accuracy {{num:accuracy}}"),
            results=RESULTS, venue="arxiv",
        )
        with tempfile.TemporaryDirectory() as tmp:
            written = write_draft_receipt(report, Path(tmp) / "main.tex")
            self.assertTrue(Path(written["draft_path"]).is_file())
            receipt = json.loads(Path(written["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "q-one-draft-render-v1")


if __name__ == "__main__":
    unittest.main()
