"""Local append-only store for personal observations and review records."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import Observation

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


GENESIS = "0" * 64
EVENT_TYPES = {"observation_recorded", "review_recorded"}


class StoreError(RuntimeError):
    """Raised when local life data cannot be read or verified."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_hash(event: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in event.items() if key != "hash"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


class LifeStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise StoreError(f"blank line at event {line_number}")
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise StoreError(f"invalid JSON at event {line_number}") from exc
                if not isinstance(event, dict):
                    raise StoreError(f"event {line_number} is not an object")
                events.append(event)
        return events

    @staticmethod
    def _verify_events(events: list[dict[str, Any]]) -> None:
        previous = GENESIS
        for expected_seq, event in enumerate(events, start=1):
            if event.get("seq") != expected_seq:
                raise StoreError(f"sequence mismatch at event {expected_seq}")
            if event.get("type") not in EVENT_TYPES:
                raise StoreError(f"unknown event type at event {expected_seq}")
            if event.get("prev_hash") != previous or event.get("hash") != event_hash(event):
                raise StoreError(f"hash-chain mismatch at event {expected_seq}")
            previous = event["hash"]

    def verify(self) -> int:
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return len(events)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise StoreError(f"unknown event type: {event_type}")
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            event = {
                "seq": len(events) + 1,
                "ts": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "type": event_type,
                "payload": payload,
                "prev_hash": events[-1]["hash"] if events else GENESIS,
            }
            event["hash"] = event_hash(event)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event

    def record_observation(self, observation: Observation) -> dict[str, Any]:
        return self.append("observation_recorded", observation.to_dict())

    def record_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.append("review_recorded", payload)

    def events(self) -> list[dict[str, Any]]:
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return events

    def observations(self) -> list[Observation]:
        result: list[Observation] = []
        for event in self.events():
            if event["type"] == "observation_recorded":
                result.append(Observation.from_payload(event["payload"]))
        return result
