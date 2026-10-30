from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research import (
    build_portfolio,
    render_markdown,
    sha256_file,
    validate_research_project,
    write_portfolio,
)


class ResearchPortfolioTests(unittest.TestCase):
    def test_inventory_extracts_metadata_deduplicates_and_excludes_caches(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            canonical = root / "canonical"
            (canonical / "paper").mkdir(parents=True)
            (canonical / "paper" / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\title{Evidence-Gated Research}\n"
                "\\begin{document}\n\\end{document}\n",
                encoding="utf-8",
            )
            (canonical / "paper" / "main.pdf").write_bytes(b"pdf")
            (canonical / "CLAIM_LEDGER.md").write_text("# Claims\n", encoding="utf-8")
            (canonical / "project.json").write_text(
                json.dumps(
                    {
                        "schema": "q-one-research-project-v1",
                        "title": "Evidence-Gated Research",
                        "status": "active",
                    }
                ),
                encoding="utf-8",
            )

            backup = root / "backups"
            (backup / "paper").mkdir(parents=True)
            (backup / "paper" / "main.tex").write_bytes(
                (canonical / "paper" / "main.tex").read_bytes()
            )

            changed = root / "changed"
            (changed / "paper").mkdir(parents=True)
            (changed / "paper" / "main.tex").write_text(
                "\\title{A Changed Version}\n", encoding="utf-8"
            )

            revision = root / "revision"
            (revision / "paper").mkdir(parents=True)
            (revision / "paper" / "main.tex").write_text(
                "\\title{Evidence-Gated Research}\n\\section{Revised}\n",
                encoding="utf-8",
            )

            ignored = root / "node_modules" / "paper"
            ignored.mkdir(parents=True)
            (ignored / "main.tex").write_text("\\title{Ignored}\n", encoding="utf-8")

            skipped = root / "skipzone" / "paper"
            skipped.mkdir(parents=True)
            (skipped / "main.tex").write_text("\\title{Skipped}\n", encoding="utf-8")

            portfolio = build_portfolio(
                [root],
                generated_at="2026-10-27T00:00:00Z",
                exclude_path_fragments=("/skipzone/",),
            )

        self.assertEqual(portfolio["schema"], "q-one-paper-portfolio-v1")
        self.assertEqual(portfolio["summary"]["raw_project_roots"], 4)
        self.assertEqual(portfolio["summary"]["canonical_projects"], 2)
        self.assertEqual(portfolio["summary"]["exact_duplicate_groups"], 1)
        self.assertEqual(portfolio["summary"]["version_variants"], 1)
        self.assertEqual(portfolio["summary"]["supporting_objects"], 0)
        self.assertIsNone(portfolio["summary"]["global_readiness_score"])

        canonical_record = next(
            record
            for record in portfolio["projects"]
            if record["root"].endswith("/canonical")
        )
        self.assertEqual(canonical_record["title"], "Evidence-Gated Research")
        self.assertEqual(canonical_record["status"], "active")
        self.assertFalse(canonical_record["exact_duplicate"])

        duplicate = next(
            record
            for record in portfolio["candidates"]
            if record["root"].endswith("/backups")
        )
        self.assertTrue(duplicate["exact_duplicate"])
        self.assertEqual(
            duplicate["canonical_project_id"],
            canonical_record["project_id"],
        )
        self.assertEqual(
            duplicate["primary_sha256"],
            canonical_record["primary_sha256"],
        )
        self.assertNotIn(str(root / "node_modules"), json.dumps(portfolio))
        self.assertNotIn(str(root / "skipzone"), json.dumps(portfolio))
        markdown = render_markdown(portfolio)
        self.assertIn("Global readiness score: unknown by design", markdown)
        self.assertIn("Evidence-Gated Research", markdown)

    def test_portfolio_writer_emits_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paper = root / "paper"
            paper.mkdir()
            (paper / "main.tex").write_text("\\title{One Paper}\n", encoding="utf-8")
            portfolio = build_portfolio([root], generated_at="2026-10-27T00:00:00Z")
            output = root / "out" / "portfolio.json"
            markdown = root / "out" / "portfolio.md"
            triage = root / "out" / "portfolio.csv"
            write_portfolio(portfolio, output, markdown, triage)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["canonical_projects"], 1)
            self.assertIn("# Q-One paper portfolio", markdown.read_text(encoding="utf-8"))
            self.assertTrue(
                triage.read_text(encoding="utf-8").startswith("family_id,title,status")
            )

    def test_project_validation_checks_hashes_claims_and_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{One Paper}\n", encoding="utf-8")
            evidence = root / "evidence.json"
            evidence.write_text('{"score": 1.0}\n', encoding="utf-8")
            (root / "CLAIM_LEDGER.md").write_text(
                "| ID | Claim | Evidence | Value | Verify | Status |\n"
                "|---|---|---|---|---|---|\n"
                "| C01 | score | evidence.json -> score | 1.0 | verify | verified |\n",
                encoding="utf-8",
            )
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "one-paper",
                "title": "One Paper",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(manuscript),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [
                    {
                        "path": "evidence.json",
                        "sha256": sha256_file(evidence),
                        "state": "verified",
                        "origin": "fixture",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "C01",
                        "location": "Results",
                        "state": "blocked",
                        "evidence_refs": ["CLAIM_LEDGER.md"],
                    }
                ],
                "experiments": [],
                "reviews": [],
                "package": {
                    "state": "not-started",
                    "files": [],
                    "blockers": ["revision required"],
                },
            }
            (root / "project.json").write_text(
                json.dumps(project),
                encoding="utf-8",
            )

            report = validate_research_project(root)

        self.assertTrue(report["valid"])
        self.assertFalse(report["ready"])
        self.assertEqual(report["blocked_claims"], ["C01"])
        self.assertEqual(report["package_blockers"], ["revision required"])
        self.assertIsNone(report["global_readiness_score"])

    def test_multiple_writeups_in_one_directory_become_separate_families(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            writeups = root / "paper-evidence"
            writeups.mkdir()
            (writeups / "ARC_REVISED.md").write_text(
                "# ARC paper\n\nScores were 3.38 and 4.24.\n",
                encoding="utf-8",
            )
            (writeups / "GEMMA_REVISED.md").write_text(
                "# Gemma paper\n\nA different study.\n",
                encoding="utf-8",
            )
            portfolio = build_portfolio(
                [root],
                generated_at="2026-10-27T00:00:00Z",
                writeup_globs=("*_REVISED.md",),
            )

        self.assertEqual(portfolio["summary"]["raw_project_roots"], 2)
        self.assertEqual(portfolio["summary"]["canonical_projects"], 2)
        self.assertEqual(
            {project["title"] for project in portfolio["projects"]},
            {"ARC paper", "Gemma paper"},
        )

    def test_project_validation_rejects_package_hash_and_missing_claim_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manuscript = root / "main.tex"
            manuscript.write_text("\\title{One Paper}\n", encoding="utf-8")
            evidence = root / "evidence.json"
            evidence.write_text('{"score": 1}\n', encoding="utf-8")
            (root / "CLAIM_LEDGER.md").write_text(
                "| ID | Claim | Evidence | Value | Verify | Status |\n"
                "|---|---|---|---|---|---|\n"
                "| C01 | score | evidence.json -> score | 1 | verify | verified |\n",
                encoding="utf-8",
            )
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "bad-package",
                "title": "Bad Package",
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
                        "evidence_refs": ["missing-claim-report.md"],
                    }
                ],
                "experiments": [],
                "reviews": [],
                "package": {
                    "state": "building",
                    "files": [{"path": "evidence.json", "sha256": "0" * 64}],
                    "blockers": [],
                },
            }
            (root / "project.json").write_text(json.dumps(project), encoding="utf-8")
            report = validate_research_project(root)

        self.assertFalse(report["valid"])
        self.assertTrue(
            any("claim evidence reference is missing" in error for error in report["errors"])
        )
        self.assertTrue(
            any("package file SHA-256 mismatch" in error for error in report["errors"])
        )

    def test_project_validation_binds_measurement_to_explicit_source_field(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "main.tex").write_text("\\title{One Paper}\n", encoding="utf-8")
            evidence = root / "evidence.json"
            evidence.write_text(
                '{"metrics": {"missing": 0}, "rows": [{"score": 4.24}]}\n',
                encoding="utf-8",
            )
            (root / "CLAIM_LEDGER.md").write_text(
                "| ID | Claim | Evidence | Value | Verify | Status |\n"
                "|---|---|---|---|---|---|\n",
                encoding="utf-8",
            )
            project = {
                "schema": "q-one-research-project-v1",
                "paper_id": "measurement-binding",
                "title": "Measurement Binding",
                "status": "revision",
                "target": "arxiv",
                "root": str(root),
                "manuscript": {
                    "path": "main.tex",
                    "sha256": sha256_file(root / "main.tex"),
                    "published_source_sha256": None,
                    "matches_published_source": None,
                },
                "evidence": [
                    {
                        "path": "evidence.json",
                        "sha256": sha256_file(evidence),
                        "state": "verified",
                        "origin": "fixture",
                    }
                ],
                "claims": [],
                "experiments": [],
                "reviews": [],
                "package": {"state": "not-started", "files": [], "blockers": []},
                "measurements": [
                    {
                        "name": "missing",
                        "value": 2,
                        "unit": "count",
                        "definition": "Fixture metric.",
                        "source": "evidence.json#metrics.missing",
                        "state": "observed",
                    }
                ],
            }
            (root / "project.json").write_text(
                json.dumps(project),
                encoding="utf-8",
            )

            stale = validate_research_project(root)
            project["measurements"][0]["value"] = 0
            project["measurements"].extend(
                [
                    {
                        "name": "indexed",
                        "value": 4.24,
                        "unit": "points",
                        "definition": "Indexed fixture value.",
                        "source": "evidence.json#rows[0].score",
                        "state": "observed",
                    },
                    {
                        "name": "counted",
                        "value": 1,
                        "unit": "rows",
                        "definition": "Fixture array length.",
                        "source": "evidence.json#rows[]",
                        "state": "observed",
                    },
                ]
            )
            (root / "project.json").write_text(
                json.dumps(project),
                encoding="utf-8",
            )
            repaired = validate_research_project(root)

        self.assertFalse(stale["valid"])
        self.assertTrue(
            any(
                "measurement value does not match source" in error
                for error in stale["errors"]
            )
        )
        self.assertTrue(repaired["valid"])

    def test_qone_project_metadata_overlays_a_matching_paper_family(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paper = root / "external"
            (paper / "paper").mkdir(parents=True)
            (paper / "paper" / "main.tex").write_text(
                "\\title{Overlaid Paper}\n", encoding="utf-8"
            )
            overlay = root / "overlay"
            overlay.mkdir()
            (overlay / "project.json").write_text(
                json.dumps(
                    {
                        "schema": "q-one-research-project-v1",
                        "title": "Overlaid Paper",
                        "status": "revision",
                        "target": "arxiv",
                    }
                ),
                encoding="utf-8",
            )

            portfolio = build_portfolio([root], generated_at="2026-10-27T00:00:00Z")

        self.assertEqual(portfolio["summary"]["canonical_projects"], 1)
        self.assertEqual(portfolio["summary"]["metadata_overlays"], 1)
        project = portfolio["projects"][0]
        self.assertEqual(project["status"], "revision")
        self.assertEqual(project["target"], "arxiv")
        self.assertTrue(project["metadata_project_id"].startswith("qp-overlay-"))


if __name__ == "__main__":
    unittest.main()
