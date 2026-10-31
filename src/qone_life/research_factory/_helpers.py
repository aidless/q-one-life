"""research_factory 的共享底层工具。

这里集中放置跨子模块复用的常量、正则与小函数（路径归一、时间解析、
信号合并、数字容差等）。它们被 triage / scaffold / package 共同引用。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
import re
import subprocess
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# 各报告/记录使用的 schema 版本号。
TRIAGE_SCHEMA = "q-one-research-triage-v1"
SCAFFOLD_SCHEMA = "q-one-research-scaffold-v1"
PLAN_SCHEMA = "q-one-research-plan-v1"
PACKAGE_SCHEMA = "q-one-arxiv-package-audit-v1"
NATIVE_LEDGER_SCHEMA = "q-one-native-ledger-audit-v1"
SOURCE_LINEAGE_SCHEMA = "q-one-source-lineage-v1"

# LaTeX 构建产物后缀：不应进入上传包。
PACKAGE_AUXILIARY_SUFFIXES = {
    ".aux",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex",
    ".toc",
}

# 未清理的占位符标记（TODO/FIXME/[CITE] 等）。
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|FIXME|TBD|XXX)\b|\[(?:CITE|REF|TODO)\]")
# LaTeX 引用命令：\input / \include / \includegraphics / \bibliography / \addbibresource。
REFERENCE_RE = re.compile(
    r"\\(?P<kind>input|include|includegraphics|bibliography|addbibresource)"
    r"\s*(?:\[[^\]]*\])?\s*\{(?P<target>[^}]+)\}"
)
# \graphicspath{{...}} 里的一组图片目录。
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{((?:\{[^}]+\})+)\}")
# 绝对本地路径（Linux/macOS/Windows 盘符）——不应出现在源码里。
ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s{(\"'])(?:/home/|/Users/|/mnt/|[A-Za-z]:[\\/][A-Za-z0-9_])"
)


class ResearchFactoryError(ValueError):
    """当某项工厂操作不安全或含义不明确时抛出。"""


def _git_output(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    """在指定仓库里运行一条 git 命令并返回结果（失败时抛 CalledProcessError）。"""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=text,
    )


def audit_git_source_lineage(
    repo_root: str | Path,
    *,
    commit: str,
    path: str,
    expected_sha256: str,
    current_path: str | Path,
    generated_at: str | None = None,
    max_diff_lines: int = 400,
) -> dict[str, Any]:
    """从 git 中取回清单点名的源文件，并与当前的派生版本对比。

    这里证明的是**源码血缘**，不是发表身份。它不会写入源仓库，也不会把
    文本相似度当作科学结论。
    """
    repo = Path(repo_root).expanduser().resolve()
    if not (repo / ".git").exists():
        raise ResearchFactoryError(f"not a git worktree: {repo}")
    if path.startswith("/") or ".." in path.split("/"):
        raise ResearchFactoryError("source lineage path must be repository-relative")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ResearchFactoryError("expected_sha256 must be a lowercase SHA-256")
    if max_diff_lines < 1:
        raise ResearchFactoryError("max_diff_lines must be positive")

    # 解析 commit 的完整哈希。
    try:
        resolved = _git_output(
            repo, "rev-parse", "--verify", f"{commit}^{{commit}}", text=True
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ResearchFactoryError(f"git commit cannot be resolved: {commit}") from exc

    # 取回该 commit 下的文件字节，并读取 commit 元信息（哈希/时间/标题）。
    try:
        blob = _git_output(repo, "show", f"{resolved}:{path}").stdout
        commit_info = _git_output(
            repo,
            "show",
            "-s",
            "--format=%H%n%aI%n%s",
            resolved,
            text=True,
        ).stdout.splitlines()
    except subprocess.CalledProcessError as exc:
        raise ResearchFactoryError(
            f"git path cannot be recovered at {resolved}: {path}"
        ) from exc

    recovered_sha256 = hashlib.sha256(blob).hexdigest()
    expected_ok = recovered_sha256 == expected_sha256

    # 读取当前派生文件（若存在）并比较字节与哈希。
    current = Path(current_path).expanduser().resolve()
    current_exists = current.is_file()
    current_bytes = current.read_bytes() if current_exists else b""
    current_sha256 = hashlib.sha256(current_bytes).hexdigest() if current_exists else None
    same_bytes = current_exists and current_bytes == blob

    # 生成统一 diff，并统计新增/删除行数。
    old_text = blob.decode("utf-8", errors="replace")
    new_text = current_bytes.decode("utf-8", errors="replace")
    diff_lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=f"{resolved}:{path}",
            tofile=str(current),
            lineterm="",
        )
    )
    diff_text = "\n".join(diff_lines) + ("\n" if diff_lines else "")

    added = 0
    removed = 0
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        if line.startswith("-") and not line.startswith("---"):
            removed += 1

    diff_is_truncated = len(diff_lines) > max_diff_lines
    shown_diff = "\n".join(diff_lines[:max_diff_lines])
    if diff_is_truncated:
        shown_diff += "\n... diff truncated ..."

    # 判定血缘状态：哈希不符→mismatch；字节一致→exact；其余→recovered_revision。
    if not expected_ok:
        state = "mismatch"
    elif same_bytes:
        state = "exact"
    else:
        state = "recovered_revision"

    timestamp = generated_at or _now()
    return {
        "schema": SOURCE_LINEAGE_SCHEMA,
        "generated_at": timestamp,
        "state": state,
        "repository": str(repo),
        "commit": resolved,
        "commit_subject": commit_info[2] if len(commit_info) > 2 else None,
        "commit_authored_at": commit_info[1] if len(commit_info) > 1 else None,
        "path": path,
        "expected_sha256": expected_sha256,
        "recovered": {
            "sha256": recovered_sha256,
            "bytes": len(blob),
        },
        "current": {
            "path": str(current),
            "exists": current_exists,
            "sha256": current_sha256,
            "bytes": len(current_bytes) if current_exists else None,
        },
        "same_bytes": same_bytes,
        "checks": {
            "expected_hash_matches_recovered": expected_ok,
            "current_matches_recovered": same_bytes,
            "current_exists": current_exists,
        },
        "diff": {
            "added_lines": added,
            "removed_lines": removed,
            "sha256": hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
            "truncated_for_receipt": diff_is_truncated,
            "unified": shown_diff,
        },
        "lineage_valid": expected_ok and current_exists,
        "publication_identity_ready": False,
        "notes": [
            "The exact manifest-named source is recovered from the recorded commit.",
            "A differing current file is retained as a lineage revision, not silently relabeled.",
            "Publication identity, author, license and upload authorization remain separate gates.",
        ],
    }


def _now() -> str:
    """返回当前 UTC 时间的 ISO 字符串（以 Z 结尾）。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: str | Path) -> dict[str, Any]:
    """读取 JSON 文件，并要求顶层必须是对象。"""
    value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ResearchFactoryError(f"expected a JSON object: {path}")
    return value


