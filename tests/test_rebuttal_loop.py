import json
import tempfile
import unittest
from pathlib import Path

from qone_life.rebuttal_loop import (
    CLASS_EXECUTABLE,
    CLASS_OUT_OF_LOOP,
    CLASS_UNCLASSIFIED,
    RebuttalError,
    build_rebuttal_plan,
    classify_objection,
    plan_to_registrations,
    write_rebuttal_plan,
)


def _write_attack_output(root: Path, claims: list[dict]) -> Path:
    """伪造一份 AdversarialReview.attack 的输出目录。"""
    out = root / "attack"
    out.mkdir(parents=True)
    per_claim = []
    for claim in claims:
        claim_id = claim["claim_id"]
        receipt = {
            "schema": "q-one-adversarial-v1",
            "claim_id": claim_id,
            "claim_text": claim["claim_text"],
            "objections": [
                {"text": text, "count": 1, "models": ["m"], "kinds": ["counterexample"]}
                for text in claim["objections"]
            ],
        }
        (out / f"{claim_id}.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        per_claim.append({"claim_id": claim_id, "verdict": "objected", "objections": len(claim["objections"])})
    (out / "summary.json").write_text(
        json.dumps({"schema": "q-one-adversarial-summary-v1", "claims": per_claim}, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


class ClassifyTests(unittest.TestCase):
    def test_execution_keywords_are_executable(self):
        self.assertEqual(
            classify_objection("The baseline is missing and the code does not run."),
            CLASS_EXECUTABLE,
        )

    def test_novelty_is_out_of_loop(self):
        self.assertEqual(
            classify_objection("The novelty of this idea is unclear."),
            CLASS_OUT_OF_LOOP,
        )

    def test_unrecognized_is_unclassified(self):
        self.assertEqual(classify_objection("Something feels off here."), CLASS_UNCLASSIFIED)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.attack = _write_attack_output(self.root, [
            {"claim_id": "C01", "claim_text": "The table reproduces.", "objections": ["The baseline is missing."]},
            {"claim_id": "C02", "claim_text": "Idea is good.", "objections": ["Novelty is unclear."]},
            {"claim_id": "C03", "claim_text": "Unclear.", "objections": ["Something feels off."]},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_classifies_and_drafted(self):
        plan = build_rebuttal_plan(self.attack)
        self.assertEqual(plan["executable_count"], 1)
        self.assertEqual(plan["out_of_loop_count"], 1)
        self.assertEqual(plan["unclassified_count"], 1)
        executable = [c for c in plan["objections"] if c["class"] == CLASS_EXECUTABLE]
        self.assertEqual(executable[0]["claim_id"], "C01")
        self.assertIn("experiment", executable[0])
        self.assertIn("acceptance_criteria", executable[0]["experiment"])

    def test_plan_binds_attack_summary_hash(self):
        plan = build_rebuttal_plan(self.attack)
        summary_bytes = (self.attack / "summary.json").read_bytes()
        import hashlib
        self.assertEqual(plan["attack_output_sha256"], hashlib.sha256(summary_bytes).hexdigest())

    def test_write_rebuttal_plan_writes_markdown(self):
        plan = build_rebuttal_plan(self.attack)
        out = self.root / "REBUTTAL_PLAN.md"
        written = write_rebuttal_plan(plan, out)
        self.assertTrue(out.is_file())
        self.assertIn("REBUTTAL_PLAN.md", out.read_text(encoding="utf-8"))
        self.assertTrue(written["rebuttal_plan_sha256"])

    def test_no_objections_raises(self):
        empty = _write_attack_output(self.root / "empty", [])
        with self.assertRaises(RebuttalError):
            build_rebuttal_plan(empty)

    def test_all_out_of_loop_raises(self):
        idea_only = _write_attack_output(self.root / "idea", [
            {"claim_id": "C09", "claim_text": "x", "objections": ["Novelty is unclear."]},
        ])
        with self.assertRaises(RebuttalError):
            build_rebuttal_plan(idea_only)

    def test_registrations_only_include_executable(self):
        plan = build_rebuttal_plan(self.attack)
        registrations = plan_to_registrations(plan)
        self.assertEqual(len(registrations), 1)
        self.assertEqual(registrations[0]["claim_id"], "C01")
        self.assertTrue(registrations[0]["approval_required"])
        self.assertIn("cloud", registrations[0]["resource_requirement"])


if __name__ == "__main__":
    unittest.main()
