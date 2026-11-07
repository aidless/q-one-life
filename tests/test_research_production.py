import tempfile
import unittest
from pathlib import Path

from qone_life.research_production import (
    ProductionError,
    ResearchProduction,
    read_stage,
)


class FakeExecutor:
    """返回成功的最小云端执行器替身，仅用于测试管线阶段流转。"""

    def submit(self, job_dir):
        return {
            "job_id": "job-1",
            "remote_dir": "/remote/job-1",
            "submitted_at": "2026-11-05T00:00:00Z",
        }

    def wait(self, job_id, *, max_runtime_sec, poll_interval):
        return {"state": "succeeded"}

    def fetch(self, job_id, target_dir):
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        outputs = target / "outputs"
        outputs.mkdir(exist_ok=True)
        result = outputs / "result.json"
        result.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        return {
            "job_id": job_id,
            "target": str(target),
            "files": [{"path": "outputs/result.json", "sha256": "abc", "bytes": 18}],
            "logs": {},
            "fetched_at": "2026-11-05T00:00:01Z",
        }


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

    def _advance_to_claim_ledger(self):
        pipeline = ResearchProduction(self.ws, executor=FakeExecutor())
        pipeline.register_question("demo", self.question, "arxiv")
        pipeline.register_hypothesis("demo", {
            "null_hypothesis": "H0", "alternative_hypothesis": "H1",
            "falsification_condition": "any mismatch",
        })
        script = self.ws / "run.sh"
        script.write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
        data = self.ws / "data.txt"
        data.write_text("1", encoding="utf-8")
        pipeline.register_experiment_plan(
            "demo", missing_evidence="none", proposed_experiment="test",
            resource_requirement="cpu", run_script=script, inputs=[data],
            max_runtime_sec=60, max_disk_gb=1,
        )
        pipeline.execute_cloud("demo")
        target = self.ws / "fetched"
        pipeline.collect_results("demo", target)
        pipeline.write_claim_ledger("demo", [{
            "claim_id": "C01", "text": "A", "evidence": "evidence/a.json",
            "state": "verified",
        }])
        return pipeline

    def test_rebuttal_requires_claim_ledger(self):
        with self.assertRaises(ProductionError):
            self.pipeline.attach_rebuttal_plan("demo", {"objections": [
                {"claim_id": "C01", "class": "executable", "objection": "x",
                 "experiment": {"experiment": "y"}},
            ]})

    def test_rebuttal_rejects_empty_plan(self):
        pipeline = self._advance_to_claim_ledger()
        with self.assertRaises(ProductionError):
            pipeline.attach_rebuttal_plan("demo", {"objections": [
                {"claim_id": "C02", "class": "out_of_loop", "objection": "novelty"},
            ]})

    def test_rebuttal_attaches_with_hashes(self):
        pipeline = self._advance_to_claim_ledger()
        receipt = pipeline.attach_rebuttal_plan("demo", {"objections": [
            {"claim_id": "C01", "class": "executable", "objection": "baseline missing",
             "experiment": {"experiment": "rerun baseline"}},
        ]})
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["auxiliary"], "rebuttal")
        self.assertEqual(len(receipt["plan_sha256"]), 64)
        self.assertTrue(Path(receipt["plan_path"]).is_file())
        self.assertTrue(Path(receipt["markdown_path"]).is_file())
        self.assertTrue(receipt["registrations"][0]["approval_required"])


if __name__ == "__main__":
    unittest.main()
