#!/usr/bin/env python3
"""Re-evaluate the one frozen Paper 6 numerical carrier receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_locator(data: Any, expression: str) -> Any:
    # The shipped receipt uses a bounded subset of Python indexing:
    # aggregate[1]["S4: high-honest, strong-attack"].
    match = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]\[\"([^\"]+)\"\]", expression
    )
    if match:
        name, index, key = match.groups()
        return data[name][int(index)][key]
    current = data
    for part in expression.split("."):
        if part.endswith("]") and "[" in part:
            name, rest = part.split("[", 1)
            current = current[name]
            for index in re.findall(r"\[(\d+)\]", rest):
                current = current[int(index)]
        else:
            current = current[part]
    return current


def audit(root: Path, receipt_path: Path, generated_at: str) -> dict[str, Any]:
    receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for receipt in receipts:
        artifact_name = str(receipt["artifact"])
        artifact = root / "evidence" / "upstream" / "paper" / artifact_name
        if not artifact.is_file():
            artifact = root / "evidence" / "upstream" / "source" / artifact_name
        expected = float(receipt["value"])
        dp = int(receipt.get("dp", 3))
        value: float | None = None
        source_line: str | None = None
        value_match = False
        line_match = False
        if artifact.is_file():
            data = json.loads(artifact.read_text(encoding="utf-8"))
            value = float(resolve_locator(data, str(receipt["locator"])))
            value_match = abs(value - expected) <= 0.5 * 10**-dp + 1e-12
            line_ref = str(receipt.get("line", ""))
            if ":" in line_ref:
                source_name, line_number = line_ref.rsplit(":", 1)
                source_name = source_name.removeprefix("paper/")
                source_path = root / "evidence" / "upstream" / "paper" / source_name
                if source_path.is_file():
                    lines = source_path.read_text(encoding="utf-8").splitlines()
                    line_index = int(line_number) - 1
                    if 0 <= line_index < len(lines):
                        source_line = lines[line_index]
                        values = [float(token) for token in NUMBER_RE.findall(source_line)]
                        line_match = any(abs(item - expected) <= 0.5 * 10**-dp + 1e-12 for item in values)
        status = "PASS" if value_match and line_match else "FAIL"
        results.append(
            {
                "status": status,
                "artifact": str(artifact),
                "artifact_sha256": sha256_file(artifact) if artifact.is_file() else None,
                "locator": receipt.get("locator"),
                "expected": expected,
                "value": value,
                "value_match": value_match,
                "line": receipt.get("line"),
                "line_preview": source_line,
                "line_match": line_match,
            }
        )
    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "schema": "q-one-paper6-carrier-audit-v1",
        "generated_at": generated_at,
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "summary": {"receipts": len(results), "passed": passed, "failed": len(results) - passed},
        "receipts": results,
        "scientific_ready": False,
        "external_submission": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--receipts", default="evidence/upstream/paper/evidence/CARRIER_RECEIPTS.json")
    parser.add_argument("--output", required=True)
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
