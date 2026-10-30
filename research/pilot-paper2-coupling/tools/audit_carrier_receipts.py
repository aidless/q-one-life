#!/usr/bin/env python3
"""Re-evaluate the frozen numerical carrier receipts for the Paper 2 overlay."""

from __future__ import annotations

import argparse
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
        root / "evidence" / "upstream" / "source" / relative,
        root / "evidence" / "upstream" / "source" / "evidence" / relative.name,
        root / "evidence" / "upstream" / "paper" / relative.name,
        root / "evidence" / relative,
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


def numeric_value(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def tolerance(dp: int) -> float:
    return 0.5 * (10 ** -dp) + 1e-12


def carrier_result(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    artifact = resolve_artifact(root, str(receipt["artifact"]))
    expected = numeric_value(receipt["value"])
    dp = int(receipt.get("dp", 3))
    if artifact is None:
        return {
            "status": "FAIL",
            "reason": "artifact_missing",
            "artifact": receipt.get("artifact"),
        }
    if expected is None:
        return {
            "status": "FAIL",
            "reason": "non_numeric_receipt",
            "artifact": str(artifact),
        }

    data = json.loads(artifact.read_text(encoding="utf-8"))
    candidates = [
        value
        for value in resolve_values(data, str(receipt["over"]))
        if numeric_value(value) is not None
    ]
    value_match = any(
        abs(float(value) - expected) <= tolerance(dp) for value in candidates
    )

    line_match = True
    line_preview = None
    line_ref = receipt.get("line")
    if line_ref:
        source_name, raw_line = str(line_ref).rsplit(":", 1)
        line_number = int(raw_line)
        if source_name == "paper/main.tex":
            source = root / "evidence" / "upstream" / "paper" / "main.tex"
        else:
            source = root / "evidence" / "upstream" / "source" / "main.tex"
        lines = source.read_text(encoding="utf-8").splitlines()
        if not 1 <= line_number <= len(lines):
            line_match = False
            line_preview = "line_out_of_range"
        else:
            line_preview = lines[line_number - 1]
            line_values = [
                float(token) for token in NUMBER_RE.findall(line_preview)
            ]
            line_match = any(
                abs(value - expected) <= tolerance(dp) for value in line_values
            )

    passed = value_match and line_match
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact": str(artifact),
        "artifact_sha256": sha256_file(artifact),
        "expression": receipt.get("over"),
        "expected": expected,
        "dp": dp,
        "candidates": candidates,
        "value_match": value_match,
        "line_match": line_match,
        "line": line_ref,
        "line_preview": line_preview,
    }


def audit(root: Path, receipt_path: Path, generated_at: str) -> dict[str, Any]:
    receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    results = [carrier_result(root, receipt) for receipt in receipts]
    passed = sum(result["status"] == "PASS" for result in results)
    failed = len(results) - passed
    artifacts = {
        result["artifact"]: result["artifact_sha256"]
        for result in results
        if result.get("artifact_sha256")
    }
    manuscript = root / "source" / "main.tex"
    upstream = root / "evidence" / "upstream" / "paper" / "main.tex"
    return {
        "schema": "q-one-paper2-carrier-audit-v1",
        "generated_at": generated_at,
        "source": {
            "manuscript": str(manuscript),
            "manuscript_sha256": sha256_file(manuscript),
            "upstream": str(upstream),
            "upstream_sha256": sha256_file(upstream),
            "receipts": str(receipt_path),
            "receipts_sha256": sha256_file(receipt_path),
        },
        "summary": {
            "receipts": len(results),
            "passed": passed,
            "failed": failed,
            "artifacts": len(artifacts),
        },
        "artifact_hashes": [
            {"path": path, "sha256": digest}
            for path, digest in sorted(artifacts.items())
        ],
        "receipts": results,
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "A PASS means the frozen artifact field and printed number are mutually consistent.",
            "A carrier receipt does not establish proof validity, held-out generalization, or independent review.",
        ],
    }


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    failures = [
        item for item in payload["receipts"] if item["status"] == "FAIL"
    ]
    lines = [
        "# Paper 2 carrier receipt audit",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Receipts: {summary['receipts']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Unique artifacts: {summary['artifacts']}",
        "",
        "## Failures",
        "",
    ]
    if not failures:
        lines.append("None.")
    else:
        for item in failures:
            lines.append(
                f"- `{item.get('artifact')}` `{item.get('expression')}`: "
                f"{item.get('reason', 'value or line mismatch')}"
            )
    lines.extend(
        [
            "",
            "A carrier match is not a proof audit, held-out validation, or publication approval.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--receipts",
        default="evidence/CARRIER_RECEIPTS.json",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown")
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    receipt_path = Path(args.receipts)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    payload = audit(root, receipt_path.resolve(), args.generated_at)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.markdown:
        report = Path(args.markdown)
        if not report.is_absolute():
            report = root / report
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
