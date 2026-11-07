"""type-level rubric：按论文类型检查结构性要求（RubricAtlas 式）。

只做确定性文本检查；不评价论证质量，也不替代人工评分。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TYPE_RUBRIC_SCHEMA = "q-one-type-rubric-v1"

# 每种类型只列"缺了就不完整"的结构要求；检查用正则，命中即通过。
TYPE_RUBRICS: dict[str, dict[str, Any]] = {
    "empirical_ml": {
        "label": "Empirical ML",
        "checks": {
            "dataset_named": r"\b(dataset|corpus|benchmark)\b",
            "baselines": r"\b(baseline|compare|comparison)\b",
            "metrics": r"\b(metric|accuracy|f1|auc|bleu|perplexity)\b",
            "seeds_or_repeats": r"\b(seed|replicate|repeat|run[s]?)\b",
            "ablation": r"\bablation\b",
            "limitations": r"\b(limitations?|threats to validity)\b",
        },
    },
    "benchmark": {
        "label": "Benchmark",
        "checks": {
            "task_definition": r"\b(task|suite|benchmark)\b",
            "splits": r"\b(split|train|dev|test|held.?out)\b",
            "baselines": r"\b(baseline|reference)\b",
            "metrics": r"\b(metric|score|accuracy|pass@)\b",
            "leakage_check": r"\b(leak|contaminat|overlap)\b",
            "limitations": r"\b(limitations?|threats to validity)\b",
        },
    },
    "systems": {
        "label": "Systems",
        "checks": {
            "architecture": r"\b(architecture|design|component|pipeline)\b",
            "implementation": r"\b(implement|prototype|artifact)\b",
            "workload": r"\b(workload|throughput|latency|cost)\b",
            "baseline_comparison": r"\b(baseline|compare|comparison)\b",
            "reproducibility": r"\b(reproduc\w*|artifact|code availability)\b",
            "limitations": r"\b(limitations?|threats to validity)\b",
        },
    },
    "theory": {
        "label": "Theory",
        "checks": {
            "theorem": r"\b(theorem|lemma|proposition|corollary)\b",
            "proof": r"\b(proof|prove|derivation)\b",
            "assumptions": r"\b(assumption|condition|hypothesis)\b",
            "related_work": r"\\cite[a-z]*\{",
            "limitations": r"\b(limitations?|scope)\b",
        },
    },
    "audit": {
        "label": "Audit / Measurement",
        "checks": {
            "claim_ledger": r"\b(claim|ledger|receipt)\b",
            "evidence_binding": r"\b(evidence|sha.?256|hash|receipt)\b",
            "reproduction": r"\b(reproduc\w*|rerun|re-run|recompute)\b",
            "baselines": r"\b(baseline|reference)\b",
            "limitations": r"\b(limitations?|threats to validity)\b",
            "citations": r"\\cite[a-z]*\{",
        },
    },
    "survey": {
        "label": "Survey",
        "checks": {
            "scope": r"\b(scope|coverage|inclusion|exclusion)\b",
            "taxonomy": r"\b(taxonomy|categor|axis|dimension)\b",
            "comparison": r"\b(compare|comparison|contrast)\b",
            "citations": r"\\cite[a-z]*\{",
            "limitations": r"\b(limitations?|threats to validity)\b",
        },
    },
}


class TypeRubricError(RuntimeError):
    """type-level rubric 输入不合法时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def infer_paper_type(manuscript: str) -> str:
    """按关键词命中数推断类型；平局按固定顺序。"""
    if not manuscript.strip():
        raise TypeRubricError("manuscript is empty")
    scores: dict[str, int] = {}
    for name, spec in TYPE_RUBRICS.items():
        hits = sum(
            1 for pattern in spec["checks"].values()
            if re.search(pattern, manuscript, re.I)
        )
        scores[name] = hits
    best = max(scores.values())
    for name in TYPE_RUBRICS:
        if scores[name] == best:
            return name
    return "empirical_ml"


def evaluate_type_rubric(
    manuscript: str | Path,
    *,
    paper_type: str | None = None,
) -> dict[str, Any]:
    """检查指定类型（或推断类型）的结构要求。"""
    path = Path(manuscript).expanduser().resolve()
    if not path.is_file():
        raise TypeRubricError(f"manuscript is missing: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise TypeRubricError("manuscript is empty")

    resolved_type = paper_type or infer_paper_type(text)
    if resolved_type not in TYPE_RUBRICS:
        raise TypeRubricError(f"unknown paper type: {resolved_type}")

    spec = TYPE_RUBRICS[resolved_type]
    checks = []
    for check_id, pattern in spec["checks"].items():
        matched = bool(re.search(pattern, text, re.I))
        checks.append({
            "check_id": check_id,
            "passed": matched,
            "pattern": pattern,
        })
    passed = sum(1 for item in checks if item["passed"])
    return {
        "schema": TYPE_RUBRIC_SCHEMA,
        "generated_at": _now(),
        "manuscript_path": str(path),
        "manuscript_sha256": _sha256(path.read_bytes()),
        "paper_type": resolved_type,
        "paper_type_label": spec["label"],
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "ratio": round(passed / len(checks), 4) if checks else 0.0,
        "status": "passed" if passed == len(checks) else "incomplete",
        "note": "Structural completeness only; not an argument-quality score.",
    }


def write_type_rubric(report: dict[str, Any], output: str | Path) -> dict[str, Any]:
    """写入 type-level rubric 回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
