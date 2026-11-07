import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.autopilot import (
    AutopilotError,
    generate_hypotheses,
    make_hypothesis_scorer,
    run_batch,
    screen_hypotheses,
    write_autopilot_report,
)


def _candidate(index: int) -> dict:
    return {
        "null_hypothesis": f"H0-{index}",
        "alternative_hypothesis": f"H1-{index}",
        "falsification_condition": "any mismatch",
        "novelty_rationale": "not yet established",
        "required_resources": "cpu",
    }


class GenerateTests(unittest.TestCase):
    def test_generates_requested_candidates(self):
        payload = json.dumps([_candidate(i) for i in range(3)])
        report = generate_hypotheses("Does X affect Y?", lambda prompt: payload, n=3)
        self.assertEqual(report["schema"], "q-one-hypothesis-candidates-v1")
        self.assertEqual(len(report["candidates"]), 3)
        self.assertEqual(report["candidates"][0]["candidate_id"], "H01")
        self.assertNotIn("question_sha256", report["candidates"][0])

    def test_rejects_missing_field(self):
        bad = _candidate(0)
        del bad["falsification_condition"]
        with self.assertRaises(AutopilotError):
            generate_hypotheses("q", lambda prompt: json.dumps([bad]), n=1)

    def test_rejects_none_answer(self):
        with self.assertRaises(AutopilotError):
            generate_hypotheses("q", lambda prompt: None, n=1)

    def test_rejects_too_few_candidates(self):
        with self.assertRaises(AutopilotError):
            generate_hypotheses("q", lambda prompt: json.dumps([_candidate(0)]), n=2)

    def test_rejects_non_array(self):
        with self.assertRaises(AutopilotError):
            generate_hypotheses("q", lambda prompt: '{"a": 1}', n=1)

    def test_requires_model_call(self):
        with self.assertRaises(AutopilotError):
            generate_hypotheses("q", None, n=1)


class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"candidate_id": f"H{i:02d}", "null_hypothesis": f"h{i}"}
            for i in range(1, 5)
        ]

    def test_ranks_and_selects_top_k(self):
        scores = {"H01": 0.2, "H02": 0.9, "H03": 0.5, "H04": 0.7}
        report = screen_hypotheses(
            self.candidates, lambda c: scores[c["candidate_id"]], top_k=2
        )
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["selected"], ["H02", "H04"])

    def test_inconclusive_not_treated_as_zero(self):
        scores = {"H01": 0.2, "H02": None, "H03": 0.5, "H04": 0.7}
        report = screen_hypotheses(
            self.candidates, lambda c: scores[c["candidate_id"]], top_k=2
        )
        self.assertEqual(report["inconclusive"], 1)
        self.assertEqual(report["selected"], ["H04", "H03"])
        self.assertEqual(report["status"], "ok")

    def test_majority_inconclusive_blocks(self):
        scores = {"H01": None, "H02": None, "H03": 0.5, "H04": None}
        report = screen_hypotheses(
            self.candidates, lambda c: scores[c["candidate_id"]], top_k=1
        )
        self.assertEqual(report["status"], "blocked")

    def test_out_of_range_score_raises(self):
        with self.assertRaises(AutopilotError):
            screen_hypotheses(self.candidates, lambda c: 1.5, top_k=1)

    def test_scorer_factory_parses_json(self):
        answers = iter(
            ['{"score": 0.8, "reason": "cheap"}', '{"score": 0.1, "reason": "costly"}']
        )
        scorer = make_hypothesis_scorer(lambda prompt: next(answers, None))
        self.assertEqual(scorer(self.candidates[0]), 0.8)
        self.assertEqual(scorer(self.candidates[1]), 0.1)

    def test_scorer_factory_returns_none_on_garbage(self):
        scorer = make_hypothesis_scorer(lambda prompt: "not json")
        self.assertIsNone(scorer(self.candidates[0]))


class ReportTests(unittest.TestCase):
    def test_write_report_returns_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sub" / "report.json"
            written = write_autopilot_report({"schema": "x"}, out)
            self.assertTrue(out.is_file())
            self.assertEqual(len(written["sha256"]), 64)


class BatchTests(unittest.TestCase):
    def _model_call(self, prompt: str):
        if "Produce exactly" in prompt:
            return json.dumps([_candidate(i) for i in range(2)])
        return '{"score": 0.6, "reason": "ok"}'

    def test_batch_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            question = root / "q.md"
            question.write_text("Does X affect Y?", encoding="utf-8")
            items = [
                {"slug": "a", "question": str(question)},
                {"slug": "b", "question": str(question)},
            ]
            summary = run_batch(items, self._model_call, n=2, output_dir=root / "out")
            self.assertEqual(summary["ok"], 2)
            self.assertEqual(summary["failed"], 0)
            self.assertTrue((root / "out" / "a" / "hypotheses.json").is_file())
            self.assertTrue((root / "out" / "summary.json").is_file())

    def test_batch_isolates_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            question = root / "q.md"
            question.write_text("Does X affect Y?", encoding="utf-8")
            items = [
                {"slug": "ok", "question": str(question)},
                {"slug": "bad", "question": str(root / "missing.md")},
            ]
            summary = run_batch(items, self._model_call, n=2, output_dir=root / "out")
            self.assertEqual(summary["ok"], 1)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["results"][1]["status"], "failed")

    def test_empty_batch_raises(self):
        with self.assertRaises(AutopilotError):
            run_batch([], lambda prompt: None, output_dir="/tmp/x")


if __name__ == "__main__":
    unittest.main()
