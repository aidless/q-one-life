"""Claim ledger primitives: register, bind, verify and render."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "q-evidence-ledger-v1"
CLAIM_STATES = {"verified", "candidate", "inconclusive", "blocked", "unknown"}


class LedgerError(ValueError):
    """Raised when a ledger operation would break invariants."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": SCHEMA, "claims": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise LedgerError(f"unexpected schema: {payload.get('schema')}")
    return payload


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_claim(
    ledger_path: str | Path,
    claim_id: str,
    text: str,
    *,
    state: str = "candidate",
) -> dict[str, Any]:
    """Add a claim. Duplicate ids are rejected rather than overwritten."""
    if state not in CLAIM_STATES:
        raise LedgerError(f"invalid state: {state}")
    if not claim_id.strip() or not text.strip():
        raise LedgerError("claim_id and text must be non-empty")
    path = Path(ledger_path)
    payload = _load(path)
    if any(claim["claim_id"] == claim_id for claim in payload["claims"]):
        raise LedgerError(f"claim already registered: {claim_id}")
    claim = {"claim_id": claim_id, "text": text, "state": state, "evidence": []}
    payload["claims"].append(claim)
    _save(path, payload)
    return claim


def bind_evidence(
    ledger_path: str | Path,
    claim_id: str,
    evidence_path: str | Path,
    *,
    field: str | None = None,
) -> dict[str, Any]:
    """Attach a file (and optional field pointer) to a claim by content hash."""
    evidence = Path(evidence_path).expanduser().resolve()
    if not evidence.is_file():
        raise LedgerError(f"evidence file is missing: {evidence}")
    path = Path(ledger_path)
    payload = _load(path)
    claim = next((c for c in payload["claims"] if c["claim_id"] == claim_id), None)
    if claim is None:
        raise LedgerError(f"unknown claim: {claim_id}")
    entry = {"path": str(evidence), "sha256": _sha256_file(evidence), "bytes": evidence.stat().st_size}
    if field:
        entry["field"] = field
    claim["evidence"].append(entry)
    _save(path, payload)
    return entry


def verify_ledger(ledger_path: str | Path, *, require_evidence: bool = True) -> dict[str, Any]:
    """Re-hash every bound evidence file and report drift."""
    path = Path(ledger_path)
    payload = _load(path)
    errors: list[str] = []
    verified = 0
    for claim in payload["claims"]:
        if claim["state"] not in CLAIM_STATES:
            errors.append(f"{claim['claim_id']}: invalid state")
        if require_evidence and claim["state"] == "verified" and not claim["evidence"]:
            errors.append(f"{claim['claim_id']}: verified without evidence")
        for entry in claim["evidence"]:
            file = Path(entry["path"])
            if not file.is_file():
                errors.append(f"{claim['claim_id']}: evidence missing: {file}")
                continue
            if _sha256_file(file) != entry["sha256"]:
                errors.append(f"{claim['claim_id']}: evidence hash drift: {file}")
                continue
            verified += 1
    return {
        "schema": "q-evidence-verification-v1",
        "ledger": str(path),
        "claims": len(payload["claims"]),
        "evidence_checked": verified,
        "errors": errors,
        "result": "passed" if not errors else "failed",
    }


def render_report(ledger_path: str | Path, *, out: str | Path | None = None) -> str:
    """Render a markdown ledger table."""
    payload = _load(Path(ledger_path))
    lines = ["| ID | Claim | State | Evidence |", "|---|---|---|---|"]
    for claim in payload["claims"]:
        evidence = ", ".join(Path(e["path"]).name for e in claim["evidence"]) or "-"
        lines.append(f"| {claim['claim_id']} | {claim['text']} | {claim['state']} | {evidence} |")
    text = "\n".join(lines) + "\n"
    if out:
        target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return text


def bulk_bind(
    ledger_path: str | Path,
    claim_id: str,
    evidence_paths: Iterable[str | Path],
) -> list[dict[str, Any]]:
    """Convenience wrapper for binding several files at once."""
    return [bind_evidence(ledger_path, claim_id, item) for item in evidence_paths]
