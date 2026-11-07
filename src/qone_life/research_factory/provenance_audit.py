"""Standalone, read-only provenance checks; no experiment or closure is rerun.

Run this file directly with Python, or import audit_provenance / require_provenance.
A git_commit check proves local object existence, not remote origin, ancestry
completeness, or checkout identity. A hash_pinned_archive check proves only the
listed bytes against the supplied manifest. Pin manifest_sha256 out of band when
using either mode as a runner gate. Neither mode authenticates the manifest author.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "q-one-provenance-manifest-v1"
REPORT_SCHEMA = "q-one-provenance-audit-v1"


class ProvenanceError(RuntimeError):
    """A provenance gate failed; report contains the recorded checks."""

    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__("provenance failed: " + ", ".join(report["failed"]))


def manifest_sha256(manifest: dict[str, Any]) -> str:
    """Hash canonical JSON bytes, independently of formatting and key order."""
    canonical = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _directory_descriptor(root: Path) -> int:
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in root.parts[1:]:
            child = os.open(
                component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError:
        os.close(descriptor)
        raise


def _file_sha256(root_descriptor: int, relative: str) -> str:
    if (
        not isinstance(relative, str) or not relative
        or "\\" in relative or ":" in relative or "\0" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ValueError("file path must be a canonical relative POSIX path")
    components = relative.split("/")
    descriptor = os.dup(root_descriptor)
    try:
        for component in components[:-1]:
            child = os.open(
                component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=descriptor,
        )
        with os.fdopen(file_descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("manifest entries must be regular files")
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _git(root: Path, *arguments: str) -> bytes:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_ATTR_NOSYSTEM": "1",
    })
    result = subprocess.run(
        [
            "git", "--no-replace-objects", "-c", "core.hooksPath=/dev/null",
            "-C", str(root), *arguments,
        ],
        capture_output=True, env=environment, timeout=10, check=False,
    )
    if result.returncode:
        raise ValueError("git object check failed (no ref-text fallback)")
    return result.stdout


def audit_provenance(
    root: str | Path,
    manifest: dict[str, Any],
    *,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Return a fail-closed report without modifying the source or Git state.

    Manifest: schema, mode (git_commit or hash_pinned_archive), files
    ([{path, sha256}]); git_commit additionally requires a full commit object ID.
    Files are mandatory for archives and optional for a metadata-only Git audit.
    Git file hashes, when supplied, do not prove membership in the commit tree.
    """
    root_path = Path(os.path.abspath(os.path.expanduser(os.fspath(root))))
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root_path),
        "mode": manifest.get("mode") if isinstance(manifest, dict) else None,
        "status": "failed",
        "manifest_sha256": None,
        "manifest_pin_verified": False,
        "commit_object_verified": False,
        "origin_authenticated": False,
        "working_tree_matches_commit": None,
        "fresh_experiment_rerun": False,
        "files_verified": [],
        "checks": [],
        "failed": [],
        "limitations": [
            "Object existence does not authenticate repository origin or historical cloud state.",
            "File hashes bind listed bytes only; unlisted files are outside this audit.",
            "This audit is not a fresh experiment rerun or scientific closure.",
        ],
    }

    def check(check_id: str, passed: bool, detail: str) -> None:
        report["checks"].append({
            "check_id": check_id, "passed": passed, "detail": detail,
        })
        if not passed:
            report["failed"].append(check_id)

    if not isinstance(manifest, dict):
        check("manifest", False, "manifest must be a JSON object")
        return report
    check("schema", manifest.get("schema") == MANIFEST_SCHEMA, "manifest schema")
    try:
        report["manifest_sha256"] = manifest_sha256(manifest)
    except (TypeError, ValueError):
        check("manifest", False, "manifest must contain finite JSON values")
        return report
    if expected_manifest_sha256 is not None:
        pinned = (
            isinstance(expected_manifest_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256) is not None
            and expected_manifest_sha256 == report["manifest_sha256"]
        )
        report["manifest_pin_verified"] = pinned
        check("manifest_digest", pinned, "canonical manifest SHA-256 pin")
    mode = manifest.get("mode")
    check(
        "mode", mode in ("git_commit", "hash_pinned_archive"),
        "explicit supported provenance mode required; no automatic downgrade",
    )
    try:
        root_descriptor = _directory_descriptor(root_path)
    except OSError:
        check("root", False, "root must exist and contain no symlink components")
        return report
    try:
        check("root", True, "root opened without following symlinks")
        has_dotgit = os.path.lexists(root_path / ".git")
        bare = all((root_path / name).exists() for name in ("HEAD", "objects", "refs"))
        if mode == "git_commit":
            repository_boundary = (
                has_dotgit and not (root_path / ".git").is_symlink()
            ) or bare
            check(
                "repository_boundary", repository_boundary,
                "explicit repository root required; parent repository is not evidence",
            )
            commit_oid = manifest.get("commit")
            valid_oid = (
                isinstance(commit_oid, str)
                and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit_oid) is not None
            )
            check("commit_id", valid_oid, "full hexadecimal commit object ID required")
            if valid_oid and repository_boundary:
                try:
                    object_type = _git(root_path, "cat-file", "-t", commit_oid).strip()
                    if object_type != b"commit":
                        raise ValueError("requested object is not a commit")
                    size = int(_git(root_path, "cat-file", "-s", commit_oid))
                    if not 0 < size <= 8 * 1024 * 1024:
                        raise ValueError("commit metadata size is invalid")
                    payload = _git(root_path, "cat-file", "commit", commit_oid)
                    header = f"commit {len(payload)}\0".encode("ascii")
                    algorithm = "sha1" if len(commit_oid) == 40 else "sha256"
                    actual = hashlib.new(algorithm, header + payload).hexdigest()
                    if len(payload) != size or actual != commit_oid:
                        raise ValueError("commit bytes do not hash to the pinned object ID")
                    tree_type = _git(
                        root_path, "cat-file", "-t", f"{commit_oid}^{{tree}}"
                    ).strip()
                    if tree_type != b"tree":
                        raise ValueError("commit tree object is missing")
                    report["commit"] = commit_oid
                    report["commit_object_verified"] = True
                    check("commit_object", True, "cat-file type, raw object digest and tree verified")
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    check("commit_object", False, "commit object bytes/tree unavailable or invalid")
        elif mode == "hash_pinned_archive":
            check(
                "archive_boundary", not has_dotgit and not bare,
                "archive must contain no Git metadata; a ref stub is not an archive",
            )
        files = manifest.get("files", [])
        valid_files = isinstance(files, list) and (
            bool(files) or mode == "git_commit"
        )
        check("files", valid_files, "archives require a non-empty file manifest")
        seen: set[str] = set()
        if valid_files:
            for index, item in enumerate(files):
                entry: dict[str, Any] = {"index": index, "passed": False}
                try:
                    if not isinstance(item, dict):
                        raise TypeError("file entry must be an object")
                    relative = item.get("path")
                    expected = item.get("sha256")
                    if (
                        not isinstance(relative, str) or relative in seen
                        or not isinstance(expected, str)
                        or re.fullmatch(r"[0-9a-f]{64}", expected) is None
                    ):
                        raise ValueError("invalid or duplicate path/SHA-256 entry")
                    seen.add(relative)
                    actual = _file_sha256(root_descriptor, relative)
                    entry.update(
                        path=relative, sha256=actual, expected_sha256=expected,
                        passed=actual == expected,
                    )
                except (OSError, ValueError, TypeError):
                    entry["error"] = "unsafe, missing, duplicate or invalid file entry"
                report["files_verified"].append(entry)
                check(f"file:{index}", entry["passed"], entry.get("error", "file SHA-256 comparison"))
    finally:
        os.close(root_descriptor)
    report["status"] = "failed" if report["failed"] else "passed"
    return report


def require_provenance(
    root: str | Path,
    manifest: dict[str, Any],
    *,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Runner gate: return verified evidence or raise ProvenanceError."""
    report = audit_provenance(
        root, manifest, expected_manifest_sha256=expected_manifest_sha256,
    )
    if report["status"] != "passed":
        raise ProvenanceError(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", help="out-of-band canonical JSON digest")
    parser.add_argument("--output", help="create a new JSON report; never overwrite")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        report = audit_provenance(
            args.root, manifest, expected_manifest_sha256=args.manifest_sha256,
        )
    except (OSError, ValueError, UnicodeError):
        report = {
            "schema": REPORT_SCHEMA, "status": "failed",
            "failed": ["manifest_input"],
            "error": "manifest could not be read as UTF-8 JSON",
        }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            with Path(args.output).open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        except OSError:
            print(json.dumps({
                "schema": REPORT_SCHEMA, "status": "failed",
                "failed": ["output"], "error": "report output must be a new writable file",
            }))
            return 1
    print(encoded, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
