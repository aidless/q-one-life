import json
import tempfile
import unittest
from pathlib import Path

from qone_life.cloud_executor import (
    MAX_DISK_GB,
    MAX_RUNTIME_SEC,
    CloudExecutionError,
    CloudExecutor,
)


def _job(root: Path, **overrides) -> Path:
    job_dir = root / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    script = job_dir / "run.sh"
    script.write_text("#!/bin/bash\nmkdir -p outputs\nprintf 'ok' > outputs/result.txt\n", encoding="utf-8")
    script.chmod(0o755)
    (job_dir / "input.txt").write_text("payload", encoding="utf-8")
    job = {
        "job_id": "test-job",
        "run_script": "run.sh",
        "inputs": ["input.txt"],
        "max_runtime_sec": 60,
        "max_disk_gb": 1,
    }
    job.update(overrides)
    (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
    return job_dir


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.executor = CloudExecutor(timeout=5)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_job_json(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(empty)

    def test_missing_run_script(self):
        job_dir = _job(self.root)
        (job_dir / "run.sh").unlink()
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_runtime_above_limit_rejected(self):
        job_dir = _job(self.root, max_runtime_sec=MAX_RUNTIME_SEC + 1)
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_disk_above_limit_rejected(self):
        job_dir = _job(self.root, max_disk_gb=MAX_DISK_GB + 1)
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_zero_runtime_rejected(self):
        job_dir = _job(self.root, max_runtime_sec=0)
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_absolute_input_rejected(self):
        job_dir = _job(self.root, inputs=["/etc/passwd"])
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_parent_traversal_rejected(self):
        job_dir = _job(self.root, inputs=["../escape.txt"])
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_missing_input_rejected(self):
        job_dir = _job(self.root, inputs=["missing.txt"])
        with self.assertRaises(CloudExecutionError):
            self.executor._validate_job(job_dir)

    def test_valid_job_passes(self):
        job_dir = _job(self.root)
        job = self.executor._validate_job(job_dir)
        self.assertEqual(job["job_id"], "test-job")


if __name__ == "__main__":
    unittest.main()
