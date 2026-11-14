import hashlib
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.environment_manifest import (
    ENVIRONMENT_SCHEMA,
    EnvironmentError,
    lock_environment,
    validate_environment,
    write_environment_validation,
)


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data.csv"
        self.data.write_text("a,b\n1,2\n", encoding="utf-8")
        self.digest = hashlib.sha256(self.data.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def _manifest(self):
        return {
            "schema": ENVIRONMENT_SCHEMA,
            "environment_id": "env-1",
            "paper": {"title": "T", "url": "https://arxiv.org/abs/1234.5678"},
            "datasets": [{"path": "data.csv", "sha256": self.digest}],
            "baseline_metrics": {"accuracy": 0.9},
            "tolerance": 0.01,
            "run_command": "python run.py",
            "max_runtime_sec": 600,
            "max_disk_gb": 5,
            "expected_outputs": ["outputs/metrics.json"],
        }

    def test_valid_manifest(self):
        report = validate_environment(self._manifest(), self.root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failed"], [])

    def test_hash_mismatch(self):
        manifest = self._manifest()
        manifest["datasets"][0]["sha256"] = "0" * 64
        report = validate_environment(manifest, self.root)
        self.assertEqual(report["status"], "failed")
        self.assertIn("datasets", report["failed"])

    def test_missing_dataset(self):
        manifest = self._manifest()
        manifest["datasets"][0]["path"] = "missing.csv"
        report = validate_environment(manifest, self.root)
        self.assertIn("datasets", report["failed"])

    def test_over_limit(self):
        manifest = self._manifest()
        manifest["max_runtime_sec"] = 999999
        manifest["max_disk_gb"] = 999
        report = validate_environment(manifest, self.root)
        self.assertIn("runtime_limit", report["failed"])
        self.assertIn("disk_limit", report["failed"])

    def test_missing_metrics(self):
        manifest = self._manifest()
        manifest["baseline_metrics"] = {}
        report = validate_environment(manifest, self.root)
        self.assertIn("baseline_metrics", report["failed"])

    def test_lock_is_stable(self):
        manifest = self._manifest()
        self.assertEqual(lock_environment(manifest), lock_environment(dict(manifest)))

    def test_write_report(self):
        report = validate_environment(self._manifest(), self.root)
        written = write_environment_validation(report, self.root / "env.json")
        self.assertTrue(Path(written["path"]).is_file())
        self.assertEqual(len(written["sha256"]), 64)

    def test_non_object_manifest(self):
        with self.assertRaises(EnvironmentError):
            validate_environment([], self.root)


if __name__ == "__main__":
    unittest.main()
