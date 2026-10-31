"""arXiv 打包审计与原生数字台账审计。

本模块只做**机械性**检查：文件是否齐全、引用是否可解析、占位符是否清理、
台账数字能否对上源文件字段。它**不能**证明科学结论正确、许可合规或可上传。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..research import sha256_file
from ._helpers import (
    ABSOLUTE_PATH_RE,
    GRAPHICSPATH_RE,
    NATIVE_LEDGER_SCHEMA,
    PACKAGE_AUXILIARY_SUFFIXES,
    PACKAGE_SCHEMA,
    PLACEHOLDER_RE,
    REFERENCE_RE,
    ResearchFactoryError,
    _collect_package_files,
    _load_json,
    _now,
    _numeric_match,
    _resolve_json_path,
    _resolve_reference,
    _strip_tex_comments,
    _write_json,
)


def audit_arxiv_package(
    source_dir: str | Path,
    *,
    main_file: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """审计一棵 LaTeX 源码树，判断它是否满足机械打包要求。

    返回的 blockers 表示必须解决的问题；warnings 表示需要人工确认的疑点。
    无论是否通过，ready_for_upload 一律为 False——上传还需独立的许可与授权。
    """
    root = Path(source_dir).expanduser().resolve()
    if not root.is_dir():
        raise ResearchFactoryError(f"source directory is missing: {root}")

    timestamp = generated_at or _now()
    main = root / (main_file or "main.tex")
    blockers: list[str] = []
    warnings: list[str] = []

    if not main.is_file():
        blockers.append(f"main manuscript is missing: {main_file or 'main.tex'}")

    files, symlink_blockers = _collect_package_files(root)
    blockers.extend(symlink_blockers)
    file_paths = [str(path.relative_to(root)) for path in files]

    # 主文件正文（去掉注释后再做结构检查）。
    main_text = main.read_text(encoding="utf-8", errors="replace") if main.is_file() else ""
    main_check = _strip_tex_comments(main_text)

    # 收集所有 .tex 文本（同样去注释），后续统一做路径/占位符/引用检查。
    tex_texts: dict[str, str] = {}
    for path in files:
        if path.suffix.lower() != ".tex":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tex_texts[path.relative_to(root).as_posix()] = _strip_tex_comments(text)

    if main_check:
        if "\\begin{document}" not in main_check:
            blockers.append("main manuscript has no begin document marker")
        if "\\title" not in main_check:
            blockers.append("main manuscript has no title")

    # 逐文件检查绝对路径、未清理占位符、可疑的未解析引用，并收集 \graphicspath。
    graphics_paths: list[Path] = []
    for name, text in tex_texts.items():
        if ABSOLUTE_PATH_RE.search(text):
            blockers.append(f"absolute local path in {name}")

        placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
        if placeholders:
            blockers.append(f"unresolved placeholders in {name}: " + ", ".join(placeholders))

        if "??" in text:
            warnings.append(f"found '??' in {name}; confirm it is not an unresolved reference")

        graphics_match = GRAPHICSPATH_RE.search(text)
        if graphics_match:
            for value in re.findall(r"\{([^}]+)\}", graphics_match.group(1)):
                graphics_paths.append(root / value)

    # 检查 \input / \include / \includegraphics / \bibliography 等引用目标是否存在。
    for name, text in tex_texts.items():
        for match in REFERENCE_RE.finditer(text):
            kind = match.group("kind")
            target = match.group("target").strip()
            if not _resolve_reference(root, target, kind, graphics_paths=graphics_paths):
                blockers.append(f"referenced {kind} target is missing in {name}: {target}")

    # 是否存在参考文献来源：.bib / .bbl 文件，或内联的 thebibliography 环境。
    has_bibliography = any(path.suffix in {".bib", ".bbl"} for path in files)
    if not has_bibliography:
        for path in files:
            if path.name != "bibliography.tex":
                continue
            try:
                bibliography_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                bibliography_text = ""
            if "\\begin{thebibliography}" in bibliography_text:
                has_bibliography = True
                break

    combined_text = "\n".join(tex_texts.values())
    if "\\cite" in combined_text and not has_bibliography:
        blockers.append("citation commands are present but no .bib or .bbl file exists")

    # 构建产物（.aux/.log 等）与隐藏文件不应进入上传包，给出警告。
    auxiliary = sorted(
        path for path in file_paths if Path(path).suffix.lower() in PACKAGE_AUXILIARY_SUFFIXES
    )
    if auxiliary:
        warnings.append("build auxiliary files should be excluded: " + ", ".join(auxiliary[:12]))

    hidden = sorted(
        path for path in file_paths if any(part.startswith(".") for part in Path(path).parts)
    )
    if hidden:
        warnings.append("hidden files should be reviewed before upload: " + ", ".join(hidden[:12]))

    # 记录每个文件的相对路径、哈希与大小。
    file_records = []
    for path in files:
        relative = path.relative_to(root)
        file_records.append(
            {
                "path": str(relative),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )

    # 包哈希覆盖「排序后的路径+哈希清单」，而不是 tar 字节流。
    manifest_lines = []
    for item in file_records:
        manifest_lines.append(f"{item['path']}\0{item['sha256']}")
    package_sha256 = hashlib.sha256("\n".join(manifest_lines).encode("utf-8")).hexdigest()

    mechanical_pass = not blockers
    return {
        "schema": PACKAGE_SCHEMA,
        "generated_at": timestamp,
        "source_dir": str(root),
        "main_file": str(main),
        "mechanical_pass": mechanical_pass,
        "ready_for_upload": False,
        "upload_blocker": (
            "Mechanical packaging does not establish scientific readiness, license, "
            "metadata correctness, or user authorization."
        ),
        "blockers": blockers,
        "warnings": warnings,
        "file_count": len(files),
        "visible_suffixes": dict(
            sorted(Counter(path.suffix.lower() or "<none>" for path in files).items())
        ),
        "files": file_records,
        "package_sha256": package_sha256,
        "notes": [
            "This is a source-tree audit, not a clean-room LaTeX compile.",
            "The package hash covers the sorted path/hash manifest, not tar bytes.",
        ],
    }


def write_package_audit(
    audit: dict[str, Any],
    output: str | Path,
) -> None:
    """把打包审计结果写成 JSON 文件。"""
    _write_json(output, audit)


def audit_native_paper_ledger(
    ledger_path: str | Path,
    workspace_root: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """审计一份原生数字台账，只读不改写。

    识别 Q-One 论文台账的常见结构：每个条目带 source、value，并具备以下之一：
    field（从源文件字段取值核对）、derived（命名派生，只登记不执行）、
    field_waiver（显式豁免）或 recoverable=False（不可恢复，显式撤回）。
    """
    ledger = Path(ledger_path).expanduser().resolve()
    root = Path(workspace_root).expanduser().resolve()
    timestamp = generated_at or _now()
    payload = _load_json(ledger)

    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ResearchFactoryError("native ledger must contain an entries array")

    counts: Counter[str] = Counter()
    issues: list[dict[str, Any]] = []
    verified_entries: list[dict[str, Any]] = []

    for index, entry in enumerate(entries):
        counts["entries_total"] += 1
        if not isinstance(entry, dict):
            counts["invalid_entry"] += 1
            issues.append({"index": index, "issue": "entry is not an object"})
            continue

        key = str(entry.get("key") or f"entry-{index}")
        source_value = entry.get("source")
        field = entry.get("field")
        derived = entry.get("derived")
        waiver = entry.get("field_waiver")
        recoverable = entry.get("recoverable")

        if isinstance(field, str) and isinstance(source_value, str):
            # field 绑定型：从源文件的 JSON 字段里取实际值，与声称值比较。
            counts["field_bound_total"] += 1
            source = (root / source_value).resolve()
            if not source.is_file():
                counts["missing_source_file"] += 1
                issues.append(
                    {"key": key, "issue": "missing source file", "source": source_value}
                )
                continue
            if source.suffix.lower() == ".json":
                try:
                    carrier = json.loads(source.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError):
                    counts["unparseable_source"] += 1
                    issues.append(
                        {"key": key, "issue": "unparseable source", "source": source_value}
                    )
                    continue

                actual = _resolve_json_path(carrier, field)
                if actual is None:
                    counts["missing_field"] += 1
                    issues.append(
                        {
                            "key": key,
                            "issue": "missing field",
                            "source": source_value,
                            "field": field,
                        }
                    )
                    continue

                if not _numeric_match(entry.get("value"), actual):
                    counts["value_mismatch"] += 1
                    issues.append(
                        {
                            "key": key,
                            "issue": "value mismatch",
                            "source": source_value,
                            "field": field,
                            "claimed": entry.get("value"),
                            "actual": actual,
                        }
                    )
                    continue

            counts["field_verified"] += 1
            verified_entries.append(
                {
                    "key": key,
                    "value": entry.get("value"),
                    "source": source_value,
                    "field": field,
                }
            )
        elif isinstance(derived, str):
            counts["named_derivation"] += 1
        elif isinstance(waiver, str):
            counts["field_waiver"] += 1
        elif recoverable is False:
            counts["unrecoverable_retraction"] += 1
        else:
            counts["unbound_register"] += 1

    # 只要出现任一硬缺陷，机械有效性即为 False。
    hard_defects = (
        "invalid_entry",
        "missing_source_file",
        "unparseable_source",
        "missing_field",
        "value_mismatch",
    )
    mechanically_valid = True
    for defect_key in hard_defects:
        if counts[defect_key]:
            mechanically_valid = False
            break

    return {
        "schema": NATIVE_LEDGER_SCHEMA,
        "generated_at": timestamp,
        "ledger": str(ledger),
        "ledger_sha256": sha256_file(ledger),
        "workspace_root": str(root),
        "mechanically_valid": mechanically_valid,
        "scientific_ready": False,
        "counts": dict(sorted(counts.items())),
        "issues": issues,
        "verified_entries_sample": verified_entries[:20],
        "notes": [
            "Named derivations are retained as candidates; this audit does not execute them.",
            "Field waivers and unrecoverable retractions are not silently converted to verified.",
            "A mechanically valid native ledger does not establish scientific readiness.",
        ],
    }


def write_native_ledger_audit(
    audit: dict[str, Any],
    output: str | Path,
    *,
    markdown: str | Path | None = None,
) -> None:
    """写出原生台账审计：JSON 必写，Markdown 按需写出。"""
    _write_json(output, audit)

    if markdown is None:
        return

    lines = [
        "# Native paper ledger audit",
        "",
        f"Ledger: `{audit['ledger']}`",
        f"SHA-256: `{audit['ledger_sha256']}`",
        f"Mechanically valid: `{audit['mechanically_valid']}`",
        f"Scientific ready: `{audit['scientific_ready']}`",
        "",
        "## Counts",
        "",
        "| Measure | Value |",
        "|---|---:|",
    ]
    for key, value in audit["counts"].items():
        lines.append(f"| {key} | {value} |")

    if audit["issues"]:
        lines.extend(["", "## Issues", "", "| Key | Issue | Source | Field |", "|---|---|---|---|"])
        for issue in audit["issues"][:100]:
            lines.append(
                f"| {issue.get('key', '')} | {issue.get('issue', '')} | "
                f"{issue.get('source', '')} | {issue.get('field', '')} |"
            )

    target = Path(markdown)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
