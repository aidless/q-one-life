"""Deterministic research-production controls for the Q-One portfolio.

This module deliberately separates orchestration signals from scientific
quality. It proposes the next piece of work, creates an external evidence
overlay, and checks whether a LaTeX tree is mechanically packageable. None of
these operations claims that a paper is ready for submission.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import io
import json
import math
import os
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .research import PROJECT_SCHEMA, sha256_file, validate_research_project

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


def triage_portfolio(
    portfolio: dict[str, Any],
    *,
    pilots: Sequence[dict[str, Any]] = (),
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Rank the next production work by transparent signals.

    The returned priority is an orchestration order, not a scientific-quality
    score. The source portfolio's human disposition is copied unchanged.
    """

    timestamp = generated_at or _now()
    generated = _parse_timestamp(timestamp) or datetime.now(timezone.utc)
    family_by_project = {
        family.get("canonical_project_id"): family
        for family in portfolio.get("families", [])
        if family.get("canonical_project_id")
    }
    record_by_project = {
        record.get("project_id"): record
        for record in [*portfolio.get("projects", []), *portfolio.get("candidates", [])]
        if isinstance(record, dict) and record.get("project_id")
    }
    records: list[dict[str, Any]] = []
    for project in portfolio.get("projects", []):
        family = family_by_project.get(project.get("project_id"), {})
        variant_count = max(0, len(family.get("members", [])) - 1)
        pilot_matches = _matched_pilots(project, pilots)
        pilot = pilot_matches[0] if pilot_matches else None
        overlay = record_by_project.get(project.get("metadata_project_id"))
        files = _merged_file_signals(
            project.get("files", {}),
            overlay.get("files") if overlay else None,
        )
        factors: list[dict[str, Any]] = []

        if pilot is not None:
            factors.append(
                {
                    "code": "PINNED_PILOT",
                    "points": 200,
                    "observed": (
                        f"Matched pilot {pilot['id']} at phase {pilot.get('phase', 'P0')}."
                    ),
                }
            )
        if project.get("metadata_project_id"):
            factors.append(
                {
                    "code": "QONE_OVERLAY",
                    "points": 40,
                    "observed": f"Q-One overlay metadata: {project['metadata_project_id']}.",
                }
            )
        if _has_file(files, "claim_ledgers"):
            factors.append(
                {"code": "CLAIM_LEDGER", "points": 35, "observed": "Claim ledger is present."}
            )
        if _has_file(files, "bibliographies"):
            factors.append(
                {
                    "code": "BIBLIOGRAPHY",
                    "points": 20,
                    "observed": "At least one bibliography file is present.",
                }
            )
        if _has_file(files, "pdfs"):
            factors.append(
                {"code": "COMPILED_PDF", "points": 15, "observed": "At least one PDF is present."}
            )
        if _has_file(files, "evidence_directories"):
            factors.append(
                {
                    "code": "EVIDENCE_DIRECTORY",
                    "points": 20,
                    "observed": "At least one evidence directory is present.",
                }
            )
        if str(project.get("target") or "").lower() == "arxiv":
            factors.append(
                {
                    "code": "ARXIV_TARGET",
                    "points": 15,
                    "observed": "Explicit arXiv target is recorded.",
                }
            )
        if project.get("status") not in {None, "unknown"}:
            factors.append(
                {
                    "code": "EXPLICIT_STATUS",
                    "points": 10,
                    "observed": f"Explicit status: {project['status']}.",
                }
            )
        modified = _parse_timestamp(project.get("modified_at"))
        if modified is not None and modified >= generated - timedelta(days=30):
            factors.append(
                {
                    "code": "RECENT_30D",
                    "points": 10,
                    "observed": "Canonical source changed within the last 30 days.",
                }
            )
        if variant_count:
            factors.append(
                {
                    "code": "VERSION_RECONCILIATION",
                    "points": 5,
                    "observed": (
                        f"{variant_count} extra normalized-title source version(s) require "
                        "review."
                    ),
                }
            )
        if project.get("project_type") == "legacy":
            factors.append(
                {
                    "code": "LEGACY_SOURCE",
                    "points": 0,
                    "observed": "Legacy source type; no points, review still required.",
                }
            )

        score = sum(int(factor["points"]) for factor in factors)
        disposition, reason = _suggested_disposition(
            project,
            pilot=pilot,
            variant_count=variant_count,
            generated=generated,
        )
        claim_ledger = _has_file(files, "claim_ledgers")
        bibliography = _has_file(files, "bibliographies")
        pdf = _has_file(files, "pdfs")
        if not project.get("target"):
            next_action = "confirm_target_and_scope"
        elif not claim_ledger:
            next_action = "create_claim_ledger"
        elif not bibliography:
            next_action = "build_bibliography"
        elif not pdf:
            next_action = "compile_manuscript"
        else:
            next_action = "run_claim_and_package_audit"

        records.append(
            {
                "family_id": project.get("family_id") or family.get("family_id"),
                "project_id": project.get("project_id"),
                "title": project.get("title"),
                "primary_source": project.get("primary_source"),
                "project_type": project.get("project_type"),
                "target": project.get("target"),
                "status": project.get("status", "unknown"),
                "final_disposition": project.get("disposition", "unreviewed"),
                "suggested_disposition": disposition,
                "suggested_next_action": next_action,
                "suggestion_reason": reason,
                "human_review_required": True,
                "pilot_ids": [item["id"] for item in pilot_matches],
                "priority_band": _priority_band(score, pilot),
                "production_priority": score,
                "priority_factors": factors,
                "observable_inputs": {
                    "claim_ledger": claim_ledger,
                    "bibliography": bibliography,
                    "compiled_pdf": pdf,
                    "evidence_directory": _has_file(files, "evidence_directories"),
                },
                "variants_to_reconcile": variant_count,
            }
        )

    priority_counts = Counter(record["priority_band"] for record in records)
    suggestion_counts = Counter(record["suggested_disposition"] for record in records)
    action_counts = Counter(record["suggested_next_action"] for record in records)
    pilot_ids = {
        pilot_id
        for record in records
        for pilot_id in record.get("pilot_ids", [])
    }
    return {
        "schema": TRIAGE_SCHEMA,
        "generated_at": timestamp,
        "source_portfolio": {
            "generated_at": portfolio.get("generated_at"),
            "canonical_projects": portfolio.get("summary", {}).get("canonical_projects"),
        },
        "definitions": {
            "production_priority": (
                "A transparent orchestration ordering based on declared workflow signals. "
                "It is not paper quality, readiness, acceptance probability, or evidence strength."
            ),
            "suggested_disposition": (
                "A machine proposal only. The source portfolio's human disposition remains "
                "authoritative until explicitly reviewed."
            ),
        },
        "summary": {
            "paper_families": len(records),
            "priority_bands": dict(sorted(priority_counts.items())),
            "suggested_dispositions": dict(sorted(suggestion_counts.items())),
            "next_actions": dict(sorted(action_counts.items())),
            "matched_pilots": sorted(pilot_ids),
            "final_dispositions_unchanged": dict(
                sorted(Counter(record["final_disposition"] for record in records).items())
            ),
            "global_readiness_score": None,
            "note": "No global readiness or quality score is produced.",
        },
        "projects": sorted(
            records,
            key=lambda item: (
                -int(item["production_priority"]),
                str(item["title"]),
                str(item["project_id"]),
            ),
        ),
    }


