"""方向多样性排序：在 ROI 之外给少尝试方向探索奖励。

只做确定性贪心选择；不改变 ROI 定义，也不产生质量评分。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIVERSITY_SCHEMA = "q-one-direction-allocation-v1"


class DiversityError(RuntimeError):
    """输入不合法时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rank_with_diversity(
    items: list[dict[str, Any]],
    capacity: int,
    *,
    exploration_bonus: float = 0.15,
    decay: float = 1.0,
    open_cost: float = 0.05,
) -> dict[str, Any]:
    """贪心选择：score = roi + bonus/(1+count)^decay - open_cost(首次)。"""
    if capacity < 1:
        raise DiversityError("capacity must be at least 1")
    if not items:
        raise DiversityError("items is empty")
    if exploration_bonus < 0 or open_cost < 0 or decay < 0:
        raise DiversityError("bonus, open_cost and decay must be non-negative")

    remaining = []
    for item in items:
        family_id = str(item.get("family_id") or "").strip()
        if not family_id:
            raise DiversityError("every item needs a family_id")
        roi = item.get("roi")
        if not isinstance(roi, (int, float)):
            raise DiversityError(f"item {family_id} has a non-numeric roi")
        remaining.append({
            "family_id": family_id,
            "roi": float(roi),
            "direction": str(item.get("direction") or "unassigned"),
        })

    counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < capacity:
        best = None
        best_original = None
        for item in remaining:
            direction = item["direction"]
            count = counts.get(direction, 0)
            bonus = exploration_bonus / ((1 + count) ** decay)
            cost = open_cost if count == 0 else 0.0
            score = item["roi"] + bonus - cost
            candidate = {**item, "score": score, "bonus": bonus, "open_cost": cost,
                         "direction_count_before": count}
            if best is None or (
                candidate["score"], candidate["family_id"]
            ) > (best["score"], best["family_id"]):
                best = candidate
                best_original = item
        if best is None:
            break
        counts[best["direction"]] = counts.get(best["direction"], 0) + 1
        selected.append({
            "family_id": best["family_id"],
            "direction": best["direction"],
            "roi": best["roi"],
            "exploration_bonus": round(best["bonus"], 6),
            "open_cost": round(best["open_cost"], 6),
            "selection_score": round(best["score"], 6),
            "direction_count_before": best["direction_count_before"],
        })
        remaining = [item for item in remaining if item is not best_original]

    selected_ids = {item["family_id"] for item in selected}
    return {
        "schema": DIVERSITY_SCHEMA,
        "generated_at": _now(),
        "capacity": capacity,
        "exploration_bonus": exploration_bonus,
        "decay": decay,
        "open_cost": open_cost,
        "selected": selected,
        "directions": dict(sorted(counts.items())),
        "skipped": sorted(
            item["family_id"] for item in remaining
            if item["family_id"] not in selected_ids
        ),
        "note": "Direction bonus changes selection order only; it is not a quality score.",
    }


def write_direction_allocation(
    report: dict[str, Any], output: str | Path
) -> dict[str, Any]:
    """写入方向分配回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
