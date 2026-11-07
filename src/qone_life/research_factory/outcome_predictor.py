"""结果预测筛选：用预测器给候选实验排序，低置信度才真跑。

预测器由调用方注入；本模块不训练模型，也不把缺失预测当成 0 分。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCREEN_SCHEMA = "q-one-outcome-screen-v1"


class PredictorError(RuntimeError):
    """筛选输入不合法时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def screen_plans(
    plans: list[dict[str, Any]],
    predictor: Callable[[dict[str, Any]], dict[str, Any] | None],
    *,
    metric: str = "score",
    top_k: int = 2,
    confidence_threshold: float = 0.6,
    higher_is_better: bool = True,
) -> dict[str, Any]:
    """按预测指标排序；选中项中低置信度的进入 must_run。"""
    if not plans:
        raise PredictorError("plans is empty")
    if top_k < 1:
        raise PredictorError("top_k must be at least 1")
    if not callable(predictor):
        raise PredictorError("predictor must be callable")
    if not 0 <= confidence_threshold <= 1:
        raise PredictorError("confidence_threshold must be in [0,1]")

    evaluated: list[dict[str, Any]] = []
    unpredicted = 0
    for plan in plans:
        plan_id = str(plan.get("plan_id") or "").strip()
        if not plan_id:
            raise PredictorError("every plan needs a plan_id")
        prediction = predictor(plan)
        if not isinstance(prediction, dict):
            unpredicted += 1
            evaluated.append({
                "plan_id": plan_id,
                "predicted": None,
                "confidence": None,
                "state": "unpredicted",
            })
            continue
        value = (prediction.get("predicted") or {}).get(metric)
        confidence = prediction.get("confidence")
        if not isinstance(value, (int, float)) or not isinstance(
            confidence, (int, float)
        ):
            unpredicted += 1
            evaluated.append({
                "plan_id": plan_id,
                "predicted": None,
                "confidence": None,
                "state": "unpredicted",
            })
            continue
        if not 0 <= float(confidence) <= 1:
            raise PredictorError(f"confidence out of range for {plan_id}")
        evaluated.append({
            "plan_id": plan_id,
            "predicted": {metric: float(value)},
            "confidence": float(confidence),
            "state": "predicted",
        })

    def sort_key(item: dict[str, Any]) -> tuple:
        value = item["predicted"][metric] if item["predicted"] else None
        if value is None:
            return (1, 0.0, item["plan_id"])
        return (0, -value if higher_is_better else value, item["plan_id"])

    ranked = sorted(evaluated, key=sort_key)
    selected = ranked[:top_k]
    must_run = [
        item["plan_id"] for item in selected
        if item["state"] == "unpredicted"
        or item["confidence"] < confidence_threshold
    ]
    trusted = [
        item["plan_id"] for item in selected
        if item["plan_id"] not in must_run
    ]
    return {
        "schema": SCREEN_SCHEMA,
        "generated_at": _now(),
        "metric": metric,
        "top_k": top_k,
        "confidence_threshold": confidence_threshold,
        "ranked": ranked,
        "selected": [item["plan_id"] for item in selected],
        "must_run": must_run,
        "trusted_prediction": trusted,
        "unpredicted": unpredicted,
        "note": (
            "unpredicted is not zero: it always enters must_run. "
            "trusted_prediction still needs a recorded run before a claim."
        ),
    }


def write_screen_report(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """写入筛选回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
