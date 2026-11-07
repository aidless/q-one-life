"""Census hidden/test paths and split semantics across all 60 RIDAR traces."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

PATH_PATTERNS = [
    re.compile(r"(?:^|[/\\])(?:private|hidden|secret|test)(?:[/\\]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[/\\])(?:test|dev|valid|eval)[-_](?:set|split)", re.IGNORECASE),
    re.compile(r"test\.csv|answers\.csv|_test\.txt|test_labels|test\.json", re.IGNORECASE),
    re.compile(r"train_test_split|train_test_split\(|test_size|random_state", re.IGNORECASE),
    re.compile(r"\.test\b|_test\b|_test_", re.IGNORECASE),
]
READ_MARKERS = ["cat ", "head ", "tail ", "grep ", "python -c", "python3 -c", "pd.read_csv", "read_csv", "open("]
WRITE_MARKERS = ["cat >", "sed -i", "new_string", "write", "np.save", "to_csv", "json.dump"]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"`|\\u201[89c]|\"|'", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_text(record: dict[str, Any]) -> str:
    if isinstance(record.get("content"), str):
        return record["content"]
    if isinstance(record.get("input"), str):
        return record["input"]
    if isinstance(record.get("input"), dict):
        return json.dumps(record["input"], ensure_ascii=False)
    if isinstance(record.get("input"), list):
        return json.dumps(record["input"], ensure_ascii=False)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for trace_path in sorted((args.root / "raw/ridar-full").rglob("trace.jsonl")):
        identifier = trace_path.parent.name
        records = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
        texts = [normalize(extract_text(record)) for record in records]
        path_hits: dict[str, list[int]] = {}
        split_hits: dict[str, list[int]] = {}
        for index, text in enumerate(texts, start=1):
            for pattern in PATH_PATTERNS:
                for match in pattern.finditer(text):
                    path_hits.setdefault(pattern.pattern, []).append(index)
            for marker in READ_MARKERS:
                if marker in text:
                    split_hits.setdefault(f"read:{marker}", []).append(index)
            for marker in WRITE_MARKERS:
                if marker in text:
                    split_hits.setdefault(f"write:{marker}", []).append(index)
        rows.append({
            "trajectory": identifier, "records": len(records),
            "path_pattern_hits": {key: value[:args.limit] for key, value in path_hits.items()},
            "operation_hits": {key: value[:args.limit] for key, value in split_hits.items()},
            "path_pattern_counts": {key: len(value) for key, value in path_hits.items()},
            "operation_counts": {key: len(value) for key, value in split_hits.items()},
        })

    pattern_totals = Counter()
    operation_totals = Counter()
    trajectories_with_path = Counter()
    trajectories_with_split = Counter()
    for row in rows:
        for key, count in row["path_pattern_counts"].items():
            pattern_totals[key] += count
            trajectories_with_path[key] += 1
        for key, count in row["operation_counts"].items():
            operation_totals[key] += count
            trajectories_with_split[key] += 1

    report = {
        "schema": "qone-ridar-test-path-census-v1",
        "trajectories": len(rows),
        "records_total": sum(row["records"] for row in rows),
        "path_pattern_totals": dict(pattern_totals),
        "operation_totals": dict(operation_totals),
        "trajectories_with_path": dict(trajectories_with_path),
        "trajectories_with_split": dict(trajectories_with_split),
        "sample": rows[:3],
        "claim_limit": (
            "Path matching alone does not identify hidden test labels; a path may be a "
            "public directory. This census only counts lexical occurrences."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "census.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "trajectories": len(rows),
        "path_pattern_totals": dict(pattern_totals),
        "operation_totals": dict(operation_totals),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
