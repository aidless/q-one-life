import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.free_judge_panel import (
    CANDIDATE_MODELS,
    PanelConfig,
    build_messages,
    canonical_sha256,
    grade_batch,
    parse_judge_response,
    probe_candidates,
    redact,
)


def response(text: str, model_id: str = "mock") -> dict:
    return {
        "model": model_id,
        "choices": [{"message": {"content": text}}],
        "usage": {"total_tokens": 10},
    }


class FakeClient:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    def complete(self, model_id, messages, timeout_s):
        self.calls.append((model_id, timeout_s))
        value = self.behavior(model_id, len(self.calls))
        if isinstance(value, Exception):
            raise value
        return value


class FreeJudgePanelTests(unittest.TestCase):
    def setUp(self):
        self.models = CANDIDATE_MODELS[:3]
        self.config = PanelConfig(model_ids=self.models, retries=2, max_concurrency=3)
        self.leaves = [{"leaf_id": f"leaf-{index}", "requirements": "evidence exists",
                        "evidence": {"carrier": "artifact.json"}} for index in range(2)]
        self.go = {model_id: {"go": True, "batch": "unit", "budget": "free"}
                   for model_id in self.models}

    def test_parse_strict_and_fenced_json(self):
        score, explanation = parse_judge_response('{"score": 0.75, "explanation": "yes"}')
        self.assertEqual(score, 0.75)
        self.assertEqual(explanation, "yes")
        score, _ = parse_judge_response('```json\n{"score": 1, "explanation": "ok"}\n```')
        self.assertEqual(score, 1.0)

    def test_parse_rejects_bad_score_and_missing_explanation(self):
        for text in ('{"score": 2, "explanation": "bad"}',
                     '{"score": 0.5}', 'not json'):
            with self.subTest(text=text), self.assertRaises(Exception):
                parse_judge_response(text)

    def test_prompt_disallows_tools_and_requires_json_only(self):
        messages = build_messages("leaf", "requirement", {"carrier": "x"})
        joined = " ".join(message["content"] for message in messages)
        self.assertIn("No tools", joined)
        self.assertIn("one JSON object", joined)
        self.assertEqual(messages[0]["role"], "system")

    def test_three_models_same_leaf_batch(self):
        client = FakeClient(lambda model_id, call: response(
            json.dumps({"score": 0.8, "explanation": model_id})))
        receipt = grade_batch(self.config, self.leaves, client=client,
                              go_receipts=self.go, sleep=lambda _: None)
        self.assertTrue(receipt.complete)
        self.assertEqual(len(receipt.results), 6)
        self.assertEqual({row.model_id for row in receipt.results}, set(self.models))
        self.assertEqual(receipt.judge_type, "free_multimodel")
        self.assertFalse(receipt.official)
        self.assertEqual(receipt.canonical_sha256, canonical_sha256(receipt.body()))

    def test_missing_go_blocks_before_any_call(self):
        client = FakeClient(lambda model_id, call: response(
            json.dumps({"score": 0.8, "explanation": "ok"})))
        incomplete = dict(self.go)
        del incomplete[self.models[1]]
        receipt = grade_batch(self.config, self.leaves, client=client,
                              go_receipts=incomplete, sleep=lambda _: None)
        self.assertFalse(receipt.complete)
        self.assertEqual(client.calls, [])
        self.assertTrue(any("missing_user_go" in reason for reason in receipt.blocked_reasons))

    def test_timeout_retry_then_one_model_missing_blocks_batch(self):
        def behavior(model_id, call):
            if model_id == self.models[2]:
                raise TimeoutError("gateway timeout")
            return response(json.dumps({"score": 0.6, "explanation": "ok"}))

        client = FakeClient(behavior)
        receipt = grade_batch(self.config, self.leaves[:1], client=client,
                              go_receipts=self.go, sleep=lambda _: None)
        self.assertFalse(receipt.complete)
        self.assertEqual(len(receipt.results), 3)
        self.assertEqual(sum(row.status == "scored" for row in receipt.results), 2)
        self.assertTrue(any("gateway timeout" in row.error for row in receipt.results))

    def test_parse_error_no_partial_score(self):
        client = FakeClient(lambda model_id, call: response("not json"))
        receipt = grade_batch(self.config, self.leaves[:1], client=client,
                              go_receipts=self.go, sleep=lambda _: None)
        self.assertFalse(receipt.complete)
        self.assertTrue(all(row.score is None for row in receipt.results))

    def test_probe_locks_first_three_passed(self):
        def behavior(model_id, call):
            if model_id.startswith("opencode-zen-free/crouton"):
                return response("not json")
            return response(json.dumps({"score": 0.9, "explanation": "ok"}))

        report = probe_candidates(self.leaves[0], client=FakeClient(behavior),
                                  timeout_s=5, retries=1, sleep=lambda _: None)
        self.assertTrue(report["complete"])
        self.assertEqual(len(report["locked_model_ids"]), 3)
        self.assertNotIn("opencode-zen-free/crouton-alpha-free", report["locked_model_ids"])

    def test_redact_secret_shaped_logs(self):
        self.assertEqual(redact("Bearer abcdefghijklmnop"), "[REDACTED]")
        self.assertIn("[REDACTED]", redact("sk-abcdefghijklmnop"))

    def test_go_cli_never_writes_budget_secret(self):
        from unittest.mock import patch
        from scripts.run_free_judge_panel import main

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "go.json"
            argv = ["run_free_judge_panel.py", "go", "--go-file", str(path),
                    "--model-id", self.models[0], "--batch", "leaf-batch-1",
                    "--budget", "free-only"]
            with patch("sys.argv", argv):
                self.assertEqual(main(), 0)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["receipts"][self.models[0]]["go"])
            self.assertNotIn("key", path.read_text(encoding="utf-8").lower().replace("key value", ""))


if __name__ == "__main__":
    unittest.main()
