"""Check whether RIDAR evidence spans point at the records their notes quote."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

QUOTE_PATTERNS = [
    re.compile(r'"([^"\n]{8,})"'),
    re.compile(r"\u201c([^\u201d\n]{8,})\u201d"),
    re.compile(r"'([^'\n]{8,})'"),
    re.compile(r"`([^`\n]{8,})`"),
]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[`*_>#]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def quoted_snippets(note: str) -> list[str]:
    snippets = []
    for pattern in QUOTE_PATTERNS:
        snippets.extend(pattern.findall(note))
    seen = []
    for snippet in snippets:
        normalized = normalize(snippet)
        if len(normalized) >= 8 and normalized not in seen:
            seen.append(normalized)
    return seen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    annotations = [json.loads(line) for line in
                   (args.root / "raw/ridar-hf/riv-gold/annotations.jsonl").read_text().splitlines()
                   if line.strip()]
    traces = {path.parent.name: path for path in
              (args.root / "raw/ridar-full").rglob("trace.jsonl")}
    cache: dict[str, list[str]] = {}
    records_by_trace: dict[str, int] = {}

    spans = []
    for annotation in annotations:
        identifier = annotation["id"]
        path = traces[identifier]
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        records_by_trace[identifier] = len(records)
        cache[identifier] = [normalize(record_text(record)) for record in records]
        for category, behavior in (annotation.get("behaviors") or {}).items():
            for act in behavior.get("acts") or []:
                for evidence in act.get("evidence") or []:
                    spans.append({
                        "trajectory": identifier, "category": category,
                        "start": evidence.get("start"), "end": evidence.get("end"),
                        "note": evidence.get("note") or "",
                    })

    def matched_at(span: dict[str, Any], offset: int) -> bool | None:
        snippets = quoted_snippets(span["note"])
        if not snippets:
            return None
        start = span["start"] + offset
        end = span["end"] + offset
        if start < 1 or end > records_by_trace[span["trajectory"]]:
            return False
        window = " ".join(cache[span["trajectory"]][start - 1:end])
        return any(snippet in window for snippet in snippets)

    offsets = [-2, -1, 0, 1, 2]
    offset_stats = {}
    for offset in offsets:
        results = [matched_at(span, offset) for span in spans]
        judged = [value for value in results if value is not None]
        offset_stats[str(offset)] = {
            "judged": len(judged),
            "matched": sum(judged),
            "rate": round(sum(judged) / len(judged), 4) if judged else None,
        }

    quoted = [span for span in spans if quoted_snippets(span["note"])]
    unquoted = len(spans) - len(quoted)
    start_types = Counter()
    for span in spans:
        record = json.loads(traces[span["trajectory"]].read_text().splitlines()[span["start"] - 1])
        start_types[record.get("type")] += 1
    widths = Counter(span["end"] - span["start"] + 1 for span in spans)
    category_stats: dict[str, dict[str, int]] = {}
    for span in quoted:
        entry = category_stats.setdefault(span["category"], {"quoted": 0, "matched": 0})
        entry["quoted"] += 1
        entry["matched"] += int(bool(matched_at(span, 0)))

    report = {
        "schema": "qone-ridar-span-alignment-v1",
        "spans": len(spans),
        "trajectories": len(records_by_trace),
        "quoted_spans": len(quoted),
        "unquoted_spans": unquoted,
        "span_width_distribution": {
            str(width): count for width, count in sorted(widths.items())[:10]
        },
        "single_line_share": round(widths[1] / len(spans), 4),
        "start_record_type": dict(start_types),
        "quote_match_at_offset": offset_stats,
        "quote_match_at_span": {
            "judged": offset_stats["0"]["judged"],
            "matched": offset_stats["0"]["matched"],
            "rate": offset_stats["0"]["rate"],
        },
        "by_category": {
            name: {**values, "rate": round(values["matched"] / values["quoted"], 4) if values["quoted"] else None}
            for name, values in sorted(category_stats.items())
        },
        "claim_limit": (
            "Quote containment checks only literal text reuse between note and record; "
            "a miss does not prove the span is wrong, and a hit does not prove the act is real."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "audit.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1)[:4000])
    return 0


def matched_at(span: dict[str, Any], offset: int, records: list[dict[str, Any]] | None = None) -> bool | None:
    """Public wrapper used by the miss inspector; requires records when called externally."""
    if records is None:
        raise ValueError("records required for standalone matched_at")
    snippets = quoted_snippets(span["note"])
    if not snippets:
        return None
    start = span["start"] + offset
    end = span["end"] + offset
    if start < 1 or end > len(records):
        return False
    window = " ".join(normalize(record_text(record)) for record in records[start - 1:end])
    return any(snippet in window for snippet in snippets)


if __name__ == "__main__":
    raise SystemExit(main())
