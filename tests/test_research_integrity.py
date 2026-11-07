import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.research_integrity import (
    NOT_ASSESSED,
    PASS,
    VIOLATION,
    audit_integrity,
    write_integrity_report,
)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _clean(self):
        manuscript = self._write(
            "main.tex",
            r"\section*{Limitations} Limitations. \cite{k1} {{num:acc}}",
        )
        ledger = self._write(
            "CLAIM_LEDGER.md",
            "| ID | Claim | Evidence | State |\n|---|---|---|---|\n| C01 | x | e | verified |\n",
        )
        results = self._write("results.json", json.dumps({"acc": 0.9}))
        bib = self._write("refs.bib", "@article{k1,\n title={T}\n}\n")
        job = self._write(
            "job.json",
            json.dumps({"max_runtime_sec": 60, "max_disk_gb": 1}),
        )
        prereg = self._write("prereg.json", json.dumps({"version": "1.0.0"}))
        return dict(
            manuscript=manuscript, ledger=ledger, results=results,
            bibliography=bib, job=job, preregistration=prereg,
        )

    def test_rf_unresolved_placeholder_is_violation(self):
        paths = self._clean()
        paths["results"] = self._write("r2.json", json.dumps({"other": 1}))
        report = audit_integrity(**paths)
        rf = next(item for item in report["findings"] if item["type"] == "RF")
        self.assertEqual(rf["state"], VIOLATION)
        self.assertEqual(report["status"], "violation")
        self.assertEqual(report["release"], "withhold")

    def test_cf_missing_bib_key_is_violation(self):
        paths = self._clean()
        paths["bibliography"] = self._write("refs2.bib", "@article{other,\n}\n")
        report = audit_integrity(**paths)
        cf = next(item for item in report["findings"] if item["type"] == "CF")
        self.assertEqual(cf["state"], VIOLATION)

    def test_cf_accepts_manual_bibitem(self):
        paths = self._clean()
        paths["manuscript"] = self._write(
            "m3.tex",
            r"\section*{Limitations} \cite{k1} {{num:acc}} "
            r"\begin{thebibliography}{1}\bibitem{k1} T.\end{thebibliography}",
        )
        paths["bibliography"] = self._write("empty.bib", "")
        report = audit_integrity(**paths)
        cf = next(item for item in report["findings"] if item["type"] == "CF")
        self.assertEqual(cf["state"], PASS)

    def test_sr_blocked_without_limitations(self):
        paths = self._clean()
        paths["manuscript"] = self._write("m2.tex", r"Result \cite{k1} {{num:acc}}")
        paths["ledger"] = self._write(
            "l2.md",
            "| ID | Claim | Evidence | State |\n|---|---|---|---|\n| C01 | x | e | blocked |\n",
        )
        report = audit_integrity(**paths)
        sr = next(item for item in report["findings"] if item["type"] == "SR")
        self.assertEqual(sr["state"], VIOLATION)

    def test_cv_job_over_limit(self):
        paths = self._clean()
        paths["job"] = self._write(
            "job2.json", json.dumps({"max_runtime_sec": 999999, "max_disk_gb": 1})
        )
        report = audit_integrity(**paths)
        cv = next(item for item in report["findings"] if item["type"] == "CV")
        self.assertEqual(cv["state"], VIOLATION)

    def test_et_evaluator_hash_mismatch(self):
        paths = self._clean()
        evaluator = self._write("evaluator.py", "print('x')\n")
        report = audit_integrity(
            **paths, evaluator=evaluator, evaluator_sha256="0" * 64
        )
        et = next(item for item in report["findings"] if item["type"] == "ET")
        self.assertEqual(et["state"], VIOLATION)

    def test_oddc_amendment_with_frozen_parent_passes(self):
        paths = self._clean()
        frozen = self._write("frozen.json", json.dumps({"version": "1.0.0"}))
        amended = self._write(
            "amended.json",
            json.dumps({"version": "1.1.0", "amended_at": "2026-11-06T00:00:00Z",
                        "amendments": [{"issue": "path redaction"}]}),
        )
        paths["preregistration"] = amended
        paths["frozen_preregistration"] = frozen
        report = audit_integrity(**paths)
        oddc = next(item for item in report["findings"] if item["type"] == "ODDC")
        self.assertEqual(oddc["state"], PASS)

    def test_unimplemented_types_are_not_assessed(self):
        report = audit_integrity(**self._clean())
        unassessed_types = {
            i["type"] for i in report["findings"] if i["state"] == NOT_ASSESSED
        }
        self.assertTrue({"NG", "NVE", "CM", "EDG", "TCE", "EG", "SRM", "CI"} <= unassessed_types)
        self.assertIn("ET", unassessed_types)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["release"], "withhold")

    def test_write_report(self):
        report = audit_integrity(**self._clean())
        written = write_integrity_report(report, self.root / "integrity.json")
        self.assertTrue(Path(written["path"]).is_file())
        self.assertEqual(len(written["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
