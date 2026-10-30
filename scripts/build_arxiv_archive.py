#!/usr/bin/env python3
"""Build a deterministic internal arXiv candidate archive and recompile it."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from qone_life.research import sha256_file
from qone_life.research_factory import audit_arxiv_package


def _tarinfo(name: str, *, size: int = 0, mode: int = 0o664, directory: bool = False) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    return info


def _build_archive(source: Path, files: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        archive.addfile(_tarinfo("./", directory=True, mode=0o775))
        directories: set[str] = set()
        for entry in sorted(files, key=lambda item: str(item["path"])):
            relative = Path(str(entry["path"]))
            parents = [
                f"./{parent.as_posix()}/"
                for parent in relative.parents
                if parent != Path(".")
            ]
            for directory in reversed(parents):
                if directory not in directories:
                    archive.addfile(_tarinfo(directory, directory=True, mode=0o775))
                    directories.add(directory)
            path = source / relative
            with path.open("rb") as handle:
                archive.addfile(
                    _tarinfo(f"./{relative.as_posix()}", size=path.stat().st_size),
                    handle,
                )


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            target = destination / member.name
            resolved = target.resolve()
            if destination.resolve() not in resolved.parents and resolved != destination.resolve():
                raise ValueError(f"unsafe archive member: {member.name}")
        archive.extractall(destination, filter="data")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--main", default="main.tex")
    parser.add_argument("--compile-output", required=True)
    parser.add_argument("--blocker", action="append", default=[])
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    receipt_path = Path(args.receipt).expanduser().resolve()
    compile_output = Path(args.compile_output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    audit = audit_arxiv_package(source, main_file=args.main)
    if not audit["mechanical_pass"]:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 1

    with tempfile.TemporaryDirectory(prefix="qone-archive-build-") as temporary:
        root = Path(temporary)
        first = root / "first.tar.gz"
        second = root / "second.tar.gz"
        _build_archive(source, audit["files"], first)
        _build_archive(source, audit["files"], second)
        deterministic = sha256_file(first) == sha256_file(second)
        repeat_hash = sha256_file(second)
        shutil.copy2(first, output)
        extracted = root / "extracted"
        extracted.mkdir()
        _safe_extract(first, extracted)
        compile_receipt = compile_output / "receipt.json"
        command = [
            sys.executable,
            str(Path(__file__).with_name("cleanroom_compile.py")),
            "--source",
            str(extracted),
            "--output-dir",
            str(compile_output),
            "--main",
            args.main,
            "--receipt",
            str(compile_receipt),
        ]
        compile_result = subprocess.run(
            command,
            env={**os.environ},
            capture_output=True,
            text=True,
            check=False,
        )
        compile_stdout = compile_output / "build.stdout.log"
        compile_stderr = compile_output / "build.stderr.log"
        compile_output.mkdir(parents=True, exist_ok=True)
        compile_stdout.write_text(compile_result.stdout, encoding="utf-8")
        compile_stderr.write_text(compile_result.stderr, encoding="utf-8")

    compile_data = (
        json.loads(compile_receipt.read_text(encoding="utf-8"))
        if compile_receipt.is_file()
        else None
    )
    blockers = list(args.blocker)
    blockers.extend(
        [
            "This is an internal candidate archive; no arXiv upload was performed.",
            "Author, category, license, abstract and final metadata remain user decisions.",
            "A compiling archive does not establish scientific readiness or independent review.",
        ]
    )
    receipt = {
        "schema": "q-one-arxiv-candidate-package-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "path": str(source),
            "main_sha256": sha256_file(source / args.main),
            "package_sha256": audit["package_sha256"],
            "file_count": audit["file_count"],
        },
        "archive": {
            "path": str(output),
            "sha256": sha256_file(output),
            "bytes": output.stat().st_size,
            "repeat_sha256": repeat_hash,
            "deterministic": deterministic,
        },
        "entries": audit["files"],
        "extract_compile": {
            "exit_code": compile_result.returncode,
            "receipt": str(compile_receipt),
            "receipt_sha256": sha256_file(compile_receipt)
            if compile_receipt.is_file()
            else None,
            "pdf_pages": compile_data.get("pdf", {}).get("pages")
            if compile_data
            else None,
            "pdf_sha256": compile_data.get("pdf", {}).get("sha256_run1")
            if compile_data
            else None,
            "command_stdout": str(compile_stdout),
            "command_stderr": str(compile_stderr),
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "ready_for_upload": False,
        "blockers": blockers,
        "notes": [
            "The archive uses sorted entries and normalized owner, mode and mtime.",
            "The archive was extracted into a separate temporary directory before compilation.",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "archive": str(output),
                "sha256": receipt["archive"]["sha256"],
                "deterministic": deterministic,
                "compile_exit_code": compile_result.returncode,
                "pdf_pages": receipt["extract_compile"]["pdf_pages"],
                "ready_for_upload": False,
            },
            indent=2,
        )
    )
    return 0 if deterministic and compile_result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
