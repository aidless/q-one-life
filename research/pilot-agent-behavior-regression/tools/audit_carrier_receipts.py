#!/usr/bin/env python3
"""Re-evaluate the frozen Paper 35 carrier receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+|\*)\]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact(root: Path, raw: str) -> Path | None:
    relative = Path(raw)
    candidates = [
        root / "evidence" / "upstream" / relative,
        root / "evidence" / "upstream" / "paper" / relative,
        root / "evidence" / "upstream" / "source" / relative,
    ]
    return next((path for path in candidates if path.is_file()), None)


def resolve_values(data: Any, expression: str) -> list[Any]:
    values = [data]
    for match in SEGMENT_RE.finditer(expression):
        key, index = match.groups()
        next_values: list[Any] = []
        for value in values:
            if key is not None:
                if isinstance(value, dict) and key in value:
                    next_values.append(value[key])
                continue
            if not isinstance(value, list):
                continue
            if index == "*":
                next_values.extend(value)
            else:
                position = int(index)
                if 0 <= position < len(value):
                    next_values.append(value[position])
        values = next_values
        if not values:
            break
    return values


def tolerance(dp: int) -> float:
    return 0.5 * (10**-dp) + 1e-12


def numeric(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_json(artifact: Path, receipt: dict[str, Any]) -> tuple[list[float], int | None]:
    data = json.loads(artifact.read_text(encoding="utf-8"))
    candidates = resolve_values(data, str(receipt["locator"]))
    values = [float(value) for value in candidates if numeric(value) is not None]
    return values, None


def evaluate_csv(artifact: Path, receipt: dict[str, Any]) -> tuple[list[float], int]:
    rows = list(csv.DictReader(artifact.read_text(encoding="utf-8").splitlines()))
    where = receipt.get("where", {})
    selected = [
        row
        for row in rows
        if all(str(row.get(key)) == str(value) for key, value in where.items())
    ]
    field = str(receipt.get("over", "")).removeprefix("rows[*].").strip()
    values = [float(row[field]) for row in selected]
    mean = sum(values) / len(values) if values else None
    return ([mean] if mean is not None else []), len(selected)


def line_matches(root: Path, line_ref: str, expected: float, dp: int) -> tuple[bool, str | None]:
    source_name, raw_line = line_ref.rsplit(":", 1)
    if source_name == "source/main.tex":
        path = root / "evidence" / "upstream" / "source" / "main.tex"
    else:
        path = root / "evidence" / "upstream" / "paper" / "main.tex"
    lines = path.read_text(encoding="utf-8").splitlines()
    line_number = int(raw_line)
    if not 1 <= line_number <= len(lines):
        return False, None
    line = lines[line_number - 1]
    values = [float(token) for token in NUMBER_RE.findall(line)]
    return any(abs(value - expected) <= tolerance(dp) for value in values), line


def audit(root: Path, receipt_path: Path, generated_at: str) -> dict[str, Any]:
    receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    results = []
    for receipt in receipts:
        artifact = resolve_artifact(root, str(receipt["artifact"]))
        expected = numeric(receipt["value"])
        dp = int(receipt.get("dp", 2))
        if artifact is None or expected is None:
            results.append(
                {
                    "status": "FAIL",
                    "reason": "artifact_or_expected_value_missing",
                    "receipt": receipt,
                }
            )
            continue
        if artifact.suffix.lower() == ".csv":
            values, selected = evaluate_csv(artifact, receipt)
        else:
            values, selected = evaluate_json(artifact, receipt)
        value_match = any(
            abs(value - expected) <= tolerance(dp) for value in values
        )
        line_match, line_preview = line_matches(
            root, str(receipt["line"]), expected, dp
        )
        expected_count = receipt.get("expect")
        count_match = expected_count is None or selected == int(expected_count)
        passed = value_match and line_match and count_match
        results.append(
            {
                "status": "PASS" if passed else "FAIL",
                "artifact": str(artifact),
                "artifact_sha256": sha256_file(artifact),
                "locator": receipt.get("locator"),
                "over": receipt.get("over"),
                "expected": expected,
                "values": values,
                "value_match": value_match,
                "line_match": line_match,
                "line_preview": line_preview,
                "selected_rows": selected,
                "expected_rows": expected_count,
                "count_match": count_match,
            }
        )
    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "schema": "q-one-paper35-carrier-audit-v1",
        "generated_at": generated_at,
        "source": {
            "receipts": str(receipt_path),
            "receipts_sha256": sha256_file(receipt_path),
            "overlay_main_sha256": sha256_file(root / "source" / "main.tex"),
            "upstream_main_sha256": sha256_file(
                root / "evidence" / "upstream" / "paper" / "main.tex"
            ),
        },
        "summary": {"receipts": len(results), "passed": passed, "failed": len(results) - passed},
        "receipts": results,
        "scientific_ready": False,
        "external_submission": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--receipts", default="evidence/upstream/paper/evidence/CARRIER_RECEIPTS.json"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown", required=True)
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    receipt_path = Path(args.receipts)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    payload = audit(root, receipt_path, args.generated_at)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    markdown = Path(args.markdown)
    if not markdown.is_absolute():
        markdown = root / markdown
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [item for item in payload["receipts"] if item["status"] != "PASS"]
    lines = [
        "# Paper 35 carrier audit",
        "",
        f"- Receipts: {payload['summary']['receipts']}",
        f"- Passed: {payload['summary']['passed']}",
        f"- Failed: {payload['summary']['failed']}",
        "",
        "## Failures",
        "",
    ]
    if failures:
        for item in failures:
            lines.append(f"- `{item.get('artifact', item.get('receipt'))}`")
    else:
        lines.append("None.")
    lines.append("")
    markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
