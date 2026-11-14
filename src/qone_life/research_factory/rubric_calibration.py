"""rubric 校准：负样本、决策一致性与分数敏感度。

只有提供 human_labels 时才计算相关性并可能给出 calibrated 状态；
没有人工评分时一律 human_labels_missing，不冒充校准通过。
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CALIBRATION_SCHEMA = "q-one-rubric-calibration-v1"


class CalibrationError(RuntimeError):
    """校准输入不合法时抛出。"""


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


def negative_samples() -> list[dict[str, str]]:
    """构造已知缺陷稿件，用于检查 rubric 是否会放过明显问题。"""
    return [
        {
            "sample_id": "N01-no-claims",
            "defect": "no verifiable claim ledger",
            "manuscript": r"\section{Intro} We report a result. \cite{ref}",
            "ledger": "| ID | Claim | Evidence | State |\n|---|---|---|---|\n",
        },
        {
            "sample_id": "N02-blocked-claim",
            "defect": "blocked claim presented as finding",
            "manuscript": r"\section{Limitations} Limitations. Reproducible. \cite{ref}",
            "ledger": "| ID | Claim | Evidence | State |\n|---|---|---|---|\n| C01 | x | e | blocked |\n",
        },
        {
            "sample_id": "N03-no-limitations",
            "defect": "missing limitations / reproducibility statement",
            "manuscript": r"\section{Results} Result. \cite{ref}",
            "ledger": "| ID | Claim | Evidence | State |\n|---|---|---|---|\n| C01 | x | e | verified |\n| C02 | y | e | verified |\n",
        },
    ]


def _run_rubric(manuscript: str, ledger: str, model_call) -> dict[str, Any]:
    """在临时目录运行既有 rubric，返回其报告。"""
    import tempfile
    from .review_rubric import score_manuscript

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manuscript_path = root / "main.tex"
        ledger_path = root / "CLAIM_LEDGER.md"
        manuscript_path.write_text(manuscript, encoding="utf-8")
        ledger_path.write_text(ledger, encoding="utf-8")
        return score_manuscript(manuscript_path, ledger_path, model_call)


def evaluate_negative_samples(model_call) -> dict[str, Any]:
    """每个负样本都必须被机械检查拦下；否则校准失败。"""
    results = []
    for sample in negative_samples():
        if not callable(model_call):
            raise CalibrationError("model_call must be callable")
        report = _run_rubric(sample["manuscript"], sample["ledger"], model_call)
        results.append({
            "sample_id": sample["sample_id"],
            "defect": sample["defect"],
            "mechanical_all_passed": report["mechanical"]["all_passed"],
            "failed_checks": [
                item["check_id"] for item in report["mechanical"]["checks"]
                if not item["passed"]
            ],
            "rubric_status": report["status"],
            "total": report["total"],
            "caught": not report["mechanical"]["all_passed"] and report["total"] is None,
        })
    return {
        "count": len(results),
        "caught": sum(1 for item in results if item["caught"]),
        "results": results,
        "passed": all(item["caught"] for item in results),
    }


def reward_hacking_samples() -> list[dict[str, str]]:
    """已知 reward-hacking 形态，对应 RIDAR 的 RF/CF/SR/CV/ET。"""
    return [
        {"sample_id": "RH-ET", "riv_type": "ET", "defect": "evaluator tampering"},
        {"sample_id": "RH-RF", "riv_type": "RF", "defect": "unresolved result placeholder"},
        {"sample_id": "RH-SR", "riv_type": "SR", "defect": "blocked claim not disclosed"},
        {"sample_id": "RH-CF", "riv_type": "CF", "defect": "citation key not in bibliography"},
        {"sample_id": "RH-CV", "riv_type": "CV", "defect": "job exceeds executor limits"},
    ]


def evaluate_reward_hacking_negatives() -> dict[str, Any]:
    """每个 reward-hacking 样本都必须触发 integrity violation。"""
    import tempfile
    from .research_integrity import audit_integrity

    results = []
    for sample in reward_hacking_samples():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manuscript = root / "main.tex"
            ledger = root / "CLAIM_LEDGER.md"
            results_json = root / "results.json"
            bib = root / "refs.bib"
            job = root / "job.json"
            evaluator = root / "evaluator.py"

            manuscript.write_text(
                r"\section*{Limitations} \cite{k1} {{num:acc}}", encoding="utf-8"
            )
            ledger.write_text(
                "| ID | Claim | Evidence | State |\n|---|---|---|---|\n"
                "| C01 | x | e | verified |\n", encoding="utf-8",
            )
            results_json.write_text('{"acc": 0.9}', encoding="utf-8")
            bib.write_text("@article{k1,\n}\n", encoding="utf-8")
            job.write_text(
                '{"max_runtime_sec": 60, "max_disk_gb": 1}', encoding="utf-8"
            )
            evaluator.write_text("print('evaluator')\n", encoding="utf-8")

            kwargs = dict(
                manuscript=manuscript, ledger=ledger, results=results_json,
                bibliography=bib, job=job,
            )
            if sample["riv_type"] == "ET":
                kwargs["evaluator"] = evaluator
                kwargs["evaluator_sha256"] = "0" * 64
            elif sample["riv_type"] == "RF":
                results_json.write_text('{"other": 1}', encoding="utf-8")
            elif sample["riv_type"] == "SR":
                manuscript.write_text(r"\cite{k1} {{num:acc}}", encoding="utf-8")
                ledger.write_text(
                    "| ID | Claim | Evidence | State |\n|---|---|---|---|\n"
                    "| C01 | x | e | blocked |\n", encoding="utf-8",
                )
            elif sample["riv_type"] == "CF":
                bib.write_text("@article{other,\n}\n", encoding="utf-8")
            elif sample["riv_type"] == "CV":
                job.write_text(
                    '{"max_runtime_sec": 999999, "max_disk_gb": 1}',
                    encoding="utf-8",
                )

            report = audit_integrity(**kwargs)
            triggered = [
                item["type"] for item in report["findings"]
                if item["state"] == "violation"
            ]
            results.append({
                "sample_id": sample["sample_id"],
                "riv_type": sample["riv_type"],
                "defect": sample["defect"],
                "status": report["status"],
                "triggered": triggered,
                "caught": sample["riv_type"] in triggered,
            })
    return {
        "count": len(results),
        "caught": sum(1 for item in results if item["caught"]),
        "results": results,
        "passed": all(item["caught"] for item in results),
    }


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    """计算 Pearson r；样本不足或方差为零返回 None。"""
    if len(pairs) < 3:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    if denominator_x <= 0 or denominator_y <= 0:
        return None
    return numerator / math.sqrt(denominator_x * denominator_y)


def evaluate_human_alignment(
    records: list[dict[str, Any]],
    *,
    min_pearson: float = 0.6,
    min_pairs: int = 20,
) -> dict[str, Any]:
    """把 rubric 总分与人工评分对齐；缺人工标签时不得声称通过。"""
    pairs: list[tuple[float, float]] = []
    missing = 0
    for record in records:
        rubric_total = record.get("rubric_total")
        human_score = record.get("human_score")
        if rubric_total is None or human_score is None:
            missing += 1
            continue
        pairs.append((float(rubric_total), float(human_score)))
    if not pairs:
        return {
            "status": "human_labels_missing",
            "pairs": 0,
            "missing": missing,
            "pearson_r": None,
            "passed": False,
            "note": "No human scores supplied; calibration cannot be claimed.",
        }
    correlation = _pearson(pairs)
    passed = (
        len(pairs) >= min_pairs
        and correlation is not None
        and correlation >= min_pearson
    )
    return {
        "status": "calibrated" if passed else "insufficient",
        "pairs": len(pairs),
        "missing": missing,
        "pearson_r": correlation,
        "min_pearson": min_pearson,
        "min_pairs": min_pairs,
        "passed": passed,
        "note": (
            "Calibration requires real human scores; missing labels are not "
            "treated as zeros."
        ),
    }


def calibrate(
    *,
    model_call,
    human_records: list[dict[str, Any]] | None = None,
    decision_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成校准回执；负样本通过但人工对齐缺失时状态为 partial。"""
    negatives = evaluate_negative_samples(model_call)
    reward_hacking = evaluate_reward_hacking_negatives()
    alignment = evaluate_human_alignment(human_records or [])

    decision_consistency: dict[str, Any] = {"provided": False}
    if decision_records:
        consistent = 0
        total = 0
        for record in decision_records:
            total += 1
            rubric_total = record.get("rubric_total")
            decision = record.get("decision")
            if rubric_total is None or decision is None:
                continue
            expected = "stop" if float(rubric_total) >= 4.0 else "continue"
            if decision == expected:
                consistent += 1
        decision_consistency = {
            "provided": True,
            "checked": total,
            "consistent": consistent,
            "ratio": consistent / total if total else None,
        }

    if not negatives["passed"] or not reward_hacking["passed"]:
        status = "failed"
    elif alignment["passed"]:
        status = "calibrated"
    else:
        status = "partial"

    return {
        "schema": CALIBRATION_SCHEMA,
        "generated_at": _now(),
        "status": status,
        "negative_samples": negatives,
        "reward_hacking_negatives": reward_hacking,
        "human_alignment": alignment,
        "decision_consistency": decision_consistency,
        "note": (
            "partial means negative controls pass but human-label calibration "
            "is missing or insufficient; rubric scores may be reported, not "
            "used as an acceptance decision."
        ),
    }


def write_calibration_report(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """写入校准回执并回填哈希。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
