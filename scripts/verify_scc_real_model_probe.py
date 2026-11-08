#!/usr/bin/env python3
"""Verify Semantic Self-Consistency real-model readout receipts.

Checks per-run: schema, hash integrity, row counts, parse-rate accounting,
accuracy bounds and that the claimed accuracy is *recomputable* from the raw
per-response records that ship next to the summary.

Two-direction mutation selftest: (A) tamper a stored accuracy, (B) inflate the
expected row count. Both must make the verifier red; restoring must make it green.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_NOT_EXECUTED = 3

SCHEMA_NOTE = "Accuracy here is a real open-model readout"


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower().rstrip(".")


def recompute_from_raw(raw_path: Path) -> dict[str, dict[str, float]]:
    """Re-derive accuracy per dataset from the raw response records."""
    acc: dict[str, dict[str, float]] = {}
    counts: dict[str, dict[str, int]] = {}
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        name = rec["dataset"]
        row = counts.setdefault(name, {"n": 0, "top": 0, "sc": 0, "cpw": 0, "scw": 0})
        row["n"] += 1
        gold = _norm(rec["gold"])
        row["top"] += int(_norm(rec["top_prob_answer"]) == gold)
        row["sc"] += int(_norm(rec["sc_answer"]) == gold)
        row["cpw"] += int(_norm(rec["cpw_answer"]) == gold)
        row["scw"] += int(_norm(rec["scw_answer"]) == gold)
    for name, row in counts.items():
        n = row["n"] or 1
        acc[name] = {
            "rows": row["n"],
            "accuracy_top_prob": round(row["top"] / n, 12),
            "accuracy_sc": round(row["sc"] / n, 12),
            "accuracy_cpw": round(row["cpw"] / n, 12),
            "accuracy_scw": round(row["scw"] / n, 12),
        }
    return acc


def verify_run(summary_path: Path, *, expected_rows: dict[str, int] | None = None) -> dict[str, Any]:
    problems: list[str] = []
    if not summary_path.is_file():
        return {"run": str(summary_path), "problems": ["summary_missing"], "passed": False}
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stored_hash = summary.get("canonical_sha256")
    body = {k: v for k, v in summary.items() if k != "canonical_sha256"}
    if stored_hash != canonical_sha256(body):
        problems.append("canonical_mismatch")
    if SCHEMA_NOTE not in (summary.get("note") or ""):
        problems.append("scope_note_missing")
    for key in ("model", "model_family", "prompt_mode", "k", "seed", "datasets"):
        if key not in summary:
            problems.append(f"missing_field:{key}")

    raw_path = summary_path.with_suffix(".raw.jsonl")
    if not raw_path.is_file():
        problems.append("raw_missing")
        return {"run": str(summary_path), "problems": problems, "passed": False}
    recomputed = recompute_from_raw(raw_path)
    datasets = summary.get("datasets") or {}
    if set(recomputed) != set(datasets):
        problems.append("dataset_set_mismatch")
    for name, observed in recomputed.items():
        claimed = datasets.get(name) or {}
        for key, value in observed.items():
            if key in claimed and abs(float(claimed[key]) - float(value)) > 1e-9:
                problems.append(f"recompute_mismatch:{name}:{key}")
        if not 0.0 <= float(claimed.get("accuracy_sc", 0.0)) <= 1.0:
            problems.append(f"accuracy_out_of_range:{name}")
        expected = (expected_rows or {}).get(name)
        if expected is not None and observed["rows"] != expected:
            problems.append(f"row_count:{name}")
    model = summary.get("model_family", "")
    if "NOT the paper" not in model:
        problems.append("model_scope_label_missing")
    return {
        "run": summary_path.parent.name,
        "prompt_mode": summary.get("prompt_mode"),
        "datasets": {
            name: {
                "rows": row["rows"],
                "top_prob": row["accuracy_top_prob"],
                "sc": row["accuracy_sc"],
                "cpw": row["accuracy_cpw"],
                "scw": row["accuracy_scw"],
                "parse_rate_sc": datasets.get(name, {}).get("parse_rate_sc"),
            }
            for name, row in recomputed.items()
        },
        "problems": problems,
        "passed": not problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-rows", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selftest", type=Path, default=None)
    args = parser.parse_args()

    expected_rows = {}
    for item in filter(None, (s.strip() for s in args.expected_rows.split(","))):
        name, value = item.split("=", 1)
        expected_rows[name] = int(value)

    summaries = sorted(args.root.glob("*/summary.json"))
    if not summaries:
        result = {"summary": {"gate": "NOT_EXECUTED", "runs": 0}, "runs": []}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("NOT_EXECUTED: no summary.json under", args.root)
        return EXIT_NOT_EXECUTED

    runs = [verify_run(path, expected_rows=expected_rows) for path in summaries]
    failed = [run for run in runs if not run["passed"]]
    result = {
        "summary": {
            "gate": "PASS" if not failed else "FAIL",
            "runs": len(runs),
            "problems": sum(len(run["problems"]) for run in runs),
        },
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"]))

    if args.selftest is not None:
        target = summaries[0]
        name = next(iter((json.loads(target.read_text())["datasets"])))
        original = json.loads(target.read_text())

        # Direction A: tamper one stored accuracy.
        bad = copy.deepcopy(original)
        bad["datasets"][name]["accuracy_sc"] = round(
            float(bad["datasets"][name]["accuracy_sc"]) + 0.25, 6
        )
        body = {k: v for k, v in bad.items() if k != "canonical_sha256"}
        bad["canonical_sha256"] = canonical_sha256(body)
        bad_path = target.with_name("summary.selftest-a.json")
        bad_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
        a = verify_run(bad_path, expected_rows=expected_rows)
        bad_path.unlink()

        # Direction B: inflate the expected row count.
        inflated = dict(expected_rows)
        inflated[name] = int(original["datasets"][name]["rows"]) + 1
        b = verify_run(target, expected_rows=inflated)

        restored = verify_run(target, expected_rows=expected_rows)
        selftest = {
            "summary": {
                "passed": (not a["passed"]) and (not b["passed"]) and restored["passed"],
                "direction_a_problems": len(a["problems"]),
                "direction_b_problems": len(b["problems"]),
                "restored_problems": len(restored["problems"]),
            },
            "direction_a": a["problems"],
            "direction_b": b["problems"],
        }
        args.selftest.write_text(json.dumps(selftest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(selftest["summary"]))

    return EXIT_OK if not failed else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
