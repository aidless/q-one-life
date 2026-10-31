"""Regression tests: local life-data JSONL stores must be owner-only.

SECURITY.md promises OS-ACL protection. Before this guard, ``open(path, "a")``
created the append-only files with ``0o666 & ~umask`` (observed ``0o664``),
group/world-readable. These tests lock in: data file ``<= 0o600`` and parent
directory owner-only, even when a loose file already exists.
"""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from qone_life.measurement import MeasurementStore
from qone_life.store import LifeStore


@unittest.skipIf(os.name != "posix", "POSIX file modes only")
class FilePermissionTests(unittest.TestCase):
    def _assert_secure(self, path: Path) -> None:
        self.assertTrue(path.exists(), f"{path} should exist after append")
        mode = stat.S_IMODE(path.stat().st_mode)
        self.assertEqual(mode & 0o077, 0, f"{path.name} mode {oct(mode)} is group/world accessible")
        self.assertLessEqual(mode, 0o600, f"{path.name} mode {oct(mode)} exceeds 0o600")
        dir_mode = stat.S_IMODE(path.parent.stat().st_mode)
        self.assertEqual(dir_mode & 0o077, 0, f"dir mode {oct(dir_mode)} is group/world accessible")

    def test_life_store_creates_owner_only_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            LifeStore(path).append("observation_recorded", {"index": 1})
            self._assert_secure(path)

    def test_measurement_store_creates_owner_only_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "measurements.jsonl"
            MeasurementStore(path).add("experiment_run", "s", "m", 1, "u", "definition", "source")
            self._assert_secure(path)

    def test_existing_loose_file_is_tightened(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            path.write_text("", encoding="utf-8")
            os.chmod(path, 0o664)
            LifeStore(path).append("observation_recorded", {"index": 1})
            self._assert_secure(path)


if __name__ == "__main__":
    unittest.main()