def render_triage_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Q-One research triage",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "The priority below orders production work only. It is not a paper-quality or",
        "readiness score. Final disposition remains human-owned.",
        "",
        "## Summary",
        "",
        f"- Paper families: {summary['paper_families']}",
        f"- Priority bands: `{json.dumps(summary['priority_bands'], sort_keys=True)}`",
        (
            "- Suggested dispositions: "
            f"`{json.dumps(summary['suggested_dispositions'], sort_keys=True)}`"
        ),
        f"- Global readiness score: `{summary['global_readiness_score']}`",
        "",
        "## Queue",
        "",
        "| Band | Priority | Pilot(s) | Suggested | Next action | Title |",
        "|---|---:|---|---|---|---|",
    ]
    for project in report["projects"]:
        title = str(project["title"]).replace("|", "\\|")
        pilots = ", ".join(project.get("pilot_ids", [])) or "-"
        lines.append(
            f"| {project['priority_band']} | {project['production_priority']} | "
            f"{pilots} | {project['suggested_disposition']} | "
            f"{project['suggested_next_action']} | {title} |"
        )
    lines.extend(
        [
            "",
            "The JSON companion records each scoring factor and the unchanged final disposition.",
            "",
        ]
    )
    return "\n".join(lines)


def render_triage_csv(report: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "family_id",
            "title",
            "priority_band",
            "production_priority",
            "pilot_ids",
            "suggested_disposition",
            "suggested_next_action",
            "final_disposition",
            "primary_source",
        ]
    )
    for project in report["projects"]:
        writer.writerow(
            [
                project.get("family_id") or "",
                project["title"],
                project["priority_band"],
                project["production_priority"],
                ";".join(project.get("pilot_ids", [])),
                project["suggested_disposition"],
                project["suggested_next_action"],
                project["final_disposition"],
                project["primary_source"],
            ]
        )
    return output.getvalue()


