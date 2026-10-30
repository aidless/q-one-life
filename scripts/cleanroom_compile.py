#!/usr/bin/env python3
"""Compile a mechanically valid LaTeX source tree in isolated directories."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from qone_life.research import sha256_file
from qone_life.research_factory import audit_arxiv_package


def _pdf_pages(pdf: Path) -> tuple[int | None, str]:
    command = ["pdfinfo", str(pdf)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None, result.stderr.strip()
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    return (int(match.group(1)) if match else None), result.stdout


def _copy_package(source: Path, target: Path, files: list[dict[str, object]]) -> None:
    for entry in files:
        relative = Path(str(entry["path"]))
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


def _run(
    workdir: Path,
    main_file: str,
    capture_stem: str,
    output_dir: Path,
    epoch: int,
) -> dict[str, object]:
    command = [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        main_file,
    ]
    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = str(epoch)
    environment["FORCE_SOURCE_DATE"] = "1"
    result = subprocess.run(
        command,
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_path = output_dir / f"{capture_stem}.stdout.log"
    stderr_path = output_dir / f"{capture_stem}.stderr.log"
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    main_log = workdir / f"{Path(main_file).stem}.log"
    persisted_log = None
    warnings: list[str] = []
    if main_log.is_file():
        persisted_log = output_dir / f"{capture_stem}.main.log"
        shutil.copy2(main_log, persisted_log)
        warnings = [
            line.strip()
            for line in main_log.read_text(encoding="utf-8", errors="replace").splitlines()
            if re.search(r"\b(?:Warning|Underfull|Overfull)\b", line)
        ][:100]
    return {
        "command": command,
        "environment": {
            "SOURCE_DATE_EPOCH": str(epoch),
            "FORCE_SOURCE_DATE": "1",
        },
        "exit_code": result.returncode,
        "workdir": str(workdir),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "main_log": str(persisted_log) if persisted_log else None,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--main", default="main.tex")
    parser.add_argument("--epoch", type=int, default=946684800)
    parser.add_argument("--receipt")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = audit_arxiv_package(source, main_file=args.main)
    if not audit["mechanical_pass"]:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 1

    runs: list[dict[str, object]] = []
    pdf_paths: list[Path] = []
    bbl_paths: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="qone-cleanroom-") as temporary:
        root = Path(temporary)
        for index in (1, 2):
            workdir = root / f"run-{index}"
            workdir.mkdir()
            _copy_package(source, workdir, audit["files"])
            run = _run(
                workdir,
                args.main,
                f"pass{index}",
                output_dir,
                args.epoch,
            )
            runs.append(run)
            pdf = workdir / f"{Path(args.main).stem}.pdf"
            if pdf.is_file():
                persisted_pdf = output_dir / (
                    "main.pdf" if index == 1 else "main-repeat.pdf"
                )
                shutil.copy2(pdf, persisted_pdf)
                pdf_paths.append(persisted_pdf)
            bbl = workdir / f"{Path(args.main).stem}.bbl"
            if bbl.is_file():
                persisted_bbl = output_dir / (
                    "main.bbl" if index == 1 else "main-repeat.bbl"
                )
                shutil.copy2(bbl, persisted_bbl)
                bbl_paths.append(persisted_bbl)

    compile_passed = all(int(run["exit_code"]) == 0 for run in runs) and len(pdf_paths) == 2
    deterministic = (
        compile_passed and sha256_file(pdf_paths[0]) == sha256_file(pdf_paths[1])
    )
    pages, pdfinfo = _pdf_pages(pdf_paths[0]) if pdf_paths else (None, "")
    pdfinfo_path = output_dir / "pdfinfo.txt"
    pdfinfo_path.write_text(pdfinfo, encoding="utf-8")

    generated = [
        *pdf_paths,
        *bbl_paths,
        pdfinfo_path,
        *[Path(str(run["stdout"])) for run in runs],
        *[Path(str(run["stderr"])) for run in runs],
        *[Path(str(run["main_log"])) for run in runs if run["main_log"]],
    ]
    receipt = {
        "schema": "q-one-cleanroom-compile-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "path": str(source),
            "main_file": args.main,
            "main_sha256": sha256_file(source / args.main),
            "package_sha256": audit["package_sha256"],
            "file_count": audit["file_count"],
        },
        "commands": [run["command"] for run in runs],
        "runs": runs,
        "exit_codes": [run["exit_code"] for run in runs],
        "outputs": [
            {
                "path": str(path.relative_to(output_dir.parent)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in generated
        ],
        "pdf": {
            "pages": pages,
            "sha256_run1": sha256_file(pdf_paths[0]) if pdf_paths else None,
            "sha256_run2": sha256_file(pdf_paths[1]) if len(pdf_paths) == 2 else None,
            "deterministic": deterministic,
        },
        "environment": {
            "platform": platform.platform(),
            "latexmk": subprocess.run(
                ["latexmk", "--version"], capture_output=True, text=True, check=False
            ).stdout.splitlines()[:2],
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "Only files admitted by the mechanical package audit were copied.",
            "Two independent clean directories were compiled with a fixed source epoch.",
            "A successful compile is not scientific readiness or upload authorization.",
        ],
    }
    receipt_path = Path(args.receipt) if args.receipt else output_dir / "receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "compile_passed": compile_passed,
                "deterministic_pdf": deterministic,
                "pages": pages,
                "receipt": str(receipt_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if compile_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
