"""Read-only inventory and quantification of local research projects."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

PORTFOLIO_SCHEMA = "q-one-paper-portfolio-v1"
PROJECT_SCHEMA = "q-one-research-project-v1"
QUANTIFICATION_SCHEMA = "q-one-research-quantification-v1"

MANUSCRIPT_NAMES = ("main.tex", "paper.tex", "manuscript.tex")
CONFIG_NAMES = ("project_config.json", "research-manifest.json")
PROJECT_NAMES = ("project.json",)
PLAN_NAMES = ("PAPER_PLAN.md",)
LEDGER_NAMES = ("CLAIM_LEDGER.md",)

DEFAULT_EXCLUDE_DIRS = {
    ".cache",
    ".codex",
    ".git",
    ".local",
    ".npm",
    ".nvm",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
}

DEFAULT_LOW_SIGNAL_FRAGMENTS = (
    "/.agent-memory/world-sota-3lines/repro/",
    "/.dsh/attachments/",
    "/.research/opencode_archive/",
    "/.workbuddy/skills/",
    "/Projects/agi-paper-pipeline/backups/",
    "/_scratch/",
    "/demo/papers/",
    "/fixtures/",
    "/templates/",
)

BACKUP_PARTS = {".backups", "backup", "backups"}
DEMO_PARTS = {"demo", "fixtures", "template", "templates"}
SUBMISSION_PARTS = {
    "arxiv_source",
    "preprint",
    "release",
    "releases",
    "source",
    "submission",
    "submissions",
}

VERSION_COPY_PARTS = {
    ".aris",
    "artifacts",
    "attempt-history",
    "deliveries",
    "ingest_drift",
    "packages",
    "reproducibility",
    "submission-ready",
}

TEXT_SUFFIXES = {".bib", ".json", ".md", ".tex"}
EVIDENCE_DIR_NAMES = {"artifact", "artifacts", "data", "evidence", "results", "runs"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_timestamp(path: Path) -> str:
    value = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _is_qone_research_project_file(path: Path) -> bool:
    if path.name not in PROJECT_NAMES:
        return False
    payload = _read_json(path)
    return bool(payload and payload.get("schema") == PROJECT_SCHEMA)


def _flatten_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_json_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_json_text(item) for item in value.values())
    return ""


def _balanced_braced_value(text: str, start: int) -> str | None:
    depth = 0
    buffer: list[str] = []
    escaped = False
    for character in text[start:]:
        if escaped:
            buffer.append(character)
            escaped = False
            continue
        if character == "\\":
            buffer.append(character)
            escaped = True
            continue
        if character == "{":
            depth += 1
            if depth == 1:
                continue
        elif character == "}":
            depth -= 1
            if depth == 0:
                return "".join(buffer).strip()
        if depth > 0:
            buffer.append(character)
    return None


def latex_title(text: str) -> str | None:
    match = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", text)
    if not match:
        return None
    title = _balanced_braced_value(text, match.end() - 1)
    if not title:
        return None
    title = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", title)
    title = title.replace("~", " ").replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", title).strip() or None


def markdown_title(text: str) -> str | None:
    front_matter = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if front_matter:
        match = re.search(
            r"^title\s*:\s*[\"']?(.*?)[\"']?\s*$",
            front_matter.group(1),
            re.MULTILINE,
        )
        if match and match.group(1).strip():
            return match.group(1).strip()
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _title_from_json(path: Path) -> tuple[str | None, str | None, str | None]:
    payload = _read_json(path)
    if not payload:
        return None, None, None
    project = payload.get("project")
    project_data = project if isinstance(project, dict) else payload
    title = project_data.get("title")
    target = project_data.get("target") or project_data.get("venue")
    status = project_data.get("status")
    if not isinstance(title, str):
        title = None
    if not isinstance(target, str):
        target = None
    if not isinstance(status, str):
        status = None
    return title, target, status


def _title_from_text(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return None
    if path.suffix.lower() == ".tex":
        return latex_title(text)
    return markdown_title(text)


def _project_root_for_marker(path: Path, writeup_globs: tuple[str, ...]) -> Path:
    if _matches_writeup(path, writeup_globs):
        return path.with_suffix("")
    parent = path.parent
    if parent.name.lower() in {
        "arxiv_source",
        "manuscript",
        "paper",
        "preprint",
        "source",
    }:
        return parent.parent
    return parent


def _matches_writeup(path: Path, patterns: Iterable[str]) -> bool:
    return any(fnmatch(path.name, pattern) for pattern in patterns)


def _classify_project(root: Path, primary: Path, is_paper_source: bool) -> str:
    lowered = {part.lower() for part in root.parts}
    if not is_paper_source:
        if primary.name in (*CONFIG_NAMES, *PROJECT_NAMES):
            return "supporting-config"
        if primary.name in PLAN_NAMES:
            return "plan"
        if primary.name in LEDGER_NAMES:
            return "claim-ledger"
    if lowered & BACKUP_PARTS or any(".bak-" in part for part in lowered):
        return "backup"
    if lowered & DEMO_PARTS:
        return "demo"
    if lowered & VERSION_COPY_PARTS:
        return "version-copy"
    if lowered & SUBMISSION_PARTS:
        return "submission-copy"
    if ".research" in lowered:
        return "legacy"
    return "paper"


def _candidate_score(record: dict[str, Any]) -> tuple[int, int, float]:
    type_weight = {
        "paper": 100,
        "submission-copy": 70,
        "version-copy": 60,
        "legacy": 50,
        "supporting-config": 20,
        "plan": 20,
        "claim-ledger": 20,
        "demo": 20,
        "backup": 10,
    }.get(record["project_type"], 0)
    files = record["files"]
    score = type_weight
    score += 30 if files["claim_ledgers"] else 0
    score += 20 if files["bibliographies"] else 0
    score += 20 if files["pdfs"] else 0
    score += 10 if files["configs"] else 0
    score -= max(0, record["path_depth"] - 4) * 5
    return score, -record["path_depth"], record["modified_epoch"]


def _project_id(root: Path) -> str:
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "paper"
    return f"qp-{slug}-{digest}"


def _git_metadata(path: Path, cache: dict[Path, dict[str, Any]]) -> dict[str, Any] | None:
    current = path
    while current.parent != current:
        if (current / ".git").exists():
            if current in cache:
                return cache[current]
            result = subprocess.run(
                ["git", "-C", str(current), "rev-parse", "--short", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                branch = subprocess.run(
                    ["git", "-C", str(current), "branch", "--show-current"],
                    check=False,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                dirty = subprocess.run(
                    ["git", "-C", str(current), "status", "--porcelain"],
                    check=False,
                    capture_output=True,
                    text=True,
                ).stdout
                metadata = {
                    "root": str(current),
                    "head": result.stdout.strip(),
                    "branch": branch or None,
                    "dirty": bool(dirty.strip()),
                }
            else:
                metadata = None
            cache[current] = metadata
            return metadata
        current = current.parent
    return None


def _project_metadata(root: Path) -> tuple[str | None, str | None, str | None]:
    title: str | None = None
    target: str | None = None
    status: str | None = None
    for name in (*PROJECT_NAMES, *CONFIG_NAMES):
        config = root / name
        if not config.is_file():
            continue
        if name in PROJECT_NAMES and not _is_qone_research_project_file(config):
            continue
        config_title, config_target, config_status = _title_from_json(config)
        title = title or config_title
        target = target or config_target
        status = status or config_status
    return title, target, status


def _collect_project_files(root: Path) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {
        "pdfs": [],
        "bibliographies": [],
        "claim_ledgers": [],
        "configs": [],
        "plans": [],
        "evidence_directories": [],
    }
    for current, directories, filenames in os.walk(root):
        current_path = Path(current)
        try:
            relative = current_path.relative_to(root)
        except ValueError:
            continue
        if len(relative.parts) > 3:
            directories[:] = []
            continue
        directories[:] = [
            name
            for name in directories
            if name not in DEFAULT_EXCLUDE_DIRS
            and name not in {"node_modules", "__pycache__"}
        ]
        for directory in directories:
            if directory.lower() in EVIDENCE_DIR_NAMES:
                files["evidence_directories"].append(str(current_path / directory))
        for filename in filenames:
            path = current_path / filename
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                files["pdfs"].append(str(path))
            elif suffix == ".bib":
                files["bibliographies"].append(str(path))
            elif filename in LEDGER_NAMES:
                files["claim_ledgers"].append(str(path))
            elif filename in CONFIG_NAMES or _is_qone_research_project_file(path):
                files["configs"].append(str(path))
            elif filename in PLAN_NAMES:
                files["plans"].append(str(path))
    for key, values in files.items():
        files[key] = sorted(set(values))
    return files


def _scan_markers(
    roots: Iterable[Path],
    *,
    exclude_dirs: set[str],
    exclude_path_fragments: tuple[str, ...],
    max_depth: int,
    writeup_globs: tuple[str, ...],
) -> dict[Path, list[Path]]:
    candidates: dict[Path, list[Path]] = defaultdict(list)
    for scan_root in roots:
        scan_root = scan_root.expanduser().resolve()
        if not scan_root.exists():
            continue
        root_depth = len(scan_root.parts)
        for current, directories, filenames in os.walk(scan_root):
            current_path = Path(current)
            depth = len(current_path.parts) - root_depth
            if depth >= max_depth:
                directories[:] = []
            directories[:] = [
                name
                for name in directories
                if name not in exclude_dirs
                and name not in DEFAULT_EXCLUDE_DIRS
            ]
            current_marker = current_path.as_posix()
            if any(fragment in current_marker for fragment in exclude_path_fragments):
                directories[:] = []
                continue
            for filename in filenames:
                path = current_path / filename
                is_marker = (
                    filename in MANUSCRIPT_NAMES
                    or filename in CONFIG_NAMES
                    or _is_qone_research_project_file(path)
                    or filename in PLAN_NAMES
                    or filename in LEDGER_NAMES
                    or _matches_writeup(path, writeup_globs)
                )
                if is_marker:
                    candidates[_project_root_for_marker(path, writeup_globs)].append(path)
    return candidates


def _choose_primary(root: Path, markers: list[Path], writeup_globs: tuple[str, ...]) -> Path:
    priority: list[tuple[int, int, str]] = []
    for path in markers:
        name = path.name
        if name in MANUSCRIPT_NAMES:
            rank = MANUSCRIPT_NAMES.index(name)
        elif _matches_writeup(path, writeup_globs):
            rank = 10
        elif name in CONFIG_NAMES or _is_qone_research_project_file(path):
            rank = 20
        elif name in PLAN_NAMES:
            rank = 30
        elif name in LEDGER_NAMES:
            rank = 40
        else:
            rank = 50
        priority.append((rank, len(str(path)), str(path)))
    return Path(min(priority)[2])


def _build_record(
    root: Path,
    markers: list[Path],
    *,
    writeup_globs: tuple[str, ...],
    git_cache: dict[Path, dict[str, Any]],
) -> dict[str, Any]:
    primary = _choose_primary(root, markers, writeup_globs)
    metadata_title, metadata_target, metadata_status = _project_metadata(root)
    title = metadata_title
    if not title and (
        primary.name in MANUSCRIPT_NAMES or _matches_writeup(primary, writeup_globs)
    ):
        title = _title_from_text(primary)

    files = _collect_project_files(root)
    primary_hash = sha256_file(primary)
    is_paper_source = (
        primary.name in MANUSCRIPT_NAMES or _matches_writeup(primary, writeup_globs)
    )
    project_type = _classify_project(root, primary, is_paper_source)
    record = {
        "project_id": _project_id(root),
        "title": title or root.name.replace("_", " ").replace("-", " "),
        "root": str(root),
        "primary_source": str(primary),
        "primary_sha256": primary_hash,
        "project_type": project_type,
        "target": metadata_target,
        "status": metadata_status or "unknown",
        "disposition": "unreviewed",
        "priority": None,
        "files": files,
        "git": _git_metadata(root, git_cache),
        "modified_at": _utc_timestamp(primary),
        "modified_epoch": primary.stat().st_mtime,
        "path_depth": len(root.parts),
        "markers": sorted(str(path) for path in markers),
    }
    return record


def _normalized_title(title: str) -> str:
    title = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", title)
    title = title.replace("{", "").replace("}", "").replace("\\", " ")
    title = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", title).lower()
    return re.sub(r"\s+", " ", title).strip()


def _family_id(title_key: str) -> str:
    digest = hashlib.sha256(title_key.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", title_key).strip("-")[:40] or "paper"
    return f"qf-{slug}-{digest}"


def build_portfolio(
    roots: Iterable[str | Path],
    *,
    generated_at: str | None = None,
    exclude_dirs: Iterable[str] = (),
    exclude_path_fragments: Iterable[str] = (),
    writeup_globs: Iterable[str] = (),
    max_depth: int = 8,
) -> dict[str, Any]:
    roots = [Path(root) for root in roots]
    exclude_dir_set = set(exclude_dirs)
    fragment_tuple = tuple(exclude_path_fragments)
    glob_tuple = tuple(writeup_globs)
    marker_map = _scan_markers(
        roots,
        exclude_dirs=exclude_dir_set,
        exclude_path_fragments=fragment_tuple,
        max_depth=max_depth,
        writeup_globs=glob_tuple,
    )

    git_cache: dict[Path, dict[str, Any]] = {}
    records = [
        _build_record(root, markers, writeup_globs=glob_tuple, git_cache=git_cache)
        for root, markers in marker_map.items()
    ]
    records.sort(key=lambda record: record["root"])

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["primary_sha256"]].append(record)

    duplicate_groups: list[dict[str, Any]] = []
    canonical_by_hash: dict[str, str] = {}
    for digest, group in groups.items():
        canonical = max(group, key=_candidate_score)
        canonical_by_hash[digest] = canonical["project_id"]
        if len(group) > 1:
            duplicate_groups.append(
                {
                    "primary_sha256": digest,
                    "canonical_project_id": canonical["project_id"],
                    "members": [
                        {
                            "project_id": member["project_id"],
                            "root": member["root"],
                            "project_type": member["project_type"],
                        }
                        for member in sorted(group, key=lambda item: item["root"])
                    ],
                }
            )

    canonical_records: list[dict[str, Any]] = []
    for record in records:
        canonical_id = canonical_by_hash[record["primary_sha256"]]
        record["canonical_project_id"] = canonical_id
        record["exact_duplicate"] = canonical_id != record["project_id"]
        if not record["exact_duplicate"]:
            canonical_records.append(record)

    canonical_records.sort(key=lambda record: (-_candidate_score(record)[0], record["root"]))
    duplicate_groups.sort(key=lambda group: group["canonical_project_id"])

    eligible_types = {"paper", "submission-copy", "version-copy", "legacy"}
    family_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    supporting_records: list[dict[str, Any]] = []
    supporting_by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in canonical_records:
        if record["project_type"] not in eligible_types:
            record["family_id"] = None
            record["family_representative"] = False
            record["title_key"] = _normalized_title(record["title"])
            supporting_records.append(record)
            if record["title_key"]:
                supporting_by_title[record["title_key"]].append(record)
            continue
        title_key = _normalized_title(record["title"])
        if len(title_key) < 4:
            title_key = f"{_normalized_title(record['root'])} {title_key}".strip()
        record["title_key"] = title_key
        record["family_id"] = _family_id(title_key)
        family_groups[title_key].append(record)

    family_records: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    metadata_overlays = 0
    for title_key, group in family_groups.items():
        representative = max(group, key=_candidate_score)
        representative["family_representative"] = True
        overlay_candidates = supporting_by_title.get(title_key, [])
        overlay = max(overlay_candidates, key=_candidate_score) if overlay_candidates else None
        if overlay is not None:
            metadata_overlays += 1
            representative["metadata_project_id"] = overlay["project_id"]
            representative["metadata_root"] = overlay["root"]
            if overlay["status"] != "unknown":
                representative["status"] = overlay["status"]
            if overlay["target"]:
                representative["target"] = overlay["target"]
        family_records.append(representative)
        families.append(
            {
                "family_id": representative["family_id"],
                "title": representative["title"],
                "title_key": title_key,
                "canonical_project_id": representative["project_id"],
                "metadata_project_id": (
                    representative.get("metadata_project_id")
                    if overlay is not None
                    else None
                ),
                "members": [
                    {
                        "project_id": member["project_id"],
                        "root": member["root"],
                        "project_type": member["project_type"],
                        "primary_sha256": member["primary_sha256"],
                    }
                    for member in sorted(group, key=lambda item: item["root"])
                ],
            }
        )
        for member in group:
            member["family_representative"] = member is representative

    family_records.sort(key=lambda record: (-_candidate_score(record)[0], record["root"]))
    families.sort(key=lambda family: family["family_id"])
    type_counts: dict[str, int] = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)
    disposition_counts: dict[str, int] = defaultdict(int)
    for record in family_records:
        type_counts[record["project_type"]] += 1
        status_counts[record["status"]] += 1
        disposition_counts[record["disposition"]] += 1

    family_member_count = sum(len(family["members"]) for family in families)
    return {
        "schema": PORTFOLIO_SCHEMA,
        "generated_at": generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": {
            "roots": [str(root.expanduser().resolve()) for root in roots],
            "exclude_dirs": sorted(exclude_dir_set),
            "exclude_path_fragments": list(fragment_tuple),
            "writeup_globs": list(glob_tuple),
            "max_depth": max_depth,
        },
        "summary": {
            "raw_project_roots": len(records),
            "canonical_projects": len(family_records),
            "exact_duplicate_groups": len(duplicate_groups),
            "duplicate_project_roots": len(records) - len(canonical_records),
            "version_variants": family_member_count - len(family_records),
            "supporting_objects": len(supporting_records),
            "metadata_overlays": metadata_overlays,
            "project_types": dict(sorted(type_counts.items())),
            "statuses": dict(sorted(status_counts.items())),
            "dispositions": dict(sorted(disposition_counts.items())),
            "global_readiness_score": None,
            "note": "Readiness is deliberately not collapsed into a global score.",
        },
        "projects": family_records,
        "families": families,
        "duplicates": duplicate_groups,
        "candidates": records,
    }


def render_markdown(portfolio: dict[str, Any]) -> str:
    summary = portfolio["summary"]
    lines = [
        "# Q-One paper portfolio",
        "",
        f"Generated: `{portfolio['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Project roots discovered: {summary['raw_project_roots']}",
        f"- Paper families after exact and title-version grouping: {summary['canonical_projects']}",
        f"- Exact duplicate groups: {summary['exact_duplicate_groups']}",
        f"- Duplicate roots merged: {summary['duplicate_project_roots']}",
        f"- Version variants merged by normalized title: {summary['version_variants']}",
        f"- Supporting objects excluded from paper families: {summary['supporting_objects']}",
        "- Global readiness score: unknown by design",
        "",
        "## Canonical projects",
        "",
        "| Type | Title | Status | Disposition | Primary source | Variants merged |",
        "|---|---|---|---|---|---:|",
    ]
    variant_counts = {
        family["canonical_project_id"]: len(family["members"]) - 1
        for family in portfolio["families"]
    }
    for project in portfolio["projects"]:
        title = project["title"].replace("|", "\\|")
        source = project["primary_source"].replace("|", "\\|")
        lines.append(
            f"| {project['project_type']} | {title} | {project['status']} | "
            f"{project['disposition']} | "
            f"`{source}` | {variant_counts.get(project['project_id'], 0)} |"
        )
    lines.extend(
        [
            "",
            (
                "The JSON companion contains every candidate root, exact hashes, "
                "metadata files, git revision, evidence directories, and duplicate "
                "membership."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_triage_csv(portfolio: dict[str, Any]) -> str:
    variant_counts = {
        family["family_id"]: len(family["members"]) - 1 for family in portfolio["families"]
    }
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "family_id",
            "title",
            "status",
            "disposition",
            "priority",
            "project_type",
            "target",
            "primary_source",
            "modified_at",
            "variants_merged",
        ]
    )
    for project in sorted(
        portfolio["projects"], key=lambda item: item["modified_at"], reverse=True
    ):
        writer.writerow(
            [
                project["family_id"],
                project["title"],
                project["status"],
                project["disposition"],
                project.get("priority") or "",
                project["project_type"],
                project.get("target") or "",
                project["primary_source"],
                project["modified_at"],
                variant_counts.get(project["project_id"], 0),
            ]
        )
    return output.getvalue()


def write_portfolio(
    portfolio: dict[str, Any],
    output: Path,
    markdown_output: Path | None = None,
    triage_output: Path | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_markdown(portfolio), encoding="utf-8")
    if triage_output is not None:
        triage_output.parent.mkdir(parents=True, exist_ok=True)
        triage_output.write_text(render_triage_csv(portfolio), encoding="utf-8")


def quantify_research_project(root: str | Path) -> dict[str, Any]:
    """Compute the documented research quantities for a single project.

    Implements the seven computable quantities from
    RESEARCH_QUANTIFICATION.zh-CN.md.  Every quantity is reported as a value
    plus the explicit denominator it was computed over; when the denominator
    is unknown or the field is absent, the value is ``"unknown"`` rather than 0.

    The function is read-only: it loads ``project.json`` and validates the
    claims ledger cross-reference without writing anything.
    """
    root = Path(root).expanduser().resolve()
    project_path = root / "project.json"
    if not project_path.is_file():
        return {
            "schema": QUANTIFICATION_SCHEMA,
            "root": str(root),
            "valid": False,
            "quantities": {
                "claim_evidence_coverage": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "claim_recomputation_coverage": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "experiment_reproduction_coverage": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "citation_verification_coverage": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "unresolved_critical": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "unresolved_major": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
                "package_completeness": {"value": "unknown", "numerator": "unknown", "denominator": "unknown"},
            },
            "errors": ["project.json is missing"],
        }
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {
            "schema": QUANTIFICATION_SCHEMA,
            "root": str(root),
            "valid": False,
            "quantities": {},
            "errors": [f"project.json is not valid JSON: {exc}"],
        }
    if not isinstance(project, dict):
        return {
            "schema": QUANTIFICATION_SCHEMA,
            "root": str(root),
            "valid": False,
            "quantities": {},
            "errors": ["project.json must be an object"],
        }

    errors: list[str] = []
    quantities: dict[str, Any] = {}

    # claim_evidence_coverage: claims with at least one valid evidence_ref
    claims = project.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims must be an array")
        claims = []
    total_claims = len(claims)
    claims_with_evidence = sum(
        1
        for claim in claims
        if isinstance(claim, dict) and claim.get("evidence_refs")
    )
    quantities["claim_evidence_coverage"] = _ratio(
        claims_with_evidence, total_claims
    )

    # claim_recomputation_coverage: claims with a runnable recomputation method
    # The project schema carries no explicit recomputation field; a claim with
    # an evidence_ref pointing at a JSON file is treated as recomputable.
    recomputable_claims = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        refs = claim.get("evidence_refs", [])
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if isinstance(ref, str) and ref.lower().endswith((".json", ".csv", ".tsv")):
                recomputable_claims += 1
                break
    quantities["claim_recomputation_coverage"] = _ratio(
        recomputable_claims, total_claims
    )

    # experiment_reproduction_coverage: reproducible experiments / required
    experiments = project.get("experiments", [])
    if not isinstance(experiments, list):
        errors.append("experiments must be an array")
        experiments = []
    required_experiments = 0
    reproducible_experiments = 0
    for experiment in experiments:
        if not isinstance(experiment, dict):
            continue
        if experiment.get("state") not in {"required", "planned", "running", "completed"}:
            continue
        required_experiments += 1
        receipt = experiment.get("receipt")
        environment = experiment.get("environment_sha256")
        if receipt and isinstance(receipt, str):
            receipt_path = root / receipt
            if receipt_path.is_file() and environment:
                reproducible_experiments += 1
    quantities["experiment_reproduction_coverage"] = _ratio(
        reproducible_experiments, required_experiments
    )

    # citation_verification_coverage: verified citations / total citations
    # The project schema has no citations field; the ledger is the only
    # structured citation carrier available.
    ledger_path = root / "CLAIM_LEDGER.md"
    if ledger_path.is_file():
        ledger_text = ledger_path.read_text(encoding="utf-8")
        ledger_rows = [
            line for line in ledger_text.splitlines()
            if line.strip().startswith("|") and re.search(r"\bC\d+\b", line)
        ]
        total_citations = len(ledger_rows)
        verified_citations = sum(
            1
            for line in ledger_rows
            if re.search(r"\b(verified|pass|ok|yes)\b", line, re.IGNORECASE)
        )
        quantities["citation_verification_coverage"] = _ratio(
            verified_citations, total_citations
        )
    else:
        quantities["citation_verification_coverage"] = _ratio(0, 0)

    # unresolved_critical / unresolved_major: open reviews with critical/major
    reviews = project.get("reviews", [])
    if not isinstance(reviews, list):
        errors.append("reviews must be an array")
        reviews = []
    unresolved_critical = 0
    unresolved_major = 0
    for review in reviews:
        if not isinstance(review, dict):
            continue
        if review.get("state") != "open":
            continue
        unresolved_critical += int(review.get("critical", 0) or 0)
        unresolved_major += int(review.get("major", 0) or 0)
    quantities["unresolved_critical"] = {
        "value": unresolved_critical,
        "numerator": unresolved_critical,
        "denominator": "counts",
    }
    quantities["unresolved_major"] = {
        "value": unresolved_major,
        "numerator": unresolved_major,
        "denominator": "counts",
    }

    # package_completeness: passed package files / applicable package files
    package = project.get("package", {})
    if not isinstance(package, dict):
        errors.append("package must be an object")
        package = {}
    package_files = package.get("files", [])
    if not isinstance(package_files, list):
        errors.append("package files must be an array")
        package_files = []
    applicable_files = 0
    passed_files = 0
    for entry in package_files:
        if not isinstance(entry, dict):
            continue
        applicable_files += 1
        path = entry.get("path")
        if isinstance(path, str) and (root / path).is_file():
            passed_files += 1
    quantities["package_completeness"] = _ratio(
        passed_files, applicable_files
    )

    return {
        "schema": QUANTIFICATION_SCHEMA,
        "root": str(root),
        "valid": not errors,
        "quantities": quantities,
        "errors": errors,
    }


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator <= 0:
        return {
            "value": "unknown",
            "numerator": numerator if numerator > 0 else "unknown",
            "denominator": "unknown",
        }
    return {
        "value": numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
    }


def validate_research_project(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    project_path = root / "project.json"
    if not project_path.is_file():
        return {
            "schema": "q-one-research-validation-v1",
            "root": str(root),
            "valid": False,
            "ready": False,
            "errors": ["project.json is missing"],
            "warnings": [],
            "global_readiness_score": None,
        }
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {
            "schema": "q-one-research-validation-v1",
            "root": str(root),
            "valid": False,
            "ready": False,
            "errors": [f"project.json is not valid JSON: {exc}"],
            "warnings": [],
            "global_readiness_score": None,
        }

    if project.get("schema") != PROJECT_SCHEMA:
        errors.append(f"project schema must be {PROJECT_SCHEMA}")
    for key in (
        "paper_id",
        "title",
        "status",
        "target",
        "manuscript",
        "evidence",
        "claims",
        "experiments",
        "reviews",
        "package",
    ):
        if key not in project:
            errors.append(f"project field is missing: {key}")

    manuscript = project.get("manuscript")
    if isinstance(manuscript, dict):
        manuscript_path = root / str(manuscript.get("path", ""))
        if not manuscript_path.is_file():
            errors.append(f"manuscript is missing: {manuscript.get('path')}")
        elif sha256_file(manuscript_path) != manuscript.get("sha256"):
            errors.append("manuscript SHA-256 does not match project.json")
        matches_published = manuscript.get("matches_published_source")
        if (
            matches_published is not None
            and manuscript.get("published_source_sha256") is not None
            and isinstance(matches_published, bool)
        ):
            expected = (
                manuscript.get("sha256") == manuscript.get("published_source_sha256")
            )
            if matches_published != expected:
                errors.append(
                    "matches_published_source disagrees with the recorded source hashes"
                )
    else:
        errors.append("manuscript must be an object")

    evidence_states = {"verified", "candidate", "inconclusive", "blocked", "unknown"}
    evidence = project.get("evidence", [])
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
        evidence = []
    for entry in evidence:
        if not isinstance(entry, dict):
            errors.append("evidence entries must be objects")
            continue
        relative = entry.get("path")
        if not isinstance(relative, str):
            errors.append("evidence path must be a string")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"evidence file is missing: {relative}")
            continue
        if sha256_file(path) != entry.get("sha256"):
            errors.append(f"evidence SHA-256 mismatch: {relative}")
        if entry.get("state") not in evidence_states:
            errors.append(f"invalid evidence state: {relative}")

    ledger_path = root / "CLAIM_LEDGER.md"
    if not ledger_path.is_file():
        errors.append("CLAIM_LEDGER.md is missing")
        ledger_claim_ids: set[str] = set()
    else:
        ledger_claim_ids = set(
            re.findall(r"^\|\s*(C\d+)\s*\|", ledger_path.read_text(encoding="utf-8"), re.MULTILINE)
        )
    manifest_claim_ids: set[str] = set()
    blocked_claims: list[str] = []
    for claim in project.get("claims", []):
        if not isinstance(claim, dict):
            errors.append("claim entries must be objects")
            continue
        claim_id = claim.get("claim_id")
        if isinstance(claim_id, str):
            manifest_claim_ids.add(claim_id)
            if claim.get("state") == "blocked":
                blocked_claims.append(claim_id)
        for reference in claim.get("evidence_refs", []):
            if not isinstance(reference, str):
                errors.append("claim evidence_refs entries must be strings")
                continue
            if not (root / reference).is_file():
                errors.append(f"claim evidence reference is missing: {reference}")
    missing_claim_ids = sorted(manifest_claim_ids - ledger_claim_ids)
    if missing_claim_ids:
        errors.append(f"claims missing from CLAIM_LEDGER.md: {', '.join(missing_claim_ids)}")
    extra_claim_ids = sorted(ledger_claim_ids - manifest_claim_ids)
    if extra_claim_ids:
        warnings.append(f"ledger claims absent from project.json: {', '.join(extra_claim_ids)}")

    unresolved_reviews: list[str] = []
    for review in project.get("reviews", []):
        if not isinstance(review, dict):
            errors.append("review entries must be objects")
            continue
        if review.get("state") == "open" and (
            int(review.get("critical", 0)) > 0 or int(review.get("major", 0)) > 0
        ):
            unresolved_reviews.append(str(review.get("review_id", "unknown")))

    for measurement in project.get("measurements", []):
        if not isinstance(measurement, dict):
            errors.append("measurement entries must be objects")
            continue
        name = measurement.get("name", "unknown")
        source = measurement.get("source")
        if not isinstance(source, str) or "#" not in source:
            continue
        relative, pointer = source.split("#", 1)
        path = root / relative
        if not path.is_file():
            errors.append(f"measurement source is missing: {name}: {relative}")
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            observed: Any = json.loads(path.read_text(encoding="utf-8"))
            for part in pointer.replace("/", ".").split("."):
                count = part.endswith("[]")
                part = part.removesuffix("[]")
                match = re.fullmatch(r"([^\[]*)(?:\[(\d+)\])?", part)
                if not match:
                    raise KeyError(part)
                key, index = match.groups()
                if key:
                    if not isinstance(observed, dict) or key not in observed:
                        raise KeyError(key)
                    observed = observed[key]
                if index is not None:
                    if not isinstance(observed, list):
                        raise KeyError(part)
                    observed = observed[int(index)]
                if count:
                    if not isinstance(observed, list):
                        raise KeyError(part)
                    observed = len(observed)
        except (KeyError, ValueError):
            errors.append(f"measurement source field is missing: {name}: {source}")
            continue
        expected = measurement.get("value")
        if isinstance(observed, float) and isinstance(expected, (int, float)):
            matches = math.isclose(
                float(observed), float(expected), rel_tol=1e-12, abs_tol=1e-12
            )
        else:
            matches = observed == expected
        if not matches:
            errors.append(
                f"measurement value does not match source: {name}: "
                f"{expected!r} != {observed!r}"
            )

    package = project.get("package", {})
    if not isinstance(package, dict):
        errors.append("package must be an object")
        package = {}
    package_blockers = package.get("blockers", [])
    if not isinstance(package_blockers, list):
        errors.append("package blockers must be an array")
        package_blockers = []
    package_files = package.get("files", [])
    if not isinstance(package_files, list):
        errors.append("package files must be an array")
        package_files = []
    for entry in package_files:
        if not isinstance(entry, dict):
            errors.append("package file entries must be objects")
            continue
        relative = entry.get("path")
        if not isinstance(relative, str):
            errors.append("package file path must be a string")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"package file is missing: {relative}")
        elif sha256_file(path) != entry.get("sha256"):
            errors.append(f"package file SHA-256 mismatch: {relative}")

    gate_receipts = project.get("gate_receipts", [])
    if not isinstance(gate_receipts, list):
        errors.append("gate_receipts must be an array")
        gate_receipts = []
    failed_gate_receipts: list[str] = []
    for entry in gate_receipts:
        if not isinstance(entry, dict):
            errors.append("gate receipt entries must be objects")
            continue
        gate_id = entry.get("gate_id")
        if not isinstance(gate_id, str) or not gate_id:
            errors.append("gate receipt gate_id must be a non-empty string")
            gate_id = "unknown"
        relative = entry.get("receipt")
        if not isinstance(relative, str) or not relative:
            errors.append(f"gate receipt path must be a non-empty string: {gate_id}")
        else:
            path = root / relative
            if not path.is_file():
                errors.append(f"gate receipt file is missing: {relative}")
            elif sha256_file(path) != entry.get("receipt_sha256"):
                errors.append(f"gate receipt SHA-256 mismatch: {relative}")
        if entry.get("scope") not in {
            "numbers",
            "citations",
            "review",
            "package",
            "reproducibility",
            "other",
        }:
            errors.append(f"invalid gate receipt scope: {gate_id}")
        if entry.get("state") not in {"passed", "failed", "candidate", "blocked"}:
            errors.append(f"invalid gate receipt state: {gate_id}")
        if entry.get("state") in {"failed", "blocked"}:
            failed_gate_receipts.append(gate_id)
        source_sha256 = entry.get("source_sha256")
        if source_sha256 is not None and (
            not isinstance(source_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", source_sha256)
        ):
            errors.append(f"invalid gate receipt source_sha256: {gate_id}")
        if not isinstance(entry.get("summary"), str) or not entry.get("summary"):
            errors.append(f"gate receipt summary must be a non-empty string: {gate_id}")

    ready = (
        not errors
        and project.get("status") == "package_ready"
        and package.get("state") == "ready"
        and not package_blockers
        and not blocked_claims
        and not unresolved_reviews
        and not failed_gate_receipts
    )
    return {
        "schema": "q-one-research-validation-v1",
        "root": str(root),
        "paper_id": project.get("paper_id"),
        "valid": not errors,
        "ready": ready,
        "status": project.get("status", "unknown"),
        "package_state": package.get("state", "unknown"),
        "errors": errors,
        "warnings": warnings,
        "blocked_claims": blocked_claims,
        "unresolved_reviews": unresolved_reviews,
        "failed_gate_receipts": failed_gate_receipts,
        "package_blockers": package_blockers,
        "claim_ids": sorted(manifest_claim_ids),
        "global_readiness_score": None,
    }
