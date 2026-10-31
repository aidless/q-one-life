#!/usr/bin/env python3
"""在隔离目录中编译一份通过机械校验的 LaTeX 源码树。

流程：先做 arXiv 包机械审计（缺引用、绝对路径、占位符等），通过后在两个
独立的临时目录里各编译一次，比较两次产出的 PDF 是否逐字节相同，以此判断
构建是否可复现。最后落一份 receipt（回执）记录命令、退出码与产物哈希。
"""

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
    """用 pdfinfo 读取 PDF 页数；失败时返回 (None, stderr)。"""
    command = ["pdfinfo", str(pdf)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None, result.stderr.strip()
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    pages = None
    if match:
        pages = int(match.group(1))
    return pages, result.stdout


def _copy_package(source: Path, target: Path, files: list[dict[str, object]]) -> None:
    """只把审计放行的文件复制到目标目录（保持原目录层级）。"""
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
    """在一个目录里跑一次 latexmk，并把日志与告警收进回执。"""
    command = [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        main_file,
    ]
    environment = dict(os.environ)
    # 固定时间戳，让同一份源码在不同机器上产出同样的 PDF。
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

    # 把 latexmk 的主日志一并留存，并从中摘出前 100 条告警行。
    main_log = workdir / f"{Path(main_file).stem}.log"
    persisted_log = None
    warnings: list[str] = []
    if main_log.is_file():
        persisted_log = output_dir / f"{capture_stem}.main.log"
        shutil.copy2(main_log, persisted_log)
        for line in main_log.read_text(encoding="utf-8", errors="replace").splitlines():
            if len(warnings) >= 100:
                break
            if re.search(r"\b(?:Warning|Underfull|Overfull)\b", line):
                warnings.append(line.strip())
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
    """审计、两轮隔离编译、比对 PDF 一致性，并写出回执。"""
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
        # 机械审计不通过时直接打印审计结果并退出，不做编译。
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 1

    runs: list[dict[str, object]] = []
    pdf_paths: list[Path] = []
    bbl_paths: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="qone-cleanroom-") as temporary:
        root = Path(temporary)
        # 跑两轮完全独立的编译，用来判断构建是否可复现。
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
                if index == 1:
                    persisted_pdf = output_dir / "main.pdf"
                else:
                    persisted_pdf = output_dir / "main-repeat.pdf"
                shutil.copy2(pdf, persisted_pdf)
                pdf_paths.append(persisted_pdf)

            bbl = workdir / f"{Path(args.main).stem}.bbl"
            if bbl.is_file():
                if index == 1:
                    persisted_bbl = output_dir / "main.bbl"
                else:
                    persisted_bbl = output_dir / "main-repeat.bbl"
                shutil.copy2(bbl, persisted_bbl)
                bbl_paths.append(persisted_bbl)

    # 两轮都退出码 0 且都产出了 PDF，才算编译通过。
    compile_passed = all(int(run["exit_code"]) == 0 for run in runs) and len(pdf_paths) == 2
    deterministic = False
    if compile_passed:
        deterministic = sha256_file(pdf_paths[0]) == sha256_file(pdf_paths[1])

    pages = None
    pdfinfo = ""
    if pdf_paths:
        pages, pdfinfo = _pdf_pages(pdf_paths[0])
    pdfinfo_path = output_dir / "pdfinfo.txt"
    pdfinfo_path.write_text(pdfinfo, encoding="utf-8")

    # 汇总本次生成的全部产物（PDF、bbl、pdfinfo、两轮日志）。
    generated: list[Path] = []
    generated.extend(pdf_paths)
    generated.extend(bbl_paths)
    generated.append(pdfinfo_path)
    for run in runs:
        generated.append(Path(str(run["stdout"])))
        generated.append(Path(str(run["stderr"])))
        if run["main_log"]:
            generated.append(Path(str(run["main_log"])))

    # 逐个计算产物哈希与大小，写进回执的 outputs 字段。
    outputs = []
    for path in generated:
        outputs.append(
            {
                "path": str(path.relative_to(output_dir.parent)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )

    sha1 = None
    sha2 = None
    if pdf_paths:
        sha1 = sha256_file(pdf_paths[0])
    if len(pdf_paths) == 2:
        sha2 = sha256_file(pdf_paths[1])

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
        "outputs": outputs,
        "pdf": {
            "pages": pages,
            "sha256_run1": sha1,
            "sha256_run2": sha2,
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
