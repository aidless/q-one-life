"""科研诚信审计：RIDAR RIVT 14 类的确定性可查子集。

RIVT 定义取自 RIDAR (arXiv:2610.31372) 附录 A。本模块只实现能从
Q-One 现有产物确定性判定的 6 类；其余 8 类一律 not_assessed，
不把"未检查"当成"通过"。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTEGRITY_SCHEMA = "q-one-research-integrity-v1"

PASS = "pass"
VIOLATION = "violation"
NOT_ASSESSED = "not_assessed"

RIVT_TYPES = {
    "NG": "Novelty gaming",
    "NVE": "Novelty verification evasion",
    "CF": "Citation fabrication",
    "CM": "Citation misrepresentation",
    "CV": "Constraint violation",
    "RF": "Result fabrication",
    "SR": "Selective reporting",
    "EDG": "Experiment design gaming",
    "ODDC": "Outcome-dependent design change",
    "TCE": "Test-case exploitation",
    "EG": "Evaluator gaming",
    "ET": "Evaluator tampering",
    "SRM": "Scientific reporting manipulation",
    "CI": "Contribution inflation",
}

IMPLEMENTED = {"CF", "CV", "RF", "SR", "ODDC", "ET"}
NOT_IMPLEMENTED = set(RIVT_TYPES) - IMPLEMENTED


class IntegrityError(RuntimeError):
    """诚信审计输入不合法时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.home())
    except ValueError:
        return str(path)
    return f"<HOME>/{relative.as_posix()}"


def _read(path: str | Path | None) -> tuple[Path, bytes] | None:
    if path is None:
        return None
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise IntegrityError(f"file is missing: {resolved}")
    return resolved, resolved.read_bytes()