def _write_json(path: str | Path, value: Any) -> None:
    """把对象以 UTF-8、缩进 2 的格式写入 JSON 文件（自动创建父目录）。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _normalized(value: str) -> str:
    """把标题等文本规范化：反斜杠转空格、去符号、转小写、压缩空白。"""
    value = value.replace("\\", " ")
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def _normalized_path(value: str) -> str:
    """把路径规范化：反斜杠转正斜杠、转小写、去掉末尾斜杠。"""
    return value.replace("\\", "/").lower().rstrip("/")


def _parse_timestamp(value: str | None) -> datetime | None:
    """解析 ISO 时间字符串为带 UTC 时区的 datetime；解析失败返回 None。"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # 无时区信息时按 UTC 处理，再统一转换到 UTC。
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _family_project(portfolio: dict[str, Any], family_id: str) -> dict[str, Any]:
    """按家族号找到其规范项目的完整记录；找不到则抛错。"""
    project_id = None
    for family in portfolio.get("families", []):
        if family.get("family_id") == family_id:
            project_id = family.get("canonical_project_id")
            break
    if not project_id:
        raise ResearchFactoryError(f"paper family not found: {family_id}")

    project = None
    for item in portfolio.get("projects", []):
        if item.get("project_id") == project_id:
            project = item
            break
    if project is None:
        raise ResearchFactoryError(f"canonical project not found for family: {family_id}")
    return project


