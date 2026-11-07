#!/usr/bin/env python3
"""Audit the three public datasets used by semantic-self-consistency."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED = {
    "aqua_test.jsonl": {"rows": 254, "sha256": "de41581881ef95c5588c44ddc701c77fd480839241dd422a0d181262af24520c"},
    "svamp.json": {"rows": 1000, "sha256": "5be77703a6d891ae476d7c082787ad361392aa02453b132516cdd5f4e7934e3e"},
    "strategyqa_test.json": {"rows": 687, "sha256": "6da41445f044a7abde29f987d3311757cd0c33e759ea6f37fa100917bf0a82b0"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def numeric_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "median": statistics.median(values),
        "p95": sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)],
    }


def audit_file(path: Path) -> dict[str, Any]:
    rows = []
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            rows = payload
        else:
            for key in ("data", "examples"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
    if not rows:
        raise ValueError(f"no rows in {path.name}")
    field_counts = Counter(key for row in rows for key in row)
    missing = {key: len(rows) - count for key, count in field_counts.items()}
    questions = []
    answers: list[Any] = []
    parse_failures = 0
    for row in rows:
        if path.name == "aqua_test.jsonl":
            question = row.get("question")
            answer = row.get("correct")
            options = row.get("options")
            # AQuA-RAT stores the answer as a choice letter (A-E), while
            # `options` contains the full option strings.
            if answer is not None and isinstance(options, list) and str(answer) not in {
                str(option).split(")", 1)[0].strip() for option in options
            }:
                parse_failures += 1
        elif path.name == "svamp.json":
            question = row.get("Question")
            answer = row.get("Answer")
        else:
            question = row.get("question")
            answer = row.get("answer")
        if not isinstance(question, str) or not question.strip():
            parse_failures += 1
        else:
            questions.append(len(question))
        if answer is None or (isinstance(answer, str) and not answer.strip()):
            parse_failures += 1
        else:
            answers.append(answer)
    answer_counts = Counter(str(answer) for answer in answers)
    return {
        "file": path.name,
        "rows": len(rows),
        "sha256": sha256_file(path),
        "fields": dict(sorted(field_counts.items())),
        "missing_top_level_fields": {k: v for k, v in sorted(missing.items()) if v},
        "question_char_stats": numeric_stats([float(x) for x in questions]),
        "answer_type_counts": dict(Counter(type(answer).__name__ for answer in answers)),
        "answer_value_top10": dict(answer_counts.most_common(10)),
        "answer_value_cardinality": len(answer_counts),
        "parse_failures": parse_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audits = []
    problems = []
    for name, expected in EXPECTED.items():
        path = args.data_dir / name
        if not path.is_file():
            problems.append(f"missing:{name}")
            continue
        try:
            audit = audit_file(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            problems.append(f"invalid:{name}:{type(exc).__name__}")
            continue
        if audit["rows"] != expected["rows"]:
            problems.append(f"rows:{name}:{audit['rows']}!={expected['rows']}")
        if audit["sha256"] != expected["sha256"]:
            problems.append(f"sha256:{name}")
        if audit["parse_failures"]:
            problems.append(f"parse:{name}:{audit['parse_failures']}")
        audits.append(audit)
    payload = {
        "schema": "qone-scc-dataset-audit-v1",
        "summary": {
            "files": len(audits),
            "expected_files": len(EXPECTED),
            "rows": sum(item["rows"] for item in audits),
            "problems": len(problems),
            "problem_list": problems,
            "status": "PASS" if not problems else "FAIL",
        },
        "datasets": audits,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
