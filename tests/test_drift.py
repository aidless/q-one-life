"""Tree drift checks. Stdlib only; importing this file does not load a model."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DriftTests(unittest.TestCase):
    def test_versions_docs_and_workflows_match_the_tree(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_drift.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
