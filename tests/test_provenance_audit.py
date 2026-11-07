import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/qone_life/research_factory/provenance_audit.py"
)
SPEC = importlib.util.spec_from_file_location("provenance_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
if MODULE_PATH.is_file():
    SPEC.loader.exec_module(AUDIT)


class ProvenanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = self.root / "input.txt"
        self.payload.write_bytes(b"source bytes\n")
        self.manifest = {
            "schema": "q-one-provenance-manifest-v1",
            "mode": "hash_pinned_archive",
            "files": [{
                "path": "input.txt",
                "sha256": hashlib.sha256(b"source bytes\n").hexdigest(),
            }],
        }

    def audit(self):
        self.assertTrue(
            hasattr(AUDIT, "audit_provenance"), "standalone audit API is missing"
        )
        return AUDIT.audit_provenance(self.root, self.manifest)

    def repository(self, with_object=True):
        metadata = self.root / ".git"
        (metadata / "objects").mkdir(parents=True)
        (metadata / "refs").mkdir()
        tree_bytes = b"tree 0\0"
        tree_oid = hashlib.sha1(tree_bytes).hexdigest()
        commit = (
            f"tree {tree_oid}\n"
            "author Fixture <fixture@example.invalid> 0 +0000\n"
            "committer Fixture <fixture@example.invalid> 0 +0000\n\n"
            "temporary object fixture\n"
        ).encode()
        commit_bytes = f"commit {len(commit)}\0".encode() + commit
        commit_oid = hashlib.sha1(commit_bytes).hexdigest()
        if with_object:
            for raw in (tree_bytes, commit_bytes):
                object_oid = hashlib.sha1(raw).hexdigest()
                object_path = metadata / "objects" / object_oid[:2] / object_oid[2:]
                object_path.parent.mkdir(exist_ok=True)
                object_path.write_bytes(zlib.compress(raw))
        (metadata / "HEAD").write_text(commit_oid + "\n", encoding="ascii")
        self.manifest.update(mode="git_commit", commit=commit_oid)
        return commit_oid

    def test_api_exists(self):
        self.assertTrue(hasattr(AUDIT, "audit_provenance"))
        self.assertTrue(hasattr(AUDIT, "require_provenance"))

    def test_fake_head_text_is_not_a_commit_object(self):
        commit_oid = self.repository(with_object=False)
        textual = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(textual.stdout.strip(), commit_oid)
        report = self.audit()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["commit_object_verified"])

    def test_real_commit_object_passes_without_claiming_origin(self):
        self.repository()
        report = self.audit()
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["commit_object_verified"])
        self.assertFalse(report["origin_authenticated"])
        self.assertIsNone(report["working_tree_matches_commit"])
        self.assertFalse(report["fresh_experiment_rerun"])

    def test_blob_oid_cannot_substitute_for_commit(self):
        self.repository()
        raw = b"blob 5\0hello"
        object_oid = hashlib.sha1(raw).hexdigest()
        destination = self.root / ".git/objects" / object_oid[:2] / object_oid[2:]
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(zlib.compress(raw))
        self.manifest["commit"] = object_oid
        self.assertEqual(self.audit()["status"], "failed")

    def test_git_mode_does_not_inherit_parent_repository(self):
        self.repository()
        child = self.root / "archive"
        child.mkdir()
        report = AUDIT.audit_provenance(child, self.manifest)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["commit_object_verified"])

    def test_git_environment_cannot_supply_missing_object(self):
        self.repository(with_object=False)
        with patch.dict(os.environ, {"GIT_OBJECT_DIRECTORY": "/nonexistent/objects"}):
            self.assertEqual(self.audit()["status"], "failed")

    def test_external_environment_objects_cannot_rescue_fake_repository(self):
        self.repository()
        objects = self.root / ".git/objects"
        external = self.root / "external-objects"
        objects.rename(external)
        objects.mkdir()
        with patch.dict(os.environ, {
            "GIT_OBJECT_DIRECTORY": str(external),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(external),
        }):
            self.assertEqual(self.audit()["status"], "failed")

    def test_git_environment_cannot_redirect_real_repository(self):
        self.repository()
        with patch.dict(os.environ, {"GIT_DIR": "/nonexistent/.git"}):
            self.assertEqual(self.audit()["status"], "passed")

    def test_git_replace_ref_cannot_rescue_fake_commit(self):
        real_oid = self.repository()
        fake_oid = "a" * 40
        replacement = self.root / ".git/refs/replace" / fake_oid
        replacement.parent.mkdir()
        replacement.write_text(real_oid + "\n", encoding="ascii")
        self.manifest["commit"] = fake_oid
        self.assertEqual(self.audit()["status"], "failed")

    def test_archive_passes_with_explicit_limited_evidence(self):
        report = self.audit()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["mode"], "hash_pinned_archive")
        self.assertFalse(report["commit_object_verified"])
        self.assertFalse(report["origin_authenticated"])

    def test_archive_file_mismatch_fails(self):
        self.payload.write_bytes(b"modified\n")
        self.assertEqual(self.audit()["status"], "failed")

    def test_archive_missing_file_fails(self):
        self.payload.unlink()
        self.assertEqual(self.audit()["status"], "failed")

    def test_duplicate_paths_and_special_files_fail(self):
        self.manifest["files"].append(dict(self.manifest["files"][0]))
        self.assertEqual(self.audit()["status"], "failed")
        self.manifest["files"].pop()
        self.payload.unlink()
        os.mkfifo(self.payload)
        self.assertEqual(self.audit()["status"], "failed")

    def test_archive_empty_or_malformed_file_bundle_fails(self):
        for files in ([], None, {}, ["input.txt"], [{"path": "input.txt"}]):
            with self.subTest(files=files):
                self.manifest["files"] = files
                self.assertEqual(self.audit()["status"], "failed")

    def test_escape_and_noncanonical_paths_fail(self):
        for relative in (
            "../outside", "/etc/passwd", "folder/../../input.txt",
            "./input.txt", "folder/../input.txt", "C:\\input.txt",
            "folder\\input.txt", "input.txt/.", "input.txt//extra", "",
        ):
            with self.subTest(path=relative):
                self.manifest["files"][0]["path"] = relative
                self.assertEqual(self.audit()["status"], "failed")

    def test_symlink_file_fails_even_for_in_root_target(self):
        (self.root / "link.txt").symlink_to(self.payload)
        self.manifest["files"][0]["path"] = "link.txt"
        self.assertEqual(self.audit()["status"], "failed")

    def test_symlink_directory_and_root_fail(self):
        (self.root / "link").symlink_to(self.root, target_is_directory=True)
        self.manifest["files"][0]["path"] = "link/input.txt"
        self.assertEqual(self.audit()["status"], "failed")
        self.manifest["files"][0]["path"] = "input.txt"
        report = AUDIT.audit_provenance(self.root / "link", self.manifest)
        self.assertEqual(report["status"], "failed")

    def test_archive_cannot_hide_fake_git_metadata(self):
        self.repository(with_object=False)
        self.manifest["mode"] = "hash_pinned_archive"
        self.assertEqual(self.audit()["status"], "failed")

    def test_unknown_mode_or_schema_fails(self):
        self.manifest["mode"] = "rev_parse_only"
        self.assertEqual(self.audit()["status"], "failed")
        self.manifest["mode"] = "hash_pinned_archive"
        self.manifest["schema"] = "other"
        self.assertEqual(self.audit()["status"], "failed")

    def test_manifest_digest_pin_rejects_tampering(self):
        self.assertTrue(hasattr(AUDIT, "manifest_sha256"))
        pinned = AUDIT.manifest_sha256(self.manifest)
        self.manifest["files"][0]["sha256"] = "0" * 64
        report = AUDIT.audit_provenance(
            self.root, self.manifest, expected_manifest_sha256=pinned,
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("manifest_digest", report["failed"])

    def test_fail_closed_runner_api(self):
        self.assertTrue(hasattr(AUDIT, "require_provenance"))
        self.assertEqual(
            AUDIT.require_provenance(self.root, self.manifest)["status"], "passed"
        )
        self.payload.write_bytes(b"tampered")
        with self.assertRaises(AUDIT.ProvenanceError):
            AUDIT.require_provenance(self.root, self.manifest)

    def test_cli_runs_without_package_imports_and_returns_failure_code(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        command = [
            sys.executable, "-I", "-B", str(MODULE_PATH),
            "--root", str(self.root), "--manifest", str(manifest_path),
        ]
        passed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(json.loads(passed.stdout)["status"], "passed")
        self.payload.write_bytes(b"tampered")
        failed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertEqual(json.loads(failed.stdout)["status"], "failed")

    def test_cli_rejects_invalid_json_without_traceback(self):
        manifest_path = self.root / "broken.json"
        manifest_path.write_text("{", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, "-I", "-B", str(MODULE_PATH),
                "--root", str(self.root), "--manifest", str(manifest_path),
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "failed")
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_never_overwrites_existing_output(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        output = self.root / "existing.json"
        output.write_bytes(b"original evidence")
        result = subprocess.run(
            [
                sys.executable, "-I", "-B", str(MODULE_PATH),
                "--root", str(self.root), "--manifest", str(manifest_path),
                "--output", str(output),
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output.read_bytes(), b"original evidence")


if __name__ == "__main__":
    unittest.main()
