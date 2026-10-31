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

TRIAGE_SCHEMA = "q-one-research-triage-v1"
SCAFFOLD_SCHEMA = "q-one-research-scaffold-v1"
PLAN_SCHEMA = "q-one-research-plan-v1"
PACKAGE_SCHEMA = "q-one-arxiv-package-audit-v1"
NATIVE_LEDGER_SCHEMA = "q-one-native-ledger-audit-v1"
SOURCE_LINEAGE_SCHEMA = "q-one-source-lineage-v1"
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
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|FIXME|TBD|XXX)\b|\[(?:CITE|REF|TODO)\]")
REFERENCE_RE = re.compile(
    r"\\(?P<kind>input|include|includegraphics|bibliography|addbibresource)"
    r"\s*(?:\[[^\]]*\])?\s*\{(?P<target>[^}]+)\}"
)
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{((?:\{[^}]+\})+)\}")
ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s{(\"'])(?:/home/|/Users/|/mnt/|[A-Za-z]:[\\/][A-Za-z0-9_])"
)
class ResearchFactoryError(ValueError):
    """Raised when a factory operation would be unsafe or ambiguous."""
def _git_output(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
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
    """Recover a manifest-named source blob from git and compare its descendant.

    This proves source lineage, not publication identity. It never writes to the
    source repository and never treats a textual similarity as a scientific
    result.
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

    try:
        resolved = _git_output(
            repo, "rev-parse", "--verify", f"{commit}^{{commit}}", text=True
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ResearchFactoryError(f"git commit cannot be resolved: {commit}") from exc

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
    current = Path(current_path).expanduser().resolve()
    current_exists = current.is_file()
    current_bytes = current.read_bytes() if current_exists else b""
    current_sha256 = hashlib.sha256(current_bytes).hexdigest() if current_exists else None
    same_bytes = current_exists and current_bytes == blob
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
    added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    diff_is_truncated = len(diff_lines) > max_diff_lines
    shown_diff = "\n".join(diff_lines[:max_diff_lines])
    if diff_is_truncated:
        shown_diff += "\n... diff truncated ..."

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
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ResearchFactoryError(f"expected a JSON object: {path}")
    return value
def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
def _normalized(value: str) -> str:
    value = value.replace("\\", " ")
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()
def _normalized_path(value: str) -> str:
    return value.replace("\\", "/").lower().rstrip("/")
def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
def _family_project(portfolio: dict[str, Any], family_id: str) -> dict[str, Any]:
    project_id = next(
        (
            family.get("canonical_project_id")
            for family in portfolio.get("families", [])
            if family.get("family_id") == family_id
        ),
        None,
    )
    if not project_id:
        raise ResearchFactoryError(f"paper family not found: {family_id}")
    project = next(
        (
            item
            for item in portfolio.get("projects", [])
            if item.get("project_id") == project_id
        ),
        None,
    )
    if project is None:
        raise ResearchFactoryError(f"canonical project not found for family: {family_id}")
    return project
def _match_patterns(
    project: dict[str, Any],
    *,
    title_contains_any: Sequence[str] = (),
    source_contains_any: Sequence[str] = (),
) -> bool:
    title = _normalized(str(project.get("title", "")))
    source = _normalized_path(str(project.get("primary_source", "")))
    if title_contains_any and not any(
        _normalized(pattern) in title for pattern in title_contains_any if pattern
    ):
        return False
    return not source_contains_any or any(
        _normalized_path(pattern) in source for pattern in source_contains_any if pattern
    )
def _matched_pilots(
    project: dict[str, Any], pilots: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
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
    value = files.get(key, [])
    return isinstance(value, list) and bool(value)
def _merged_file_signals(
    project_files: dict[str, Any],
    overlay_files: dict[str, Any] | None,
) -> dict[str, Any]:
    if not overlay_files:
        return project_files
    merged = dict(project_files)
    for key, values in overlay_files.items():
        if not isinstance(values, list):
            continue
        merged[key] = sorted(set(merged.get(key, [])) | set(values))
    return merged
def _priority_band(score: int, pilot: dict[str, Any] | None) -> str:
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
    return {
        "action_id": action_id,
        "priority": priority,
        "owner": "agent" if priority != "external" else "user",
        "reason": reason,
        "done_when": done_when,
    }
def _collect_package_files(source_dir: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    blockers: list[str] = []
    for current, directories, filenames in os.walk(source_dir, followlinks=False):
        current_path = Path(current)
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
    value = raw.strip().strip('"')
    if "\\" in value or "#" in value:
        return True
    if kind == "bibliography":
        names = [item.strip() for item in value.split(",") if item.strip()]
        return all((source_dir / f"{name}.bib").is_file() for name in names)
    if kind == "addbibresource":
        return (source_dir / value).is_file()
    search_roots = [source_dir]
    if kind == "includegraphics":
        search_roots.extend(graphics_paths)
    for search_root in search_roots:
        candidate = search_root / value
        if candidate.is_file():
            return True
        if candidate.suffix:
            continue
        for suffix in (".tex", ".pdf", ".png", ".jpg", ".jpeg", ".eps"):
            if candidate.with_suffix(suffix).is_file():
                return True
    return False
def _strip_tex_comments(text: str) -> str:
    """Remove LaTeX comments while preserving escaped percent signs."""
    return re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)
def _split_json_path(path: str) -> list[str]:
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
    if isinstance(claimed, bool) or isinstance(actual, bool):
        return claimed == actual
    if isinstance(claimed, (int, float)) and isinstance(actual, (int, float)):
        if not math.isfinite(float(claimed)) or not math.isfinite(float(actual)):
            return False
        return abs(float(actual) - float(claimed)) <= _number_tolerance(claimed) + 1e-12
    return claimed == actual