def _match_patterns(
    project: dict[str, Any],
    *,
    title_contains_any: Sequence[str] = (),
    source_contains_any: Sequence[str] = (),
) -> bool:
    """判断项目是否命中给定的一组标题/来源子串模式（任一命中即可）。"""
    title = _normalized(str(project.get("title", "")))
    source = _normalized_path(str(project.get("primary_source", "")))

    # 若有标题模式，则必须至少命中一个。
    if title_contains_any:
        title_hit = False
        for pattern in title_contains_any:
            if not pattern:
                continue
            if _normalized(pattern) in title:
                title_hit = True
                break
        if not title_hit:
            return False

    # 若没有来源模式，直接算通过；否则必须至少命中一个。
    if not source_contains_any:
        return True
    for pattern in source_contains_any:
        if not pattern:
            continue
        if _normalized_path(pattern) in source:
            return True
    return False


def _matched_pilots(
    project: dict[str, Any], pilots: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """返回所有命中该项目的试点，按 order（再按 id）排序。"""
    matches: list[dict[str, Any]] = []
    for pilot in pilots:
        if not isinstance(pilot, dict) or not pilot.get("id"):
            continue
        if _match_patterns(
            project,
            title_contains_any=pilot.get("title_contains_any", []),
            source_contains_any=pilot.get("source_contains_any", []),
        ):
            matches.append(pilot)
    matches.sort(key=lambda item: (int(item.get("order", 999)), str(item["id"])))
    return matches


def _has_file(files: dict[str, Any], key: str) -> bool:
    """files 字典里某个键是否为非空列表。"""
    value = files.get(key, [])
    return isinstance(value, list) and bool(value)


def _merged_file_signals(
    project_files: dict[str, Any],
    overlay_files: dict[str, Any] | None,
) -> dict[str, Any]:
    """把项目自带的文件信号与外置覆盖层的文件信号合并（按列表取并集）。"""
    if not overlay_files:
        return project_files
    merged = dict(project_files)
    for key, values in overlay_files.items():
        if not isinstance(values, list):
            continue
        merged[key] = sorted(set(merged.get(key, [])) | set(values))
    return merged


def _priority_band(score: int, pilot: dict[str, Any] | None) -> str:
    """把生产分映射到优先级档：命中的试点直接使用其 phase，否则按阈值分档。"""
    if pilot is not None:
        return str(pilot.get("phase") or "P0")
    if score >= 110:
        return "P1"
    if score >= 60:
        return "P2"
    return "P3"


def _suggested_disposition(
    project: dict[str, Any],
    *,
    pilot: dict[str, Any] | None,
    variant_count: int,
    generated: datetime,
) -> tuple[str, str]:
    """给出建议处置：repair / merge / archive，并附理由（仅建议，需人工确认）。"""
    if pilot is not None:
        return "repair", "Pinned as a production pilot; evidence and package gates still apply."

    files = project.get("files", {})

    if variant_count:
        return (
            "merge",
            (
                "One normalized-title family contains multiple source versions; reconcile "
                "the canonical source before drafting."
            ),
        )

    modified = _parse_timestamp(project.get("modified_at"))
    stale = modified is not None and modified < generated - timedelta(days=180)
    sparse = not any(
        _has_file(files, key)
        for key in ("claim_ledgers", "bibliographies", "pdfs", "evidence_directories")
    )

    if project.get("project_type") == "legacy" and stale and sparse:
        return (
            "archive",
            (
                "Legacy source is stale and has no local claim, bibliography, PDF, or "
                "evidence directory signal; archive only after human content review."
            ),
        )

    return (
        "repair",
        (
            "The canonical source has enough structure to repair, but its evidence and "
            "package gates remain unverified."
        ),
    )


def _finding(action_id: str, priority: str, reason: str, done_when: str) -> dict[str, str]:
    """构造一条「下一步动作」记录；owner 由 priority 推出（external→user，其余→agent）。"""
    owner = "agent"
    if priority == "external":
        owner = "user"
    return {
        "action_id": action_id,
        "priority": priority,
        "owner": owner,
        "reason": reason,
        "done_when": done_when,
    }


def _collect_package_files(source_dir: Path) -> tuple[list[Path], list[str]]:
    """递归收集打包源目录下的所有文件；符号链接视为阻断项。"""
    files: list[Path] = []
    blockers: list[str] = []
    for current, directories, filenames in os.walk(source_dir, followlinks=False):
        current_path = Path(current)
        # 就地排序并剔除版本库/Mac 元数据目录，保证遍历顺序稳定。
        directories[:] = sorted(
            name for name in directories if name not in {".git", ".hg", ".svn", "__MACOSX"}
        )
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                blockers.append(f"symlink is not package-safe: {path.relative_to(source_dir)}")
                continue
            files.append(path)
    return files, blockers


def _resolve_reference(
    source_dir: Path,
    raw: str,
    kind: str,
    *,
    graphics_paths: Sequence[Path] = (),
) -> bool:
    """判断一条 LaTeX 引用（input/include/includegraphics/bibliography）能否被解析到文件。"""
    value = raw.strip().strip('"')
    # 含反斜杠或 # 的多为宏/参数形式，无法静态解析，直接放行。
    if "\\" in value or "#" in value:
        return True

    if kind == "bibliography":
        names = [item.strip() for item in value.split(",") if item.strip()]
        return all((source_dir / f"{name}.bib").is_file() for name in names)

    if kind == "addbibresource":
        return (source_dir / value).is_file()

    # 其余引用在源目录（图片还可在 graphicspath 目录）下查找。
    search_roots = [source_dir]
    if kind == "includegraphics":
        search_roots.extend(graphics_paths)

    for search_root in search_roots:
        candidate = search_root / value
        if candidate.is_file():
            return True
        # 已带后缀就不再尝试补后缀。
        if candidate.suffix:
            continue
        for suffix in (".tex", ".pdf", ".png", ".jpg", ".jpeg", ".eps"):
            if candidate.with_suffix(suffix).is_file():
                return True
    return False


def _strip_tex_comments(text: str) -> str:
    """去掉 LaTeX 注释，同时保留被转义的百分号（\\%）。"""
    return re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)


