"""个人观测的显式导出模式（脱敏或完整）。"""

from __future__ import annotations

import hashlib
from typing import Any

from .models import Observation


def _public_id(value: str, salt: str) -> str:
    """把原始标识加盐后做 SHA-256，取前 16 位作为不可反推的公开标识。"""
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


def export_observations(
    observations: list[Observation],
    *,
    redacted: bool = True,
    salt: str = "q-one-public-export",
) -> dict[str, Any]:
    """导出观测列表。

    - redacted=True：只保留度量本身的去标识字段（去掉备注、决策关联与原始来源串），
      观测 id 换成加盐哈希值；
    - redacted=False：导出完整记录。
    """
    if not redacted:
        rows = [observation.to_dict() for observation in observations]
    else:
        rows = []
        for observation in observations:
            rows.append(
                {
                    "observation_id": _public_id(observation.observation_id, salt),
                    "domain": observation.domain,
                    "metric": observation.metric,
                    "value": observation.value,
                    "minimum": observation.minimum,
                    "maximum": observation.maximum,
                    "observed_at": observation.observed_at,
                    "source_class": "user_recorded",
                }
            )
    return {
        "export_mode": "redacted" if redacted else "full",
        "observations": rows,
        "limitations": [
            "redaction removes notes, decision links, and raw source strings but values may remain sensitive",
            "review the export manually before sharing",
        ],
    }