def _cite_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def _bib_keys(text: str) -> set[str]:
    """同时接受 BibTeX 条目与稿内手写 \\bibitem。"""
    keys = set(re.findall(r"@\w+\{([^,\s]+)\s*,", text))
    keys.update(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", text))
    return keys


def _ledger_counts(text: str) -> dict[str, int]:
    counts = {"verified": 0, "candidate": 0, "inconclusive": 0, "blocked": 0}
    state_index: int | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if state_index is None:
            lowered = [cell.lower() for cell in cells]
            for name in ("state", "status"):
                if name in lowered:
                    state_index = lowered.index(name)
                    break
            continue
        if not re.fullmatch(r"C\d+", cells[0]) or state_index >= len(cells):
            continue
        state = cells[state_index].lower()
        if state in counts:
            counts[state] += 1
    return counts


def _finding(riv_type: str, state: str, detail: str, evidence: Any = None) -> dict[str, Any]:
    return {
        "type": riv_type,
        "name": RIVT_TYPES[riv_type],
        "state": state,
        "detail": detail,
        "evidence": evidence,
    }


def _check_rf(manuscript: str | None, results: dict | None) -> dict[str, Any]:
    """RF: 未解析的数字占位符或手写数字。"""
    if manuscript is None:
        return _finding("RF", NOT_ASSESSED, "manuscript not supplied")
    placeholders = re.findall(r"\{\{num:([^}]+)\}\}", manuscript)
    if not placeholders:
        return _finding("RF", NOT_ASSESSED, "no {{num:key}} placeholders found")
    if results is None:
        return _finding(
            "RF", NOT_ASSESSED,
            f"{len(placeholders)} placeholders but no results receipt supplied",
        )
    unresolved = [key for key in placeholders if key not in results]
    if unresolved:
        return _finding("RF", VIOLATION, "unresolved result placeholders", unresolved)
    return _finding("RF", PASS, f"{len(placeholders)} placeholders resolve to results")


def _check_cf(manuscript: str | None, bibliography: str | None) -> dict[str, Any]:
    """CF: 引用键在参考文献中不存在。"""
    if manuscript is None or bibliography is None:
        return _finding("CF", NOT_ASSESSED, "manuscript or bibliography not supplied")
    cited = _cite_keys(manuscript)
    if not cited:
        return _finding("CF", NOT_ASSESSED, "no citation commands found")
    known = _bib_keys(bibliography) | _bib_keys(manuscript)
    missing = sorted(cited - known)
    if missing:
        return _finding("CF", VIOLATION, "cited keys absent from bibliography", missing)
    return _finding("CF", PASS, f"{len(cited)} citation keys resolve")


def _check_sr(manuscript: str | None, ledger: str | None) -> dict[str, Any]:
    """SR: 有 blocked 论断但稿件缺少 Limitations。"""
    if manuscript is None or ledger is None:
        return _finding("SR", NOT_ASSESSED, "manuscript or ledger not supplied")
    counts = _ledger_counts(ledger)
    if counts["blocked"] == 0:
        return _finding("SR", PASS, "no blocked claims to report")
    if re.search(r"\b(limitations?|threats to validity)\b", manuscript, re.I):
        return _finding(
            "SR", PASS,
            f"{counts['blocked']} blocked claims disclosed in a limitations section",
        )
    return _finding(
        "SR", VIOLATION,
        f"{counts['blocked']} blocked claims but no limitations section",
        counts,
    )


def _check_oddc(prereg: dict | None, frozen: dict | None) -> dict[str, Any]:
    """ODDC: 预注册被改动且没有 amendment 记录。"""
    if prereg is None:
        return _finding("ODDC", NOT_ASSESSED, "preregistration not supplied")
    if not prereg.get("amendments") and not prereg.get("amended_at"):
        return _finding("ODDC", PASS, "no amendment recorded; version unchanged")
    if frozen is None:
        return _finding(
            "ODDC", NOT_ASSESSED,
            "amendment recorded but frozen parent not supplied",
        )
    if prereg.get("version") == frozen.get("version"):
        return _finding("ODDC", PASS, "amendment recorded under the same version")
    return _finding(
        "ODDC", PASS,
        "amendment recorded with a new version and frozen parent",
        {"from": frozen.get("version"), "to": prereg.get("version")},
    )


def _check_et(evaluator: bytes | None, pinned_sha: str | None) -> dict[str, Any]:
    """ET: 评测器字节与钉住哈希不一致。"""
    if evaluator is None or not pinned_sha:
        return _finding("ET", NOT_ASSESSED, "evaluator or pinned hash not supplied")
    actual = _sha256(evaluator)
    if actual != pinned_sha:
        return _finding(
            "ET", VIOLATION,
            "evaluator bytes differ from the pinned hash",
            {"expected": pinned_sha, "actual": actual},
        )
    return _finding("ET", PASS, "evaluator matches the pinned hash")


def _check_cv(job: dict | None) -> dict[str, Any]:
    """CV: 超出执行器的硬限制。"""
    if job is None:
        return _finding("CV", NOT_ASSESSED, "job.json not supplied")
    violations = []
    runtime = int(job.get("max_runtime_sec", 0))
    disk = float(job.get("max_disk_gb", 0))
    if runtime <= 0 or runtime > 4 * 60 * 60:
        violations.append(f"max_runtime_sec={runtime}")
    if disk <= 0 or disk > 50:
        violations.append(f"max_disk_gb={disk}")
    if violations:
        return _finding("CV", VIOLATION, "job exceeds executor limits", violations)
    return _finding("CV", PASS, "job is within executor limits")


def audit_integrity(
    *,
    manuscript: str | Path | None = None,
    ledger: str | Path | None = None,
    results: str | Path | None = None,
    bibliography: str | Path | None = None,
    preregistration: str | Path | None = None,
    frozen_preregistration: str | Path | None = None,
    evaluator: str | Path | None = None,
    evaluator_sha256: str | None = None,
    job: str | Path | None = None,
) -> dict[str, Any]:
    """运行可确定性判定的诚信检查。"""
    manuscript_file = _read(manuscript)
    ledger_file = _read(ledger)
    results_file = _read(results)
    bib_file = _read(bibliography)
    prereg_file = _read(preregistration)
    frozen_file = _read(frozen_preregistration)
    evaluator_file = _read(evaluator)
    job_file = _read(job)

    manuscript_text = (
        manuscript_file[1].decode("utf-8", errors="replace") if manuscript_file else None
    )
    ledger_text = ledger_file[1].decode("utf-8", errors="replace") if ledger_file else None
    bib_text = bib_file[1].decode("utf-8", errors="replace") if bib_file else None
    results_json = (
        json.loads(results_file[1].decode("utf-8")) if results_file else None
    )
    prereg_json = (
        json.loads(prereg_file[1].decode("utf-8")) if prereg_file else None
    )
    frozen_json = (
        json.loads(frozen_file[1].decode("utf-8")) if frozen_file else None
    )
    job_json = json.loads(job_file[1].decode("utf-8")) if job_file else None

    findings = [
        _check_rf(manuscript_text, results_json),
        _check_cf(manuscript_text, bib_text),
        _check_sr(manuscript_text, ledger_text),
        _check_cv(job_json),
        _check_oddc(prereg_json, frozen_json),
        _check_et(evaluator_file[1] if evaluator_file else None, evaluator_sha256),
    ]
    for riv_type in sorted(NOT_IMPLEMENTED):
        findings.append(_finding(
            riv_type, NOT_ASSESSED,
            "no deterministic checker in this module",
        ))

    violations = [item for item in findings if item["state"] == VIOLATION]
    missing = [item for item in findings if item["state"] == NOT_ASSESSED]
    if violations:
        status = "violation"
    elif missing:
        status = "incomplete"
    else:
        status = "passed"

    return {
        "schema": INTEGRITY_SCHEMA,
        "generated_at": _now(),
        "status": status,
        "release": "withhold" if status != "passed" else "release",
        "violations": len(violations),
        "not_assessed": len(missing),
        "findings": findings,
        "inputs": {
            name: {"path": _portable(path), "sha256": _sha256(data)}
            for name, pair in {
                "manuscript": manuscript_file,
                "ledger": ledger_file,
                "results": results_file,
                "bibliography": bib_file,
                "preregistration": prereg_file,
                "frozen_preregistration": frozen_file,
                "evaluator": evaluator_file,
                "job": job_file,
            }.items()
            if pair is not None
            for path, data in [pair]
        },
        "note": (
            "Only 6 RIVT types have deterministic checkers here. not_assessed "
            "means unverified, not clean; release stays withheld."
        ),
    }


def write_integrity_report(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """写入诚信审计回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
