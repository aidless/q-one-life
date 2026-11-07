"""把对抗评审的边界异议映射到复算回执的明确字段。

closed 表示该异议的替代解释被记录字段排除；它不表示科学结论已定。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "q-one-rebuttal-closure-v1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get(payload: Any, dotted: str) -> Any:
    current = payload
    for part in dotted.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted)
    return current


def _check(payload: Any, field: str, expected: Any, note: str) -> dict[str, Any]:
    try:
        actual = _get(payload, field)
    except (KeyError, IndexError, ValueError):
        return {"field": field, "expected": expected, "actual": None,
                "passed": False, "note": note}
    return {"field": field, "expected": expected, "actual": actual,
            "passed": actual == expected, "note": note}


CLOSURES = {
    "C05": {
        "receipt": "reports/package-audit.json",
        "alternative": "mechanical_pass/blockers could be read as either pass or fail",
        "checks": [
            ("mechanical_pass", True, "explicit pass flag"),
            ("blockers", [], "explicit empty blocker list"),
        ],
    },
    "C06": {
        "receipt": "reports/native-numeric-gate.json",
        "alternative": "A1=0 could refer to a different counter",
        "checks": [
            ("checks.numbers.passed", True, "numbers gate passed"),
            ("checks.numbers.passed_checks", 250, "250/250"),
            ("checks.numbers.total_checks", 250, "250/250"),
            ("checks.reverse.passed", True, "reverse gate passed"),
            ("checks.reverse.n_unbound", 0, "0 unbound"),
            ("checks.anchor.passed", True, "anchor gate passed"),
            ("checks.anchor.verdict", "GREEN", "anchor census GREEN"),
            ("checks.anchor.anchor_missing", 0, "0 missing anchors"),
        ],
    },
    "C07": {
        "receipt": "reports/cleanroom/receipt.json",
        "alternative": "byte-identical could mean same page count only",
        "checks": [
            ("pdf.pages", 45, "45 pages"),
            ("pdf.deterministic", True, "deterministic flag"),
            ("pdf.sha256_run1", "94f1b3ab5bd879f33c9c596c1ad615e675951ddad3a485eb786e853dbb430818",
             "run1 PDF hash"),
            ("pdf.sha256_run2", "94f1b3ab5bd879f33c9c596c1ad615e675951ddad3a485eb786e853dbb430818",
             "run2 PDF hash"),
        ],
    },
    "C08": {
        "receipt": "reports/package/package-receipt.json",
        "alternative": "deterministic archive could mean same filename only",
        "checks": [
            ("source.file_count", 11, "11 source files"),
            ("archive.deterministic", True, "archive deterministic flag"),
            ("archive.sha256", "74218ff9f262a8a57383875faf229a93cbd6a0cf45a2738e17571b1e11900c75",
             "archive hash"),
            ("archive.repeat_sha256", "74218ff9f262a8a57383875faf229a93cbd6a0cf45a2738e17571b1e11900c75",
             "repeat archive hash"),
        ],
    },
    "C09": {
        "receipt": "experiments/producer-baseline-counterexample/results/reproduction.json",
        "alternative": "700 stable deletions could be a different slice",
        "checks": [
            ("byte_identical", True, "two runs byte-identical"),
            ("all_expected_signatures_met", True, "all signatures met"),
            ("condition_summary.0.producer_floor", 1.0, "perfect producer floor"),
            ("condition_summary.0.system_accuracies.A", 0.9, "A=0.9"),
            ("condition_summary.0.system_accuracies.B", 0.5, "B=0.5"),
            ("condition_summary.0.single_item_deletions_stable", 700, "700/700 stable"),
            ("condition_summary.0.gate_readable", False, "gate refuses"),
            ("condition_summary.0.paired_discordance.first_only_correct", 280, "280 A-only"),
            ("condition_summary.0.paired_discordance.second_only_correct", 0, "0 B-only"),
        ],
    },
    "C12": {
        "receipt": "reports/cloud-20261106-amd/a3_amd_run1.json",
        "alternative": "zero joint margin could be forced by the support fix",
        "checks": [
            ("gates.F2_loo_label_identity_on_joint_support.passed", True, "label identity"),
            ("gates.F2_loo_label_identity_on_joint_support.mismatches", 0, "0 mismatches"),
            ("gates.F2_loo_label_identity_on_joint_support.pairs", 47200, "47,200 pairs"),
            ("gates.F3_joint_support_margin_zero.passed", True, "joint margin zero"),
            ("gates.F5_kfold_control_has_teeth.passed", True, "k-fold control positive"),
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="pilot-bench-noise-floor root")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    results = []
    for claim_id, spec in CLOSURES.items():
        receipt_path = root / spec["receipt"]
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        checks = [
            _check(payload, field, expected, note)
            for field, expected, note in spec["checks"]
        ]
        closed = all(item["passed"] for item in checks)
        results.append({
            "claim_id": claim_id,
            "status": "closed" if closed else "open",
            "alternative_explanation": spec["alternative"],
            "receipt": spec["receipt"],
            "receipt_sha256": _sha256(receipt_path),
            "checks": checks,
        })

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "root": "<WORKSPACE_ROOT>",
        "results": results,
        "closed": sum(1 for item in results if item["status"] == "closed"),
        "open": sum(1 for item in results if item["status"] == "open"),
        "note": (
            "closed means the recorded fields exclude the stated alternative "
            "reading; it does not settle the scientific claim."
        ),
    }
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "closed": report["closed"],
        "open": report["open"],
        "results": [(r["claim_id"], r["status"]) for r in results],
        "receipt": str(out),
        "receipt_sha256": _sha256(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
