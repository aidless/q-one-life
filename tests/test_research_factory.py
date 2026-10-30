from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from qone_life.research import build_portfolio, sha256_file, validate_research_project
from qone_life.research_factory import (
    ResearchFactoryError,
    audit_arxiv_package,
    audit_git_source_lineage,
    audit_native_paper_ledger,
    build_research_plan,
    create_research_scaffold,
    triage_portfolio,
)


class ResearchFactoryTests(unittest.TestCase):
    def test_source_lineage_recovers_manifest_blob_and_preserves_revision_diff(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Q-One Test"],
                check=True,
            )
            paper = repo / "paper"
            paper.mkdir()
            manuscript = paper / "main.tex"
            manuscript.write_text("line one\nline two\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(repo), "add", "paper/main.tex"], check=True
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "fixture source"],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            expected = sha256_file(manuscript)
            current = repo / "current.tex"
            current.write_text("line one\nline two\nline three\n", encoding="utf-8")

            result = audit_git_source_lineage(
                repo,
                commit=commit,
                path="paper/main.tex",
                expected_sha256=expected,
                current_path=current,
                generated_at="2026-10-28T00:00:00Z",
            )

            self.assertEqual(result["state"], "recovered_revision")
            self.assertTrue(result["lineage_valid"])
            self.assertFalse(result["publication_identity_ready"])
            self.assertTrue(result["checks"]["expected_hash_matches_recovered"])
            self.assertEqual(result["diff"]["added_lines"], 1)
            self.assertEqual(result["diff"]["removed_lines"], 0)

            current.write_text("line one\nline two\n", encoding="utf-8")
            exact = audit_git_source_lineage(
                repo,
                commit=commit,
                path="paper/main.tex",
                expected_sha256=expected,
                current_path=current,
            )
            self.assertEqual(exact["state"], "exact")
            self.assertTrue(exact["same_bytes"])

            mismatch = audit_git_source_lineage(
                repo,
                commit=commit,
                path="paper/main.tex",
                expected_sha256="0" * 64,
                current_path=current,
            )
            self.assertEqual(mismatch["state"], "mismatch")
            self.assertFalse(mismatch["lineage_valid"])

    def _paper(self, root: Path) -> None:
        paper = root / "paper"
        (paper / "evidence").mkdir(parents=True)
        (paper / "main.tex").write_text(
            "\\documentclass{article}\n"
            "\\title{Production Paper}\n"
            "\\begin{document}\n\\end{document}\n",
            encoding="utf-8",
        )
        (paper / "main.pdf").write_bytes(b"pdf")
        (paper / "refs.bib").write_text("@article{x,\n}\n", encoding="utf-8")
        (paper / "CLAIM_LEDGER.md").write_text("# Claims\n", encoding="utf-8")
        (paper / "evidence" / "score.json").write_text('{"score": 1}\n', encoding="utf-8")

    def test_triage_is_transparent_and_does_not_change_final_disposition(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._paper(root)
            portfolio = build_portfolio([root], generated_at="2026-10-27T00:00:00Z")

        triage = triage_portfolio(
            portfolio,
            pilots=[
                {
                    "id": "pilot-one",
                    "phase": "P0",
                    "title_contains_any": ["Production Paper"],
                }
            ],
            generated_at="2026-10-27T00:00:00Z",
        )
        project = triage["projects"][0]
        self.assertEqual(project["suggested_disposition"], "repair")
        self.assertEqual(project["final_disposition"], "unreviewed")
        self.assertEqual(project["pilot_ids"], ["pilot-one"])
        self.assertEqual(project["priority_band"], "P0")
        self.assertGreater(project["production_priority"], 200)
        self.assertIsNone(triage["summary"]["global_readiness_score"])
        self.assertTrue(project["human_review_required"])

    def test_scaffold_does_not_overwrite_and_produces_valid_overlay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._paper(root)
            portfolio = build_portfolio([root], generated_at="2026-10-27T00:00:00Z")
            output = root / "overlay"
            result = create_research_scaffold(
                portfolio,
                family_id=portfolio["families"][0]["family_id"],
                output_dir=output,
                generated_at="2026-10-27T00:00:00Z",
            )

            self.assertTrue(result["validation"]["valid"])
            self.assertFalse(result["validation"]["ready"])
            project = json.loads((output / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(project["manuscript"]["sha256"], result["source_sha256"])
            self.assertEqual(project["status"], "unknown")
            self.assertTrue((output / "CLAIM_LEDGER.md").is_file())

            with self.assertRaises(ResearchFactoryError):
                create_research_scaffold(
                    portfolio,
                    family_id=portfolio["families"][0]["family_id"],
                    output_dir=output,
                )
            missing_output = root / "missing-evidence-overlay"
            with self.assertRaises(ResearchFactoryError):
                create_research_scaffold(
                    portfolio,
                    family_id=portfolio["families"][0]["family_id"],
                    output_dir=missing_output,
                    evidence_paths=[root / "missing.json"],
                )
            self.assertFalse(missing_output.exists())

    def test_plan_lists_evidence_actions_and_locks_submission(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._paper(root)
            portfolio = build_portfolio([root], generated_at="2026-10-27T00:00:00Z")
            output = root / "overlay"
            create_research_scaffold(
                portfolio,
                family_id=portfolio["families"][0]["family_id"],
                output_dir=output,
                generated_at="2026-10-27T00:00:00Z",
            )
            plan = build_research_plan(output)

        action_ids = {item["action_id"] for item in plan["next_actions"]}
        self.assertIn("register_claims", action_ids)
        self.assertNotIn("build_bibliography", action_ids)
        self.assertIn("external_submission_gate", action_ids)
        self.assertEqual(
            next(stage for stage in plan["stages"] if stage["stage"] == "external-submission")[
                "state"
            ],
            "locked",
        )

    def test_plan_uses_explicit_native_gate_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{Native Gate}\n", encoding="utf-8")
            receipt = root / "reports" / "numeric-gate.json"
            receipt.parent.mkdir()
            receipt.write_text('{"checks": "250/250"}\n', encoding="utf-8")
            (root / "CLAIM_LEDGER.md").write_text(
                "| ID | Claim | Evidence | Value | Verify | Status |\n"
                "|---|---|---|---|---|---|\n"
                "| C01 | numbers | reports/numeric-gate.json | 250/250 | rerun | verified |\n",
                encoding="utf-8",
            )
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "native-gate",
                "title": "Native Gate",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(manuscript),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [],
                "claims": [
                    {
                        "claim_id": "C01",
                        "location": "Results",
                        "state": "verified",
                        "evidence_refs": ["CLAIM_LEDGER.md"],
                    }
                ],
                "experiments": [],
                "reviews": [],
                "package": {"state": "not-started", "files": [], "blockers": []},
                "gate_receipts": [
                    {
                        "gate_id": "numeric-gate",
                        "scope": "numbers",
                        "state": "passed",
                        "receipt": "reports/numeric-gate.json",
                        "receipt_sha256": sha256_file(receipt),
                        "source_sha256": sha256_file(manuscript),
                        "summary": "250/250 numeric checks passed.",
                    }
                ],
            }
            (root / "project.json").write_text(json.dumps(project), encoding="utf-8")

            self.assertTrue(validate_research_project(root)["valid"])
            plan = build_research_plan(root)

        recomputation = next(
            stage
            for stage in plan["stages"]
            if stage["stage"] == "evidence-recomputation"
        )
        action_ids = {item["action_id"] for item in plan["next_actions"]}
        self.assertEqual(recomputation["state"], "verified")
        self.assertNotIn("reproduce_required_numeric_claims", action_ids)
        self.assertNotIn("bind_native_gate_to_current_source", action_ids)
        self.assertEqual(plan["gate_summary"]["bound_numeric_to_current_source"], 1)

    def test_plan_keeps_native_gate_as_candidate_until_source_hash_binds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{Native Gate}\n", encoding="utf-8")
            receipt = root / "reports" / "numeric-gate.json"
            receipt.parent.mkdir()
            receipt.write_text('{"checks": "250/250"}\n', encoding="utf-8")
            (root / "CLAIM_LEDGER.md").write_text(
                "| ID | Claim | Evidence | Value | Verify | Status |\n"
                "|---|---|---|---|---|---|\n"
                "| C01 | numbers | reports/numeric-gate.json | 250/250 | rerun | verified |\n",
                encoding="utf-8",
            )
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "native-gate-unbound",
                "title": "Native Gate",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(manuscript),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [],
                "claims": [
                    {
                        "claim_id": "C01",
                        "location": "Results",
                        "state": "verified",
                        "evidence_refs": ["CLAIM_LEDGER.md"],
                    }
                ],
                "experiments": [],
                "reviews": [],
                "package": {"state": "not-started", "files": [], "blockers": []},
                "gate_receipts": [
                    {
                        "gate_id": "numeric-gate",
                        "scope": "numbers",
                        "state": "passed",
                        "receipt": "reports/numeric-gate.json",
                        "receipt_sha256": sha256_file(receipt),
                        "source_sha256": "0" * 64,
                        "summary": "250/250 numeric checks passed.",
                    }
                ],
            }
            (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
            plan = build_research_plan(root)

        recomputation = next(
            stage
            for stage in plan["stages"]
            if stage["stage"] == "evidence-recomputation"
        )
        action_ids = {item["action_id"] for item in plan["next_actions"]}
        self.assertEqual(recomputation["state"], "candidate")
        self.assertIn("bind_native_gate_to_current_source", action_ids)
        self.assertNotIn("reproduce_required_numeric_claims", action_ids)

    def test_plan_uses_bound_citation_gate_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{Citations}\n", encoding="utf-8")
            (root / "refs.bib").write_text("@article{x,\n}\n", encoding="utf-8")
            receipt = root / "reports" / "citation-gate.json"
            receipt.parent.mkdir()
            receipt.write_text('{"missing": []}\n', encoding="utf-8")
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "citation-gate",
                "title": "Citations",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(manuscript),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [],
                "claims": [],
                "experiments": [],
                "reviews": [],
                "package": {"state": "not-started", "files": [], "blockers": []},
                "gate_receipts": [
                    {
                        "gate_id": "citation-gate",
                        "scope": "citations",
                        "state": "passed",
                        "receipt": "reports/citation-gate.json",
                        "receipt_sha256": sha256_file(receipt),
                        "source_sha256": sha256_file(manuscript),
                        "summary": "All citations resolved.",
                    }
                ],
            }
            (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
            plan = build_research_plan(root)

        citation_stage = next(
            stage
            for stage in plan["stages"]
            if stage["stage"] == "citation-verification"
        )
        self.assertEqual(citation_stage["state"], "verified")
        self.assertEqual(
            plan["gate_summary"]["bound_citations_to_current_source"], 1
        )

    def test_plan_binds_citation_gate_to_current_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{Citations}\n", encoding="utf-8")
            (root / "refs.bib").write_text("@article{x,\n}\n", encoding="utf-8")
            receipt = root / "reports" / "citation-gate.json"
            receipt.parent.mkdir()
            receipt.write_text('{"missing": []}\n', encoding="utf-8")
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "citation-gate-unbound",
                "title": "Citations",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(manuscript),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [],
                "claims": [],
                "experiments": [],
                "reviews": [],
                "package": {"state": "not-started", "files": [], "blockers": []},
                "gate_receipts": [
                    {
                        "gate_id": "citation-gate",
                        "scope": "citations",
                        "state": "passed",
                        "receipt": "reports/citation-gate.json",
                        "receipt_sha256": sha256_file(receipt),
                        "source_sha256": "0" * 64,
                        "summary": "All citations resolved.",
                    }
                ],
            }
            (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
            plan = build_research_plan(root)

        citation_stage = next(
            stage
            for stage in plan["stages"]
            if stage["stage"] == "citation-verification"
        )
        action_ids = {item["action_id"] for item in plan["next_actions"]}
        self.assertEqual(citation_stage["state"], "candidate")
        self.assertIn("bind_citation_gate_to_current_source", action_ids)

    def test_package_check_rejects_missing_references_and_placeholders(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\title{Bad package}\n"
                "\\begin{document}\n"
                "\\input{missing-section}\n"
                "\\cite{missing}\n"
                "\\includegraphics{/home/me/figure}\n"
                "TODO: write conclusion\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            audit = audit_arxiv_package(root, generated_at="2026-10-27T00:00:00Z")

        self.assertFalse(audit["mechanical_pass"])
        self.assertFalse(audit["ready_for_upload"])
        self.assertTrue(any("missing-section" in item for item in audit["blockers"]))
        self.assertTrue(any("absolute local path" in item for item in audit["blockers"]))
        self.assertTrue(any("placeholders" in item for item in audit["blockers"]))

    def test_package_check_passes_a_complete_minimal_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "figures").mkdir()
            (root / "figures" / "plot.png").write_bytes(b"png")
            (root / "bibliography.tex").write_text(
                "\\begin{thebibliography}{1}\n\\bibitem{x} Source.\n"
                "\\end{thebibliography}\n",
                encoding="utf-8",
            )
            (root / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\title{Good package}\n"
                "\\graphicspath{{figures/}}\n"
                "% /home/example/scratch and \\bibliography{missing} are comments\n"
                "\\begin{document}\n"
                "Math index $x_{i:\\,j}$ is not a drive path.\n"
                "\\includegraphics[width=1in]{plot}\n"
                "\\cite{x}\n"
                "\\input{bibliography}\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            audit = audit_arxiv_package(root, generated_at="2026-10-27T00:00:00Z")

        self.assertTrue(audit["mechanical_pass"])
        self.assertTrue(audit["files"])
        self.assertFalse(audit["ready_for_upload"])

    def test_native_ledger_adapter_verifies_fields_and_preserves_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "evidence").mkdir()
            (root / "evidence" / "data.json").write_text(
                json.dumps({"metric": {"value": 1.25}, "rows": [{"n": 3}]}),
                encoding="utf-8",
            )
            ledger = root / "paper-ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "good",
                                "value": 1.25,
                                "source": "evidence/data.json",
                                "field": "metric.value",
                            },
                            {
                                "key": "derived",
                                "value": 3,
                                "source": "evidence/data.json",
                                "derived": "row_count",
                            },
                            {
                                "key": "missing",
                                "value": 3,
                                "source": "evidence/data.json",
                                "field": "missing.path",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            audit = audit_native_paper_ledger(ledger, root)

        self.assertFalse(audit["mechanically_valid"])
        self.assertEqual(audit["counts"]["field_verified"], 1)
        self.assertEqual(audit["counts"]["named_derivation"], 1)
        self.assertEqual(audit["counts"]["missing_field"], 1)
        self.assertFalse(audit["scientific_ready"])


if __name__ == "__main__":
    unittest.main()
