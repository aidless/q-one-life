"""Fetch all pinned RIDAR RIV-Gold traces with size and hash verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET = "THU-KEG/RIDAR"
REVISION = "5ca10637e5a74fc20643000b799551b0a27cd92b"
TOTAL_LIMIT = 128 * 1024 * 1024
FILE_LIMIT = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def tree_entries() -> list[dict]:
    tree = json.loads((ROOT / "raw/metadata/ridar-gold-tree.json").read_text())
    entries = tree if isinstance(tree, list) else tree.get("siblings", [])
    return [entry for entry in entries if entry["path"].endswith("/trace.jsonl")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fetch", "verify"])
    args = parser.parse_args()
    ledger_path = ROOT / "ridar-full-manifest.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {
        "schema_version": "qone-ridar-full-v1", "dataset": DATASET,
        "revision": REVISION, "files": [], "failures": [],
    }
    entries = tree_entries()
    if args.action == "verify":
        problems = []
        total = 0
        for record in ledger["files"]:
            path = ROOT / record["path"]
            if not path.is_file():
                problems.append({"path": record["path"], "problem": "missing"})
                continue
            payload = path.read_bytes()
            total += len(payload)
            if len(payload) != record["bytes"]:
                problems.append({"path": record["path"], "problem": "size"})
            if sha256(payload) != record["sha256"]:
                problems.append({"path": record["path"], "problem": "sha256"})
        expected = sum(entry.get("size") or 0 for entry in entries)
        report = {
            "action": "verify", "files": len(ledger["files"]),
            "expected_files": len(entries), "bytes": total, "expected_bytes": expected,
            "problems": problems,
            "status": "pass" if not problems and len(ledger["files"]) == len(entries)
            and total == expected else "fail",
        }
        print(json.dumps(report))
        return 0 if report["status"] == "pass" else 1

    known = {record["path"]: record for record in ledger["files"]}
    used = sum(record["bytes"] for record in ledger["files"])
    for entry in sorted(entries, key=lambda item: item["path"]):
        relative = entry["path"]
        local = f"raw/ridar-full/{relative.split('/', 2)[2]}"
        size = entry.get("size") or 0
        if size > FILE_LIMIT:
            ledger["failures"].append({"path": relative, "reason": "file limit"})
            continue
        destination = ROOT / local
        if local in known:
            payload = destination.read_bytes()
            if len(payload) != known[local]["bytes"] or sha256(payload) != known[local]["sha256"]:
                raise SystemExit(f"existing file mismatch: {local}")
            continue
        if used + size > TOTAL_LIMIT:
            ledger["failures"].append({"path": relative, "reason": "total limit"})
            continue
        url = (f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/"
               + urllib.parse.quote(relative))
        request = urllib.request.Request(url, headers={"User-Agent": "qone-public-dataset-audit"})
        started = utc_now()
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(size + 1)
        if len(payload) != size:
            ledger["failures"].append({"path": relative, "reason": f"size {len(payload)} != {size}"})
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        record = {
            "dataset": "ridar", "role": "riv_gold_trace", "path": local,
            "source_path": relative, "source_url": url, "revision": REVISION,
            "bytes": len(payload), "sha256": sha256(payload),
            "download_started_at_utc": started, "downloaded_at_utc": utc_now(),
        }
        ledger["files"].append(record)
        known[local] = record
        used += len(payload)
        ledger_path.write_text(json.dumps(ledger, indent=1) + "\n")
    ledger_path.write_text(json.dumps(ledger, indent=1) + "\n")
    print(json.dumps({"files": len(ledger["files"]), "failures": len(ledger["failures"]),
                      "bytes": used}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