def write_triage(
    report: dict[str, Any],
    output: str | Path,
    *,
    markdown: str | Path | None = None,
    csv_path: str | Path | None = None,
) -> None:
    _write_json(output, report)
    if markdown is not None:
        target = Path(markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_markdown(report), encoding="utf-8")
    if csv_path is not None:
        target = Path(csv_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_triage_csv(report), encoding="utf-8")


def create_research_scaffold(
    portfolio: dict[str, Any],
    *,
    family_id: str,
    output_dir: str | Path,
    target: str = "arxiv",
    source: str | Path | None = None,
    evidence_paths: Iterable[str | Path] = (),
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Create a non-destructive overlay around one canonical paper family."""

    project_record = _family_project(portfolio, family_id)
    source_path = Path(source or project_record["primary_source"]).expanduser().resolve()
    if not source_path.is_file():
        raise ResearchFactoryError(f"source manuscript is missing: {source_path}")
    external = [str(Path(path).expanduser().resolve()) for path in evidence_paths]
    missing_evidence = [path for path in external if not Path(path).is_file()]
    if missing_evidence:
        raise ResearchFactoryError(
            "evidence source(s) are missing: " + ", ".join(missing_evidence)
        )
    root = Path(output_dir).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise ResearchFactoryError(f"scaffold output directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir()
    timestamp = generated_at or _now()
    source_hash = sha256_file(source_path)

    source_record = {
        "schema": "q-one-source-record-v1",
        "generated_at": timestamp,
        "family_id": family_id,
        "portfolio_project_id": project_record.get("project_id"),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "source_bytes": source_path.stat().st_size,
        "source_modified_at": datetime.fromtimestamp(
            source_path.stat().st_mtime, timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "title": project_record.get("title"),
        "project_type": project_record.get("project_type"),
    }
    source_record_path = root / "evidence" / "source_record.json"
    _write_json(source_record_path, source_record)

    evidence: list[dict[str, Any]] = [
        {
            "path": "evidence/source_record.json",
            "sha256": sha256_file(source_record_path),
            "state": "candidate",
            "origin": str(source_path),
            "description": "Q-One source identity record; this is not manuscript recomputation.",
        }
    ]
    if external:
        evidence_sources = {
            "schema": "q-one-evidence-sources-v1",
            "generated_at": timestamp,
            "sources": [
                {
                    "path": path,
                    "sha256": sha256_file(Path(path)),
                    "state": "candidate",
                }
                for path in external
                if Path(path).is_file()
            ],
            "missing": [],
        }
        evidence_sources_path = root / "evidence" / "sources.json"
        _write_json(evidence_sources_path, evidence_sources)
        evidence.append(
            {
                "path": "evidence/sources.json",
                "sha256": sha256_file(evidence_sources_path),
                "state": "candidate",
                "origin": "user-supplied source references",
                "description": "External evidence pointers; state is candidate until checked.",
            }
        )

    blockers = [
        "No claims have been registered from the current manuscript.",
        "No claim ledger has been independently verified.",
        "No bibliography verification or clean-room arXiv compile receipt exists.",
        "No scientific review has been closed against this overlay's current hashes.",
        "arXiv upload requires a separate user authorization and account action.",
    ]
    project = {
        "schema": PROJECT_SCHEMA,
        "paper_id": family_id,
        "title": project_record.get("title"),
        "status": "unknown",
        "target": target,
        "root": str(root),
        "origin": str(source_path),
        "manuscript": {
            "path": str(source_path),
            "sha256": source_hash,
            "published_source_sha256": None,
            "matches_published_source": None,
        },
        "evidence": evidence,
        "claims": [],
        "experiments": [],
        "reviews": [],
        "package": {
            "state": "not-started",
            "files": [],
            "blockers": blockers,
        },
        "measurements": [],
        "notes": [
            "Scaffold generated from the Q-One paper portfolio.",
            "The source manuscript was not modified or copied.",
            "No readiness, acceptance, award, or submission state is implied.",
        ],
    }
    project_path = root / "project.json"
    _write_json(project_path, project)

    ledger = f"""# {project['title']} Claim Ledger

Manuscript: `{source_path}`
Source SHA-256: `{source_hash}`

This overlay was created without modifying the source manuscript. Register only
claims that are present in the manuscript, and bind every numeric value to an
evidence file plus field and a recomputation command.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|

_No claims have been registered yet._
"""
    (root / "CLAIM_LEDGER.md").write_text(ledger, encoding="utf-8")

    pipeline = f"""# Research pipeline

Source: `{source_path}`
Source SHA-256: `{source_hash}`

| Stage | State | Required output |
|---|---|---|
| source-identity | candidate | Exact source hash and publication identity |
| claim-ledger | pending | Registered claims with evidence fields and recomputation |
| evidence-recomputation | pending | Reproduced numeric claims or explicit blockers |
| citation-verification | pending | Every citation resolved or marked unresolved |
| scientific-review | pending | Closed method, statistics, reproduction and writing findings |
| arxiv-package | pending | Clean source tree, bibliography, metadata and hashes |
| external-submission | locked | User authorization and account action |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same manuscript hash.
"""
    (root / "PIPELINE.md").write_text(pipeline, encoding="utf-8")

    brief = f"""# Authoring brief

Title: **{project['title']}**
Target: `{target}`
Manuscript: `{source_path}`
Source SHA-256: `{source_hash}`

The agent may:

- summarize and reorganize only registered claims;
- draft sections from evidence-bound claims;
- identify missing evidence, citations and experiments;
- propose figures from supplied data and reproducible scripts.

The agent must not:

- invent numbers, experiments, references, authors, licenses or receipts;
- upgrade an `inconclusive` claim to `verified`;
- move a `blocked` claim into the manuscript;
- upload or publish without a separate user action.

Write only after `CLAIM_LEDGER.md` contains the claims relevant to the requested
section. Preserve negative and failed results.
"""
    (root / "AUTHORING_BRIEF.md").write_text(brief, encoding="utf-8")

    readme = f"""# Q-One research overlay

This is an external overlay for **{project['title']}**.

- Source: `{source_path}`
- Source SHA-256: `{source_hash}`
- Portfolio family: `{family_id}`
- Target: `{target}`
- Status: `unknown`

The scaffold does not copy, rewrite or publish the source. Start with
`CLAIM_LEDGER.md`, then run `research-plan` and `research-validate`.
"""
    (root / "README.md").write_text(readme, encoding="utf-8")

    validation = validate_research_project(root)
    if not validation["valid"]:
        raise ResearchFactoryError(
            "generated scaffold is invalid: " + "; ".join(validation["errors"])
        )
    return {
        "schema": SCAFFOLD_SCHEMA,
        "generated_at": timestamp,
        "family_id": family_id,
        "root": str(root),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "project_path": str(project_path),
        "validation": validation,
    }


def _finding(action_id: str, priority: str, reason: str, done_when: str) -> dict[str, str]:
    return {
        "action_id": action_id,
        "priority": priority,
        "owner": "agent" if priority != "external" else "user",
        "reason": reason,
        "done_when": done_when,
    }


def build_research_plan(project_root: str | Path) -> dict[str, Any]:
    """Build the next evidence-gated actions for one overlay."""

    root = Path(project_root).expanduser().resolve()
    validation = validate_research_project(root)
    project_path = root / "project.json"
    if not project_path.is_file():
        raise ResearchFactoryError(f"project.json is missing: {root}")
    project = _load_json(project_path)
    manuscript = project.get("manuscript", {})
    claims = project.get("claims", [])
    experiments = project.get("experiments", [])
    reviews = project.get("reviews", [])
    package = project.get("package", {})
    gate_receipts = [
        item for item in project.get("gate_receipts", []) if isinstance(item, dict)
    ]

    mismatch = manuscript.get("matches_published_source") is False
    blocked_claims = [
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim, dict) and claim.get("state") == "blocked"
    ]
    pending_claims = [
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim, dict)
        and claim.get("state") in {"candidate", "inconclusive", "unknown"}
    ]
    reproduced = [
        item.get("experiment_id")
        for item in experiments
        if isinstance(item, dict) and item.get("state") == "reproduced"
    ]
    failed_experiments = [
        item.get("experiment_id")
        for item in experiments
        if isinstance(item, dict) and item.get("state") in {"failed", "blocked"}
    ]
    open_major = [
        item.get("review_id")
        for item in reviews
        if isinstance(item, dict)
        and item.get("state") == "open"
        and (int(item.get("critical", 0)) > 0 or int(item.get("major", 0)) > 0)
    ]
    numeric_gates = [
        item for item in gate_receipts if item.get("scope") in {"numbers", "reproducibility"}
    ]
    failed_numeric_gates = [
        item.get("gate_id")
        for item in numeric_gates
        if item.get("state") in {"failed", "blocked"}
    ]
    passed_numeric_gates = [
        item for item in numeric_gates if item.get("state") == "passed"
    ]
    bound_numeric_gates = [
        item
        for item in passed_numeric_gates
        if item.get("source_sha256") == manuscript.get("sha256")
    ]
    unbound_numeric_gates = [
        item.get("gate_id")
        for item in passed_numeric_gates
        if item.get("source_sha256") != manuscript.get("sha256")
    ]
    citation_gates = [
        item for item in gate_receipts if item.get("scope") == "citations"
    ]
    failed_citation_gates = [
        item.get("gate_id")
        for item in citation_gates
        if item.get("state") in {"failed", "blocked"}
    ]
    passed_citation_gates = [
        item for item in citation_gates if item.get("state") == "passed"
    ]
    bound_citation_gates = [
        item
        for item in passed_citation_gates
        if item.get("source_sha256") == manuscript.get("sha256")
    ]
    unbound_citation_gates = [
        item.get("gate_id")
        for item in passed_citation_gates
        if item.get("source_sha256") != manuscript.get("sha256")
    ]
    failed_gate_receipts = [
        item.get("gate_id")
        for item in gate_receipts
        if item.get("state") in {"failed", "blocked"}
    ]

    source_state = "blocked" if mismatch else (
        "verified" if manuscript.get("matches_published_source") is True else "candidate"
    )
    if not claims:
        ledger_state = "pending"
    elif blocked_claims:
        ledger_state = "blocked"
    elif pending_claims:
        ledger_state = "candidate"
    else:
        ledger_state = "verified"
    if failed_experiments or failed_numeric_gates:
        recomputation_state = "blocked"
    elif bound_numeric_gates and not unbound_numeric_gates:
        recomputation_state = "verified"
    elif passed_numeric_gates:
        recomputation_state = "candidate"
    else:
        recomputation_state = (
            "verified" if reproduced and not pending_claims else "pending"
        )

    manuscript_path = Path(str(manuscript.get("path", "")))
    if not manuscript_path.is_absolute():
        manuscript_path = root / manuscript_path
    source_dir = manuscript_path.parent if manuscript_path.is_file() else root
    bibliography_candidates = list(root.glob("**/*.bib")) + list(
        source_dir.glob("*.bib")
    ) + list(source_dir.glob("*.bbl")) + list(source_dir.glob("bibliography.tex"))
    if failed_citation_gates:
        citation_state = "blocked"
    elif bound_citation_gates and not unbound_citation_gates:
        citation_state = "verified"
    elif bibliography_candidates:
        citation_state = "candidate"
    else:
        citation_state = "pending"
    review_state = "blocked" if open_major else (
        "verified" if reviews and not any(
            isinstance(item, dict) and item.get("state") == "open" for item in reviews
        ) else "pending"
    )
    package_blockers = package.get("blockers", [])
    package_state = "blocked" if package_blockers else (
        "verified" if validation.get("ready") else "pending"
    )
    citation_details = (
        f"Passed citation gates bound to the current source: "
        f"{len(bound_citation_gates)}."
        if citation_state == "verified"
        else "A bibliography file is only a candidate until citations resolve."
    )
    stages = [
        {
            "stage": "source-identity",
            "state": source_state,
            "details": "The local source hash is checked; publication identity is separate.",
        },
        {
            "stage": "claim-ledger",
            "state": ledger_state,
            "details": "Claims must be registered and bound to evidence fields.",
        },
        {
            "stage": "evidence-recomputation",
            "state": recomputation_state,
            "details": (
                f"Native gates passed: {len(passed_numeric_gates)}; "
                f"bound to the current source: {len(bound_numeric_gates)}. "
                "A completed experiment is not a reproduced experiment."
            ),
        },
        {
            "stage": "citation-verification",
            "state": citation_state,
            "details": citation_details,
        },
        {
            "stage": "scientific-review",
            "state": review_state,
            "details": "Open Critical or Major findings block the package.",
        },
        {
            "stage": "arxiv-package",
            "state": package_state,
            "details": "Mechanical packageability is separate from scientific readiness.",
        },
        {
            "stage": "external-submission",
            "state": "locked",
            "details": "Upload, account use and publication require explicit user authorization.",
        },
    ]
    actions: list[dict[str, str]] = []
    if not validation.get("valid"):
        actions.append(
            _finding(
                "repair_overlay_integrity",
                "P0",
                "The overlay itself fails schema, hash, ledger or manifest validation.",
                "`research-validate` returns valid=true against the current bytes.",
            )
        )
    if mismatch:
        actions.append(
            _finding(
                "resynchronize_published_source",
                "P0",
                "The local manuscript does not match the published source hash.",
                "The exact source is recovered or the publication receipt is refreshed.",
            )
        )
    if not claims:
        actions.append(
            _finding(
                "register_claims",
                "P0",
                "No manuscript claims are in the overlay.",
                "Every numeric and causal claim has an ID, location, evidence field and status.",
            )
        )
    if pending_claims:
        actions.append(
            _finding(
                "close_inconclusive_claims",
                "P0",
                f"Claims are not verified: {', '.join(pending_claims[:12])}.",
                "Each claim is verified, explicitly hedged with missing evidence, or removed.",
            )
        )
    if blocked_claims:
        actions.append(
            _finding(
                "remove_or_repair_blocked_claims",
                "P0",
                f"Blocked claims cannot enter strong prose: {', '.join(blocked_claims)}.",
                "Blocked claims are absent from manuscript assertions or repaired.",
            )
        )
    if failed_gate_receipts:
        actions.append(
            _finding(
                "repair_failed_native_gates",
                "P0",
                f"Native gate receipts failed: {', '.join(failed_gate_receipts)}.",
                "Each failed gate is repaired or explicitly blocked in the manuscript scope.",
            )
        )
    if unbound_numeric_gates:
        actions.append(
            _finding(
                "bind_native_gate_to_current_source",
                "P1",
                f"Passed numeric gates are not bound to the current source: "
                f"{', '.join(str(item) for item in unbound_numeric_gates)}.",
                "Re-run each gate against the current source and bind its exact hash.",
            )
        )
    if failed_citation_gates:
        actions.append(
            _finding(
                "repair_failed_citation_gates",
                "P0",
                f"Native citation gates failed: {', '.join(failed_citation_gates)}.",
                "Every citation resolves against the current source or is explicitly removed.",
            )
        )
    if unbound_citation_gates:
        actions.append(
            _finding(
                "bind_citation_gate_to_current_source",
                "P1",
                "Passed citation gates are not bound to the current source: "
                + ", ".join(str(item) for item in unbound_citation_gates)
                + ".",
                "Re-run the citation audit against the current source and bind its exact hash.",
            )
        )
    if not reproduced and not passed_numeric_gates:
        actions.append(
            _finding(
                "reproduce_required_numeric_claims",
                "P1",
                "No experiment has a reproduced receipt in this overlay.",
                "Required numeric claims have a command, environment and matching output hash.",
            )
        )
    if not bibliography_candidates:
        actions.append(
            _finding(
                "build_bibliography",
                "P1",
                "No bibliography file is visible in the overlay.",
                "Every citation resolves to a source record or is marked unresolved.",
            )
        )
    if open_major:
        actions.append(
            _finding(
                "close_scientific_review",
                "P0",
                f"Open review findings remain: {', '.join(open_major)}.",
                "No open Critical or Major finding remains against the current hashes.",
            )
        )
    if package_blockers:
        actions.append(
            _finding(
                "resolve_package_blockers",
                "P1",
                "The package manifest contains unresolved blockers.",
                "The source tree, bibliography, compiled PDF and hashes are complete.",
            )
        )
    actions.append(
        _finding(
            "external_submission_gate",
            "external",
            "Q-One cannot perform an account-level arXiv action on its own.",
            "The user explicitly authorizes upload and checks metadata, license and author list.",
        )
    )
    return {
        "schema": PLAN_SCHEMA,
        "generated_at": _now(),
        "root": str(root),
        "paper_id": project.get("paper_id"),
        "title": project.get("title"),
        "target": project.get("target"),
        "validation_valid": validation.get("valid"),
        "validation_ready": validation.get("ready"),
        "gate_summary": {
            "receipts": len(gate_receipts),
            "passed_numeric": len(passed_numeric_gates),
            "bound_numeric_to_current_source": len(bound_numeric_gates),
            "unbound_passed_numeric": unbound_numeric_gates,
            "passed_citations": len(passed_citation_gates),
            "bound_citations_to_current_source": len(bound_citation_gates),
            "unbound_passed_citations": unbound_citation_gates,
            "failed_or_blocked": failed_gate_receipts,
        },
        "stages": stages,
        "next_actions": sorted(actions, key=lambda item: (item["priority"], item["action_id"])),
        "global_readiness_score": None,
        "notes": [
            "No global score is produced.",
            "Unknown is not zero.",
            "A mechanical package check is not scientific readiness.",
        ],
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Research plan: {plan['title']}",
        "",
        f"Paper ID: `{plan['paper_id']}`",
        f"Validation: valid=`{plan['validation_valid']}`, ready=`{plan['validation_ready']}`",
        "",
        "## Stages",
        "",
        "| Stage | State | Notes |",
        "|---|---|---|",
    ]
    for stage in plan["stages"]:
        lines.append(f"| {stage['stage']} | {stage['state']} | {stage['details']} |")
    lines.extend(
        [
            "",
            "## Next actions",
            "",
            "| Priority | Action | Owner | Done when |",
            "|---|---|---|---|",
        ]
    )
    for action in plan["next_actions"]:
        lines.append(
            f"| {action['priority']} | {action['action_id']} | {action['owner']} | "
            f"{action['done_when']} |"
        )
    lines.extend(["", "No submission action is implied by this plan.", ""])
    return "\n".join(lines)


def write_plan(plan: dict[str, Any], output: str | Path, markdown: str | Path | None = None) -> None:
    _write_json(output, plan)
    if markdown is not None:
        target = Path(markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_plan_markdown(plan), encoding="utf-8")


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


def audit_arxiv_package(
    source_dir: str | Path,
    *,
    main_file: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Audit a LaTeX tree for mechanical arXiv packaging."""

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
    main_text = main.read_text(encoding="utf-8", errors="replace") if main.is_file() else ""
    main_check = _strip_tex_comments(main_text)
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
            graphics_paths.extend(
                root / value for value in re.findall(r"\{([^}]+)\}", graphics_match.group(1))
            )
    for name, text in tex_texts.items():
        for match in REFERENCE_RE.finditer(text):
            kind = match.group("kind")
            target = match.group("target").strip()
            if not _resolve_reference(
                root,
                target,
                kind,
                graphics_paths=graphics_paths,
            ):
                blockers.append(f"referenced {kind} target is missing in {name}: {target}")

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
        "package_sha256": hashlib.sha256(
            "\n".join(
                f"{item['path']}\0{item['sha256']}" for item in file_records
            ).encode("utf-8")
        ).hexdigest(),
        "notes": [
            "This is a source-tree audit, not a clean-room LaTeX compile.",
            "The package hash covers the sorted path/hash manifest, not tar bytes.",
        ],
    }


