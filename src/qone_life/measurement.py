"""每日测量记录：带 SHA-256 哈希链，保证记录不可篡改。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .locking import exclusive_file_lock
from .permissions import secure_append
from .store import GENESIS, canonical_json, event_hash

MEASUREMENT_TYPES = {"code_commit", "experiment_run", "model_review", "decision", "outcome"}
MEASUREMENT_FIELDS = ("subject", "metric", "value", "unit", "definition", "source")
DECISION_FIELDS = ("subject", "chosen", "rationale", "evidence", "expected_outcome")
OUTCOME_FIELDS = ("subject", "observed_outcome", "decision_seq")


class MeasurementError(ValueError):
    """测量记录格式不合法时抛出的异常。"""


def _read_measurements(path: Path) -> list[dict[str, Any]]:
    """读取整份测量文件，逐行解析为事件列表；空行或非法 JSON 都会报错。"""
    if not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise MeasurementError(f"blank line at measurement {line_number}")
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MeasurementError(f"invalid JSON at measurement {line_number}") from exc
            if not isinstance(event, dict):
                raise MeasurementError(f"measurement {line_number} is not an object")
            events.append(event)
    return events


def _verify_chain(events: list[dict[str, Any]]) -> int:
    """校验整条哈希链：序号连续、类型合法、必填字段齐全、前后哈希衔接一致。"""
    previous = GENESIS
    for seq, event in enumerate(events, start=1):
        if event.get("seq") != seq:
            raise MeasurementError(f"sequence mismatch at measurement {seq}")
        if event.get("type") not in MEASUREMENT_TYPES:
            raise MeasurementError(f"unknown measurement type at {seq}: {event.get('type')}")
        payload = event.get("payload", {})
        # 不同记录类型的必填字段不同。
        if event.get("type") == "decision":
            required = DECISION_FIELDS
        elif event.get("type") == "outcome":
            required = OUTCOME_FIELDS
        else:
            required = MEASUREMENT_FIELDS
        for field in required:
            if not str(payload.get(field) or "").strip():
                raise MeasurementError(f"missing field {field!r} at measurement {seq}")
        if event.get("prev_hash") != previous or event.get("hash") != event_hash(event):
            raise MeasurementError(f"hash-chain mismatch at measurement {seq}")
        previous = event["hash"]
    return len(events)


class MeasurementStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    def _lock(self):
        return exclusive_file_lock(self.lock_path)

    def verify(self) -> int:
        with self._lock():
            return _verify_chain(_read_measurements(self.path))

    def add(
        self,
        record_type: str,
        subject: str,
        metric: str,
        value: Any,
        unit: str,
        definition: str,
        source: str,
    ) -> dict[str, Any]:
        if record_type not in MEASUREMENT_TYPES:
            raise MeasurementError(f"unknown measurement type: {record_type}")
        for name in MEASUREMENT_FIELDS:
            if not str(locals().get(name) or "").strip():
                raise MeasurementError(f"{name!r} must not be empty")
        payload = {
            "subject": subject,
            "metric": metric,
            "value": value,
            "unit": unit,
            "definition": definition,
            "source": source,
        }
        return self._append_payload(record_type, payload)

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock():
            _verify_chain(_read_measurements(self.path))
            return _read_measurements(self.path)

    def _append_payload(self, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """在锁内校验现有链、生成新事件并安全落盘，返回写入的事件。"""
        with self._lock():
            events = _read_measurements(self.path)
            _verify_chain(events)
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            event = {
                "seq": len(events) + 1,
                "ts": timestamp,
                "type": record_type,
                "payload": payload,
                "prev_hash": events[-1]["hash"] if events else GENESIS,
            }
            event["hash"] = event_hash(event)
            with secure_append(self.path) as handle:
                handle.write(canonical_json(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event

    def decide(
        self, subject: str, options: list[str], chosen: str,
        rationale: str, evidence: str, expected_outcome: str,
        cost: str | None = None,
        reversibility: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        if not options or chosen not in options:
            raise MeasurementError("chosen must be one of the supplied options")
        for name, value in (
            ("subject", subject), ("chosen", chosen), ("rationale", rationale),
            ("evidence", evidence), ("expected_outcome", expected_outcome),
        ):
            if not str(value or "").strip():
                raise MeasurementError(f"{name!r} must not be empty")
        if reversibility is not None and reversibility not in {"reversible", "partially_reversible", "irreversible"}:
            raise MeasurementError("reversibility must be reversible, partially_reversible, or irreversible")
        payload = {
            "subject": subject,
            "options": list(options),
            "chosen": chosen,
            "rationale": rationale,
            "evidence": evidence,
            "expected_outcome": expected_outcome,
        }
        if cost is not None:
            payload["cost"] = str(cost).strip()
        if reversibility is not None:
            payload["reversibility"] = reversibility
        if deadline is not None:
            payload["deadline"] = str(deadline).strip()
        return self._append_payload("decision", payload)

    def record_outcome(
        self, decision_seq: int, subject: str, observed_outcome: str, matched: bool,
        latency_sec: int | None = None,
    ) -> dict[str, Any]:
        if not str(subject or "").strip() or not str(observed_outcome or "").strip():
            raise MeasurementError("subject and observed_outcome must not be empty")
        if latency_sec is not None and (isinstance(latency_sec, bool) or not isinstance(latency_sec, int) or latency_sec < 0):
            raise MeasurementError("latency_sec must be a non-negative integer")
        events = self.list_all()
        # 定位被回访的那条决策。
        target = None
        for e in events:
            if e["seq"] == decision_seq:
                target = e
                break
        if not target or target["type"] != "decision":
            raise MeasurementError(f"no decision at seq {decision_seq}")
        payload = {
            "subject": subject,
            "observed_outcome": observed_outcome,
            "decision_seq": int(decision_seq),
            "matched": bool(matched),
        }
        if latency_sec is not None:
            payload["latency_sec"] = latency_sec
        return self._append_payload("outcome", payload)

    def decisions(self) -> list[dict[str, Any]]:
        return [e for e in self.list_all() if e["type"] == "decision"]

    def outcomes(self) -> list[dict[str, Any]]:
        return [e for e in self.list_all() if e["type"] == "outcome"]

    def hit_rate(self) -> dict[str, Any]:
        outcomes = self.outcomes()
        if not outcomes:
            return {"value": "unknown", "n": 0}
        matched = 0
        for o in outcomes:
            if o["payload"].get("matched") is True:
                matched += 1
        return {"value": matched / len(outcomes), "matched": matched, "n": len(outcomes)}


def plan_experiment(
    claim_id: str,
    missing_evidence: str,
    proposed_experiment: str,
    resource_requirement: str,
    estimated_duration_sec: int | None = None,
    statistical_power: float | None = None,
) -> dict[str, Any]:
    """为某个待补实验生成只读的执行计划，本身不真正运行实验。"""
    lowered = resource_requirement.lower()
    approval_required = False
    for token in ("gpu", "paid", "cloud", "external api", "submission", "account"):
        if token in lowered:
            approval_required = True
            break
    if estimated_duration_sec is not None and estimated_duration_sec <= 0:
        raise MeasurementError("estimated_duration_sec must be a positive integer")
    if statistical_power is not None and not (0 < statistical_power < 1):
        raise MeasurementError("statistical_power must be between 0 and 1")
    return {
        "schema": "q-one-experiment-plan-v1",
        "claim_id": claim_id,
        "missing_evidence": missing_evidence,
        "proposed_experiment": proposed_experiment,
        "resource_requirement": resource_requirement,
        "execution_plan": [
            "Verify claim state is blocked or inconclusive in the project ledger.",
            "Confirm the proposed experiment addresses the named evidence gap.",
            "Prepare inputs, environment and expected output format.",
            "Execute the experiment and produce a reproducible receipt.",
            "Bind the receipt hash into the claim ledger.",
        ],
        "estimated_cost": resource_requirement,
        "estimated_duration_sec": estimated_duration_sec,
        "statistical_power": statistical_power,
        "approval_required": approval_required,
        "auto_executable": not approval_required,
        "status": "plan_only",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
