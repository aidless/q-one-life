"""Inspect quote-miss spans to distinguish cross-record, paraphrase, and truncation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import ridar_span_alignment as base


def record_text(record: dict[str, Any]) -> str:
    parts = []
    content = record.get("content")
    if isinstance(content, str):
        parts.append(content)
    payload = record.get("input")
    if isinstance(payload, str):
        parts.append(payload)
    elif isinstance(payload, (dict, list)):
        parts.append(json.dumps(payload, ensure_ascii=False))
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()
    annotations = [json.loads(line) for line in
                   (args.root / "raw/ridar-hf/riv-gold/annotations.jsonl").read_text().splitlines()
                   if line.strip()]
    traces = {path.parent.name: path for path in
              (args.root / "raw/ridar-full").rglob("trace.jsonl")}

    spans = []
    for annotation in annotations:
        identifier = annotation["id"]
        records = [json.loads(line) for line in traces[identifier].read_text().splitlines() if line.strip()]
        for category, behavior in (annotation.get("behaviors") or {}).items():
            for act in behavior.get("acts") or []:
                for evidence in act.get("evidence") or []:
                    spans.append({
                        "trajectory": identifier, "category": category,
                        "start": evidence.get("start"), "end": evidence.get("end"),
                        "note": evidence.get("note") or "",
                        "records": records,
                    })

    quoted = [span for span in spans if base.quoted_snippets(span["note"])]
    misses = []
    for span in quoted:
        if base.matched_at(span, 0, span["records"]):
            continue
        snippets = base.quoted_snippets(span["note"])
        window = " ".join(base.normalize(record_text(record)) for record in span["records"]
                          [span["start"] - 1:span["end"]])
        nearest = None
        for offset in range(-5, 6):
            if span["start"] + offset >= 1 and span["start"] + offset <= len(span["records"]):
                text = base.normalize(record_text(span["records"][span["start"] + offset - 1]))
                hit = sum(snippet in text for snippet in snippets)
                if hit and nearest is None:
                    nearest = {"offset": offset, "hit": hit}
        misses.append({**span, "snippets": snippets, "window": window[:1200], "nearest": nearest})
        if len(misses) >= args.limit:
            break

    reason_counts = Counter()
    for item in misses:
        if item["nearest"] is None:
            reason_counts["no_record_quote"] += 1
        elif abs(item["nearest"]["offset"]) <= 1:
            reason_counts["adjacent_record"] += 1
        else:
            reason_counts["distant_or_partial"] += 1
    report = {
        "schema": "qone-ridar-span-miss-inspect-v1",
        "inspected": len(misses),
        "reason_counts": dict(reason_counts),
        "examples": [
            {
                "trajectory": item["trajectory"], "category": item["category"],
                "start": item["start"], "end": item["end"], "nearest": item["nearest"],
                "note": item["note"][:300], "window": item["window"][:500],
            }
            for item in misses
        ],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inspect.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1)[:3500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
