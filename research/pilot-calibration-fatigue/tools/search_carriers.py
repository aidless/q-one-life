#!/usr/bin/env python3
"""Read-only, bounded inventory of local P17 carrier candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTS = [
    "/data3/Research/CALIBRATION_MERGED",
    "/data3/Research/CALIBRATION_EFFECTS",
    "/data3/Research/CALIBRATION_UNIFIED",
    "/data3/Research/calibration_contagion",
    "/data3/Research/PAPER13_MERGED",
    "/data3/Research/finding1_rerun",
    "/data3/Research/tmlr_p21_self_eval_causal",
    "/data3/Research/MERGED_FLAGSHIPS/F1_Calibration",
    "/data3/Research/workbench/audit_calibration_contagion",
    "/data3/Research/results_20260902_115235/CALIBRATION_EFFECTS",
    "/data3/Research/results_20260902_115235/calibration_contagion",
    "<WORKSPACE_ROOT>/.research/CALIBRATION_MERGED_FULL_from_data3",
    "<WORKSPACE_ROOT>/.research/CALIBRATION_SAFE_20260910/evidence_from_backup_20260824",
    "<WORKSPACE_ROOT>/.research/CALIBRATION_SUBMISSION",
    "<WORKSPACE_ROOT>/addendum_land/CALIBRATION_MERGED",
    "<WORKSPACE_ROOT>/companion_land/CALIBRATION_MERGED",
    "<WORKSPACE_ROOT>/rebuild_blind/CALIBRATION_MERGED/src",
    "<WORKSPACE_ROOT>/Projects/agi-paper-pipeline/runs/tmlr-calibration-merged/source",
]
ARCHIVES = [
    "/data3/Research/_submission_package/arxiv_batch1_20260828/CALIBRATION_MERGED.tar.gz",
    "/data3/Research/_submission_package/arxiv_batch1_20260828/CALIBRATION_EFFECTS.tar.gz",
    "/data3/Research/_submission_package/arxiv_batch1_20260828/calibration_contagion.tar.gz",
]
LIMIT = 10 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect(data: bytes) -> dict:
    text = data.decode("utf-8-sig", errors="replace")
    models = sorted(set(re.findall(
        r'"(?:model|model_name|evaluator_model|llm_model)"\s*:\s*"([^"\n]{1,100})"', text
    )))
    features = {
        "eight_condition_signature": "C1b" in text and "C3b" in text,
        "repetition_signature": any(key in text for key in [
            "final_ECE_per_rep", "final_ece_per_rep", "per_rep", '"per_round"', '"repetitions"'
        ]),
        "finding2_signature": bool(re.search(r"self.?eval|confidence.?gat", text, re.IGNORECASE)),
        "gpt4o_text": bool(re.search(r"gpt.?4o", text, re.IGNORECASE)),
    }
    return {"models": models, "features": features}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert inspect(b'{"model":"gpt-4o","C1b":1,"C3b":2,"per_rep":[]}')["features"]["eight_condition_signature"]
        assert not inspect(b'{"model":"qwen2.5:32b"}')["features"]["gpt4o_text"]
        print("P17 carrier search signature self-test PASS; signatures are not scientific validation")
        return 0
    rows, skipped, archives = [], Counter(), set()

    def record(label: str, data: bytes) -> None:
        rows.append({"path": label, "sha256": digest(data), "bytes": len(data), **inspect(data)})

    roots = []
    for item in ROOTS:
        root = Path(item)
        roots.append({"path": item, "exists": root.is_dir()})
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name.endswith((".zip", ".tar.gz", ".tgz")):
                archives.add(path)
            if path.suffix.lower() not in {".json", ".jsonl", ".csv"}:
                continue
            if path.stat().st_size > LIMIT:
                skipped["large_plain_file"] += 1
                continue
            record(str(path), path.read_bytes())
    archives.update(Path(path) for path in ARCHIVES if Path(path).is_file())
    archive_records, errors = [], []
    for path in sorted(archives):
        if path.stat().st_size > 100 * LIMIT:
            skipped["large_archive"] += 1
            continue
        archive_records.append({"path": str(path), "sha256": digest(path.read_bytes()),
                                "bytes": path.stat().st_size})
        try:
            if path.name.endswith(".zip"):
                with zipfile.ZipFile(path) as bundle:
                    for member in bundle.infolist():
                        if Path(member.filename).suffix.lower() not in {".json", ".jsonl", ".csv"}:
                            continue
                        if member.file_size > LIMIT:
                            skipped["large_archive_member"] += 1
                            continue
                        record(f"{path}!{member.filename}", bundle.read(member))
            else:
                with tarfile.open(path) as bundle:
                    for member in bundle:
                        if not member.isfile() or Path(member.name).suffix.lower() not in {".json", ".jsonl", ".csv"}:
                            continue
                        if member.size > LIMIT:
                            skipped["large_archive_member"] += 1
                            continue
                        stream = bundle.extractfile(member)
                        if stream is not None:
                            record(f"{path}!{member.name}", stream.read(LIMIT + 1))
        except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as error:
            errors.append({"path": str(path), "error_type": type(error).__name__})
    candidates = [row for row in rows if row["features"]["eight_condition_signature"] and row["features"]["repetition_signature"]]
    payload = {
        "schema": "q-one-p17-local-carrier-search-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "roots": roots, "archive_inputs": archive_records, "skipped": dict(skipped),
        "errors": errors, "file_or_member_count": len(rows),
        "unique_content_count": len({row["sha256"] for row in rows}),
        "candidate_count": len(candidates),
        "eight_condition_candidates": candidates, "inventory": rows,
        "scope": "Only the listed readable roots and JSON/JSONL/CSV members in listed archives; no external accounts, original Windows disks or remote storage were queried. Content signatures and model strings identify candidates only, never certify raw provenance. Archives were read without extraction or execution.",
        "decision": "Historical GPT-4o headlines remain blocked until a human-reviewed, identity-matched raw carrier is bound and recomputed. Non-GPT reruns and summary-only comparison values do not restore them.",
    }
    output = ROOT / "evidence/local-carrier-search.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: payload[key] for key in [
        "file_or_member_count", "unique_content_count", "candidate_count", "skipped", "errors"
    ]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