def write_package_audit(
    audit: dict[str, Any],
    output: str | Path,
) -> None:
    _write_json(output, audit)


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


def audit_native_paper_ledger(
    ledger_path: str | Path,
    workspace_root: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Audit a native numeric ledger without rewriting it.

    The adapter recognizes the common Q-One paper-ledger shape:
    entries with source, value and either field, derived, field_waiver or an
    explicit unrecoverable retraction reason.
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
    mechanically_valid = not any(
        counts[key]
        for key in (
            "invalid_entry",
            "missing_source_file",
            "unparseable_source",
            "missing_field",
            "value_mismatch",
        )
    )
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


def optimize_portfolio(
    portfolio: dict[str, Any],
    pilots: list[dict[str, Any]],
    capacity: int,
) -> dict[str, Any]:
    """Rank paper families by evidence ROI using observable signals only.

    publishability is evidence completeness, never a quality prediction.
    """
    if capacity < 1:
        raise ResearchFactoryError("capacity must be at least 1")
    projects = portfolio.get("projects") or []
    overlay_by_title: dict[str, dict[str, Any]] = {}
    overlay_by_source: dict[str, dict[str, Any]] = {}
    for pilot in pilots:
        for title in pilot.get("title_contains_any", []) or []:
            overlay_by_title[str(title).lower()] = pilot
        for fragment in pilot.get("source_contains_any", []) or []:
            overlay_by_source[str(fragment)] = pilot
    # Resolve overlay directories from the research tree by pilot id.
    research_root = Path("research")
    overlay_dirs: dict[str, Path] = {}
    if research_root.is_dir():
        for candidate in research_root.glob("*/project.json"):
            overlay_dirs[candidate.parent.name] = candidate.parent

    ranked: list[dict[str, Any]] = []
    for project in projects:
        title = str(project.get("title") or "")
        primary_source = str(project.get("primary_source") or "")
        overlay = overlay_by_title.get(title.lower())
        if overlay is None:
            for fragment, pilot in overlay_by_source.items():
                if fragment and fragment in primary_source:
                    overlay = pilot
                    break
        overlay_path: Path | None = None
        if overlay:
            explicit = overlay.get("overlay_path")
            if explicit:
                overlay_path = Path(str(explicit))
            else:
                pilot_id = str(overlay.get("id") or "")
                suffix = pilot_id.split("-", 1)[-1] if "-" in pilot_id else pilot_id
                for name, directory in overlay_dirs.items():
                    if suffix and suffix in name:
                        overlay_path = directory
                        break
        blocked = candidate = verified = 0
        missing_gates = 0
        if overlay_path and (overlay_path / "project.json").is_file():
            try:
                payload = json.loads((overlay_path / "project.json").read_text(encoding="utf-8"))
            except ValueError:
                payload = {}
            for claim in payload.get("claims", []) or []:
                state = claim.get("state")
                if state == "blocked":
                    blocked += 1
                elif state in {"candidate", "inconclusive", "unknown"}:
                    candidate += 1
                elif state == "verified":
                    verified += 1
            gates = payload.get("gate_receipts", []) or []
            missing_gates = sum(
                1 for gate in gates
                if isinstance(gate, dict) and gate.get("state") in {"failed", "blocked"}
            )
        total = blocked + candidate + verified
        close_cost = blocked + missing_gates
        evidence_gap = (blocked + candidate) / total if total else 1.0
        publishability = verified / total if total else 0.0
        roi = publishability / close_cost if close_cost > 0 else publishability
        ranked.append({
            "family_id": project.get("family_id"),
            "title": title,
            "priority_band": project.get("priority_band"),
            "verified": verified,
            "candidate": candidate,
            "blocked": blocked,
            "missing_gates": missing_gates,
            "close_cost": close_cost,
            "evidence_gap": round(evidence_gap, 6),
            "publishability": round(publishability, 6),
            "roi": round(roi, 6),
        })

    ranked.sort(key=lambda item: (-item["roi"], item["close_cost"], item["title"]))
    selected = ranked[:capacity]
    return {
        "schema": "q-one-allocation-v1",
        "capacity": capacity,
        "considered": len(ranked),
        "ranked": selected,
        "note": (
            "ROI uses evidence completeness only. It is not a paper-quality "
            "score and does not authorize publication."
        ),
    }
