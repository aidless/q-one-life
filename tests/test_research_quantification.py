"""Research quantification quantity tests."""
import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research import quantify_research_project, sha256_file


class ResearchQuantificationTests(unittest.TestCase):
    def _write_project(self, root, project):
        (root / "project.json").write_text(json.dumps(project), encoding="utf-8")

    def test_missing_project_reports_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            report = quantify_research_project(Path(folder))
        self.assertFalse(report["valid"])
        q = report["quantities"]
        self.assertEqual(q["claim_evidence_coverage"]["value"], "unknown")

    def test_empty_project_quantities_are_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "empty", "title": "Empty", "status": "active",
                "target": "arxiv",
                "manuscript": {}, "evidence": [], "claims": [],
                "experiments": [], "reviews": [], "package": {},
            })
            report = quantify_research_project(root)
        self.assertTrue(report["valid"])
        q = report["quantities"]
        self.assertEqual(q["claim_evidence_coverage"]["value"], "unknown")
        self.assertEqual(q["experiment_reproduction_coverage"]["value"], "unknown")
        self.assertEqual(q["citation_verification_coverage"]["value"], "unknown")
        self.assertEqual(q["package_completeness"]["value"], "unknown")

    def test_claim_evidence_coverage_computed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "c", "title": "C", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [],
                "claims": [
                    {"claim_id": "C01", "state": "verified", "evidence_refs": ["e.json"]},
                    {"claim_id": "C02", "state": "verified", "evidence_refs": []},
                ],
                "experiments": [], "reviews": [], "package": {},
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["claim_evidence_coverage"]["value"], 0.5)
        self.assertEqual(report["quantities"]["claim_evidence_coverage"]["numerator"], 1)
        self.assertEqual(report["quantities"]["claim_evidence_coverage"]["denominator"], 2)

    def test_recomputation_uses_json_csv_refs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "r", "title": "R", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [],
                "claims": [
                    {"claim_id": "C01", "state": "verified", "evidence_refs": ["data.json"]},
                    {"claim_id": "C02", "state": "verified", "evidence_refs": ["report.md"]},
                    {"claim_id": "C03", "state": "verified", "evidence_refs": ["t.csv"]},
                ],
                "experiments": [], "reviews": [], "package": {},
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["claim_recomputation_coverage"]["value"], 2 / 3)

    def test_experiment_reproduction_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "receipt.json").write_text("{}", encoding="utf-8")
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "e", "title": "E", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [],
                "claims": [], "reviews": [], "package": {},
                "experiments": [
                    {"experiment_id": "E1", "state": "required",
                     "receipt": "receipt.json", "environment_sha256": "a" * 64},
                    {"experiment_id": "E2", "state": "required", "receipt": None},
                    {"experiment_id": "E3", "state": "optional"},
                ],
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["experiment_reproduction_coverage"]["value"], 0.5)
        self.assertEqual(report["quantities"]["experiment_reproduction_coverage"]["denominator"], 2)

    def test_unresolved_reviews_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "u", "title": "U", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [], "claims": [],
                "experiments": [], "package": {},
                "reviews": [
                    {"review_id": "R1", "state": "open", "critical": 1, "major": 2},
                    {"review_id": "R2", "state": "closed", "critical": 5, "major": 5},
                ],
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["unresolved_critical"]["value"], 1)
        self.assertEqual(report["quantities"]["unresolved_major"]["value"], 2)

    def test_package_completeness_counts_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "main.tex").write_text("\\title{X}", encoding="utf-8")
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "p", "title": "P", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [], "claims": [],
                "experiments": [], "reviews": [],
                "package": {
                    "files": [
                        {"path": "main.tex", "sha256": sha256_file(root / "main.tex")},
                        {"path": "missing.tex", "sha256": "0" * 64},
                    ]
                },
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["package_completeness"]["value"], 0.5)

    def test_citation_verification_reads_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "CLAIM_LEDGER.md").write_text(
                "| C01 | a | e.json | 1 | verify | verified |\n"
                "| C02 | b | f.json | 2 | verify | candidate |\n",
                encoding="utf-8",
            )
            self._write_project(root, {
                "schema": "q-one-research-project-v1",
                "paper_id": "v", "title": "V", "status": "active", "target": "arxiv",
                "manuscript": {}, "evidence": [], "claims": [],
                "experiments": [], "reviews": [], "package": {},
            })
            report = quantify_research_project(root)
        self.assertEqual(report["quantities"]["citation_verification_coverage"]["value"], 0.5)
        self.assertEqual(report["quantities"]["citation_verification_coverage"]["denominator"], 2)


if __name__ == "__main__":
    unittest.main()
