import tempfile
import unittest
from pathlib import Path

from qone_life.research_production import (
    ProductionError,
    ResearchProduction,
    read_stage,
)


class ProductionStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.pipeline = ResearchProduction(self.ws)
        self.question = self.ws / "question.md"
        self.question.write_text(
            "Does a judge reproduce its own gold definition? "
            "We test whether leave-one-out agreement is measurable.", encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_question_stage_records_receipt(self):
        receipt = self.pipeline.register_question("demo", self.question, "arxiv")
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["stage"], "question")
        self.assertIn("receipt_sha256", receipt)

    def test_short_question_rejected(self):
        short = self.ws / "short.md"
        short.write_text("too short", encoding="utf-8")
        with self.assertRaises(ProductionError):
            self.pipeline.register_question("demo", short, "arxiv")

    def test_hypothesis_requires_previous_stage(self):
        with self.assertRaises(ProductionError):
            self.pipeline.register_hypothesis("demo", {
                "null_hypothesis": "x", "alternative_hypothesis": "y",
                "falsification_condition": "z",
            })

    def test_hypothesis_requires_all_keys(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        with self.assertRaises(ProductionError):
            self.pipeline.register_hypothesis("demo", {"null_hypothesis": "x"})

    def test_hypothesis_succeeds_after_question(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        receipt = self.pipeline.register_hypothesis("demo", {
            "null_hypothesis": "H0", "alternative_hypothesis": "H1",
            "falsification_condition": "any mismatch",
        })
        self.assertEqual(receipt["status"], "passed")

    def test_cloud_execution_blocked_without_executor(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        self.pipeline.register_hypothesis("demo", {
            "null_hypothesis": "H0", "alternative_hypothesis": "H1",
            "falsification_condition": "x",
        })
        script = self.ws / "run.sh"
        script.write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
        data = self.ws / "data.txt"
        data.write_text("1", encoding="utf-8")
        self.pipeline.register_experiment_plan(
            "demo", missing_evidence="none", proposed_experiment="test",
            resource_requirement="none", run_script=script, inputs=[data],
            max_runtime_sec=60, max_disk_gb=1,
        )
        with self.assertRaises(ProductionError):
            self.pipeline.execute_cloud("demo")

    def test_claim_ledger_requires_results(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        with self.assertRaises(ProductionError):
            self.pipeline.write_claim_ledger("demo", [])

    def test_status_reports_missing_stages(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        status = self.pipeline.status("demo")
        self.assertEqual(status["stages"]["question"], "passed")
        self.assertEqual(status["stages"]["hypothesis"], "missing")

    def test_receipt_is_stable_on_disk(self):
        self.pipeline.register_question("demo", self.question, "arxiv")
        first = read_stage(self.ws / "research" / "production" / "demo", "question")
        second = read_stage(self.ws / "research" / "production" / "demo", "question")
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
