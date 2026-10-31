"""声明式账本（claim ledger）的基础原语：登记、绑定证据、校验与渲染。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCHEMA = "q-evidence-ledger-v1"
CLAIM_STATES = {"verified", "candidate", "inconclusive", "blocked", "unknown"}


class LedgerError(ValueError):
    """账本操作会破坏约束时抛出的错误。"""


def _sha256_file(path: Path) -> str:
    """分块计算文件的 sha256，避免一次性读入大文件。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    """读取账本；文件不存在时返回空骨架，schema 不符时抛错。"""
    if not path.is_file():
        return {"schema": SCHEMA, "claims": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise LedgerError(f"unexpected schema: {payload.get('schema')}")
    return payload


def _save(path: Path, payload: dict[str, Any]) -> None:
    """把账本写回磁盘（必要时创建父目录）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_claim(
    ledger_path: str | Path,
    claim_id: str,
    text: str,
    *,
    state: str = "candidate",
) -> dict[str, Any]:
    """登记一条声明；重复的 id 会被拒绝，而不是覆盖旧记录。"""
    if state not in CLAIM_STATES:
        raise LedgerError(f"invalid state: {state}")
    if not claim_id.strip() or not text.strip():
        raise LedgerError("claim_id and text must be non-empty")
    path = Path(ledger_path)
    payload = _load(path)
    # 先检查是否已存在同 id 的声明，存在则拒绝重复登记。
    for claim in payload["claims"]:
        if claim["claim_id"] == claim_id:
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
    """按内容哈希把某个文件（及可选字段指针）绑定到一条声明上。"""
    evidence = Path(evidence_path).expanduser().resolve()
    if not evidence.is_file():
        raise LedgerError(f"evidence file is missing: {evidence}")
    path = Path(ledger_path)
    payload = _load(path)
    # 找到目标声明；找不到就报错。
    claim = None
    for candidate in payload["claims"]:
        if candidate["claim_id"] == claim_id:
            claim = candidate
            break
    if claim is None:
        raise LedgerError(f"unknown claim: {claim_id}")
    entry = {
        "path": str(evidence),
        "sha256": _sha256_file(evidence),
        "bytes": evidence.stat().st_size,
    }
    if field:
        entry["field"] = field
    claim["evidence"].append(entry)
    _save(path, payload)
    return entry


def verify_ledger(ledger_path: str | Path, *, require_evidence: bool = True) -> dict[str, Any]:
    """重新对每条绑定证据做哈希，报告是否有漂移。"""
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
    result = "passed"
    if errors:
        result = "failed"
    return {
        "schema": "q-evidence-verification-v1",
        "ledger": str(path),
        "claims": len(payload["claims"]),
        "evidence_checked": verified,
        "errors": errors,
        "result": result,
    }


def render_report(ledger_path: str | Path, *, out: str | Path | None = None) -> str:
    """把账本渲染成 markdown 表格；给了 out 就同时写文件。"""
    payload = _load(Path(ledger_path))
    lines = ["| ID | Claim | State | Evidence |", "|---|---|---|---|"]
    for claim in payload["claims"]:
        # 把一条声明的多个证据文件名拼成逗号分隔；没有证据时显示 "-"。
        names = []
        for item in claim["evidence"]:
            names.append(Path(item["path"]).name)
        evidence = "-"
        if names:
            evidence = ", ".join(names)
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
    """一次性把多个文件绑定到同一条声明的便捷包装。"""
    entries = []
    for item in evidence_paths:
        entries.append(bind_evidence(ledger_path, claim_id, item))
    return entries
