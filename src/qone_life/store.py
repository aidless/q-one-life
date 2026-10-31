"""个人观测与回顾记录的本地追加式存储（带哈希链校验）。"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .locking import exclusive_file_lock
from .models import Observation
from .permissions import secure_append

GENESIS = "0" * 64
EVENT_TYPES = {"observation_recorded", "review_recorded"}


class StoreError(RuntimeError):
    """本地生活数据读取或校验失败时抛出。"""


def canonical_json(value: Any) -> str:
    """把对象序列化成规范 JSON（键排序、无多余空格），用于稳定地计算哈希。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_hash(event: dict[str, Any]) -> str:
    """计算单条事件的哈希：去掉 hash 字段本身后对规范 JSON 做 SHA-256。"""
    unsigned = {key: value for key, value in event.items() if key != "hash"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


class LifeStore:
    """一个 JSONL 文件，按顺序追加事件，并用哈希链串起来防篡改。"""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        """在文件锁保护下执行读写，避免并发写入互相踩踏。"""
        with exclusive_file_lock(self.lock_path):
            yield

    def _read_unlocked(self) -> list[dict[str, Any]]:
        """读取全部事件（调用方需已持有锁）。

        空行、非法 JSON、非对象行都视为数据损坏，直接报错而不是跳过，
        以免悄悄丢掉数据。
        """
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
        """校验事件序列：序号连续、类型合法、哈希链前后衔接。"""
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
        """校验整个文件，返回事件条数。"""
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return len(events)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """追加一条事件：先校验现有链，再补上序号、时间、前置哈希并写盘。"""
        if event_type not in EVENT_TYPES:
            raise StoreError(f"unknown event type: {event_type}")

        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)

            # 时间戳统一成 UTC、精确到秒、以 Z 结尾；id 与 hash 随后补齐。
            timestamp = (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
            event = {
                "seq": len(events) + 1,
                "ts": timestamp,
                "type": event_type,
                "payload": payload,
                "prev_hash": events[-1]["hash"] if events else GENESIS,
            }
            event["hash"] = event_hash(event)

            # 追加写入后立即 fsync，确保落盘。
            with secure_append(self.path) as handle:
                handle.write(canonical_json(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event

    def record_observation(self, observation: Observation) -> dict[str, Any]:
        """记录一条观测事件。"""
        return self.append("observation_recorded", observation.to_dict())

    def record_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        """记录一条回顾事件。"""
        return self.append("review_recorded", payload)

    def events(self) -> list[dict[str, Any]]:
        """校验并返回全部事件。"""
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return events

    def observations(self) -> list[Observation]:
        """从全部事件中还原出观测对象列表。"""
        result: list[Observation] = []
        for event in self.events():
            if event["type"] == "observation_recorded":
                result.append(Observation.from_payload(event["payload"]))
        return result