def _split_json_path(path: str) -> list[str]:
    """把 "a.b[0].c" 这类路径拆成段列表，支持引号包裹的点/方括号。"""
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    for character in path:
        if character == '"':
            quoted = not quoted
            continue
        if character == "[" and not quoted:
            if current:
                parts.append("".join(current))
                current = []
            continue
        if character == "]" and not quoted:
            if current:
                parts.append("".join(current))
                current = []
            continue
        if character == "." and not quoted:
            if current:
                parts.append("".join(current))
                current = []
            continue
        current.append(character)
    if current:
        parts.append("".join(current))
    return parts


def _resolve_json_path(value: Any, path: str) -> Any:
    """按路径在 JSON 结构里取值；如果整条路径以顶层键直接命中则优先返回。"""
    if isinstance(value, dict) and path in value:
        return value[path]

    current = value
    for segment in _split_json_path(path):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (IndexError, TypeError, ValueError):
                return None
        else:
            return None
    return current


def _number_tolerance(value: Any) -> float:
    """给出某个数值的比对容差：整数 0.5；小数按有效位取半单位；其余 0。"""
    if isinstance(value, int) and not isinstance(value, bool):
        return 0.5
    if isinstance(value, float) and math.isfinite(value):
        rendered = format(value, ".15g")
        if "." in rendered and "e" not in rendered.lower():
            decimals = len(rendered.split(".", 1)[1])
            return max(2e-5, 0.5 * 10 ** (-decimals))
        return 2e-5
    return 0.0


def _numeric_match(claimed: Any, actual: Any) -> bool:
    """判断声称值与实际值是否在容差内相等；布尔和数值分开处理。"""
    if isinstance(claimed, bool) or isinstance(actual, bool):
        return claimed == actual
    if isinstance(claimed, (int, float)) and isinstance(actual, (int, float)):
        if not math.isfinite(float(claimed)) or not math.isfinite(float(actual)):
            return False
        return abs(float(actual) - float(claimed)) <= _number_tolerance(claimed) + 1e-12
    return claimed == actual
