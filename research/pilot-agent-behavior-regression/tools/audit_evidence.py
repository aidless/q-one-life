#!/usr/bin/env python3
"""Audit evidence completeness and claim boundaries for Paper 35."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_status(manifest: Path, base: Path) -> dict[str, Any]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    files = payload.get("files", [])
    missing = [
        item["path"]
        for item in files
        if not (base / item["path"]).is_file()
    ]
    mismatched = []
    for item in files:
        path = base / item["path"]
        if path.is_file() and sha256_file(path) != item.get("sha256"):
            mismatched.append(item["path"])
    return {
        "entries": len(files),
        "present": len(files) - len(missing),
        "missing": missing,
        "hash_mismatches": mismatched,
    }


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    upstream = root / "evidence" / "upstream"
    paper_root = upstream / "paper"
    source_root = upstream / "source"
    overlay_main = root / "source" / "main.tex"
    main_text = overlay_main.read_text(encoding="utf-8")

    scenarios = [
        json.loads(line)
        for line in (paper_root / "data" / "scenarios" / "canonical.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    category_counts = dict(sorted(Counter(row["category"] for row in scenarios).items()))
    full_manifest = json.loads(
        (paper_root / "experiments" / "full_run" / "_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    cross_rows = list(
        csv.DictReader(
            (paper_root / "evidence" / "cross_model_bds.csv")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    )
    cross_mean = sum(float(row["cross_model_bds"]) for row in cross_rows) / len(cross_rows)
    stats = json.loads(
        (paper_root / "evidence" / "full_run_stats_20260813.json").read_text(
            encoding="utf-8"
        )
    )

    cite_keys: set[str] = set()
    for pattern in (r"\\cite\{([^}]+)\}", r"\\citep\{([^}]+)\}", r"\\citet\{([^}]+)\}"):
        for match in re.finditer(pattern, main_text):
            cite_keys.update(item.strip() for item in match.group(1).split(","))
    bib_keys = set(
        re.findall(
            r"@\w+\s*\{\s*([^,]+)",
            (root / "source" / "refs.bib").read_text(encoding="utf-8"),
        )
    )

    paper_manifest = manifest_status(
        paper_root / "evidence_manifest.json", paper_root
    )
    ingest_manifest = manifest_status(
        source_root / "MANIFEST_ingest.json", source_root
    )
    full_run_raw = sorted(
        path.name
        for path in (
            paper_root / "experiments" / "full_run" / "raw"
        ).glob("*")
        if path.is_file()
    )
    multi_agent_raw = sorted(
        path.name
        for path in (
            paper_root / "experiments" / "multi_agent" / "results" / "cloud_chain_ext"
        ).glob("*.jsonl")
    )
    carrier_path = root / "evidence" / "carrier-audit.json"
    carrier = json.loads(carrier_path.read_text(encoding="utf-8")) if carrier_path.is_file() else None

    checks = {
        "scenario_count_100": len(scenarios) == 100,
        "category_counts_match": category_counts
        == {"A": 20, "L": 20, "M": 20, "R": 15, "T": 10, "X": 15},
        "manifest_declares_1200_cells": (
            full_manifest.get("scenarios_count") == 100
            and full_manifest.get("total_cells") == 1200
            and len(full_manifest.get("snapshots", [])) == 4
            and len(full_manifest.get("seeds", [])) == 3
        ),
        "full_run_raw_present": len(full_run_raw) == 12,
        "multi_agent_raw_present": len(multi_agent_raw) == 12,
        "cross_mean_recomputes": abs(cross_mean - stats["q2_overall"]["mean"]) < 5e-5,
        "citations_resolve": cite_keys == bib_keys and bool(cite_keys),
        "carrier_receipts_pass": (
            carrier is not None and carrier.get("summary", {}).get("failed") == 0
        ),
        "paper_manifest_complete": not paper_manifest["missing"]
        and not paper_manifest["hash_mismatches"],
        "ingest_manifest_complete": not ingest_manifest["missing"]
        and not ingest_manifest["hash_mismatches"],
        "duplicate_reproducibility_heading_removed": main_text.count(
            "\\section*{Reproducibility Statement}"
        )
        == 1,
        "off_topic_ethics_removed": "Calibration fatigue" not in main_text,
        "formal_consistency_claim_removed": (
            "prove that BDS is a consistent estimator" not in main_text
            and "\\label{thm:bds-bound}" not in main_text
        ),
    }

    return {
        "schema": "q-one-paper35-evidence-audit-v1",
        "generated_at": generated_at,
        "source": {
            "overlay_main_sha256": sha256_file(overlay_main),
            "upstream_main_sha256": sha256_file(paper_root / "main.tex"),
        },
        "counts": {
            "scenarios": len(scenarios),
            "category_counts": category_counts,
            "full_run_declared_cells": full_manifest.get("total_cells"),
            "full_run_raw_files": len(full_run_raw),
            "multi_agent_raw_files": len(multi_agent_raw),
            "cross_model_rows": len(cross_rows),
            "citations": len(cite_keys),
            "paper_manifest_entries": paper_manifest["entries"],
            "paper_manifest_missing": len(paper_manifest["missing"]),
            "ingest_manifest_entries": ingest_manifest["entries"],
            "ingest_manifest_missing": len(ingest_manifest["missing"]),
        },
        "observed": {
            "cross_model_mean_recomputed": cross_mean,
            "cross_model_mean_frozen": stats["q2_overall"]["mean"],
            "paper_manifest_missing": paper_manifest["missing"],
            "ingest_manifest_missing": ingest_manifest["missing"],
        },
        "checks": checks,
        "gate_states": {
            "scenario_suite": "passed" if checks["scenario_count_100"] else "failed",
            "declared_cell_manifest": "passed" if checks["manifest_declares_1200_cells"] else "failed",
            "raw_cell_recount": "blocked" if not checks["full_run_raw_present"] else "candidate",
            "carrier_recomputation": "passed" if checks["carrier_receipts_pass"] else "blocked",
            "citations": "passed" if checks["citations_resolve"] else "failed",
            "template_hygiene": (
                "passed"
                if checks["duplicate_reproducibility_heading_removed"]
                and checks["off_topic_ethics_removed"]
                and checks["formal_consistency_claim_removed"]
                else "failed"
            ),
            "scientific_review": "blocked",
            "metadata_and_license": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "A 1,200-cell manifest declaration is not a raw-cell recount.",
            "The aggregate CSV can be checked while the full-run JSONL files remain missing.",
            "Clean compilation does not establish scientific readiness.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    payload = audit(root, args.generated_at)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": payload["checks"], "counts": payload["counts"]}, indent=2))
    required = [
        payload["checks"]["scenario_count_100"],
        payload["checks"]["category_counts_match"],
        payload["checks"]["citations_resolve"],
        payload["checks"]["carrier_receipts_pass"],
        payload["checks"]["duplicate_reproducibility_heading_removed"],
        payload["checks"]["off_topic_ethics_removed"],
        payload["checks"]["formal_consistency_claim_removed"],
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
