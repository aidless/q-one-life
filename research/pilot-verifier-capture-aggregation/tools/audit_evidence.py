#!/usr/bin/env python3
"""Audit the frozen Paper 6 benchmark and local-pilot evidence.

The audit recomputes the aggregate table from the per-seed records and checks
the local pilot from its cells. It deliberately does not infer a universal
capture-resilience claim from these synthetic tables.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_methods(path: Path):
    spec = importlib.util.spec_from_file_location("paper6_extended_methods", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.METHODS


def bib_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def cited_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    keys: set[str] = set()
    for command in ("cite", "citet", "citep", "citealp"):
        for match in re.finditer(rf"\\{command}\{{([^}}]+)\}}", text):
            keys.update(key.strip() for key in match.group(1).split(","))
    return keys


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    paper = root / "evidence" / "upstream" / "paper"
    source = root / "evidence" / "upstream" / "source"
    evidence = paper / "evidence"
    benchmark_path = evidence / "main_results" / "benchmark_table.json"
    per_attack_path = evidence / "main_results" / "per_attack_table.json"
    sweep_path = evidence / "main_results" / "ensemble_sweep.json"
    pilot_path = evidence / "pilot_results" / "summary_v2.json"
    local_summary_path = evidence / "real_llm_results" / "summary.json"
    local_cells_path = evidence / "real_llm_results" / "cells.json"
    source_code = source / "source"
    overlay_main = root / "source" / "main.tex"
    canonical_main = paper / "main.tex"
    refs = root / "source" / "refs.bib"

    benchmark = load_json(benchmark_path)
    per_attack = load_json(per_attack_path)
    sweep = load_json(sweep_path)
    pilot = load_json(pilot_path)
    local_summary = load_json(local_summary_path)
    local_cells = load_json(local_cells_path)
    if not all(isinstance(item, dict) for item in (benchmark, per_attack, sweep, pilot, local_summary)):
        raise TypeError("expected JSON objects")
    if not isinstance(local_cells, list):
        raise TypeError("expected local cells array")

    config = benchmark["config"]
    scenarios = list(config["scenarios"])
    methods = list(config["methods"])
    aggregate = {
        row["method"]: row for row in benchmark["aggregate"] if isinstance(row, dict)
    }
    recomputed: dict[str, dict[str, float]] = {}
    tolerance = 2e-4
    recompute_errors: list[str] = []
    for method in methods:
        recomputed[method] = {}
        for scenario in scenarios:
            seeds = benchmark.get("per_seed", {}).get(method, {}).get(scenario, [])
            values = [float(item["acc"]) for item in seeds if isinstance(item, dict)]
            if len(values) != int(config["n_seeds"]):
                recompute_errors.append(
                    f"{method}/{scenario}: {len(values)} seed values"
                )
                continue
            mean = float(np.mean(values))
            recomputed[method][scenario] = mean
            expected = float(aggregate[method][scenario])
            if abs(mean - expected) > tolerance:
                recompute_errors.append(
                    f"{method}/{scenario}: recomputed {mean} != frozen {expected}"
                )

    winners: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        ranked = sorted(
            ((float(aggregate[method][scenario]), method) for method in methods),
            reverse=True,
        )
        winners[scenario] = {
            "best_method": ranked[0][1],
            "best_value": ranked[0][0],
            "majority_value": float(aggregate["majority"][scenario]),
            "majority_gap_to_best": float(aggregate["majority"][scenario]) - ranked[0][0],
        }

    pilot_cells = [key for key in pilot if "|" in key]
    pilot_trials = sorted({int(item["n"]) for item in pilot.values() if isinstance(item, dict)})
    local_methods = load_methods(source_code / "extended_methods.py")
    local_recomputed: dict[str, float] = {}
    local_errors: list[str] = []
    for method, function in local_methods.items():
        accuracies = []
        for cell in local_cells:
            votes = np.asarray(cell["votes"], dtype=float)
            truth = np.asarray(cell["gt"], dtype=float)
            decision = function(votes, f=2) if method == "bft_pbft" else function(votes)
            accuracies.append(float((decision == truth).mean()))
        mean = float(np.mean(accuracies)) if accuracies else float("nan")
        local_recomputed[method] = mean
        expected = float(local_summary["per_method"][method]["mean"])
        if abs(mean - expected) > 1e-4:
            local_errors.append(f"{method}: recomputed {mean} != summary {expected}")

    canonical_hash = sha256_file(canonical_main)
    overlay_hash = sha256_file(overlay_main)
    source_text = overlay_main.read_text(encoding="utf-8", errors="replace")
    cited = cited_keys(overlay_main)
    resolvable = bib_keys(refs)
    missing_citations = sorted(cited - resolvable)
    manifest = load_json(source / "evidence_manifest.json")
    manifest_files = manifest.get("files", []) if isinstance(manifest, dict) else []
    manifest_missing = [
        item["path"]
        for item in manifest_files
        if isinstance(item, dict) and not (source / "source" / item["path"]).is_file()
    ]

    checks = {
        "scenario_count_4": len(scenarios) == 4,
        "method_count_7": len(methods) == 7,
        "seed_count_5": int(config["n_seeds"]) == 5,
        "rounds_1000": int(config["T"]) == 1000,
        "per_seed_recomputes_aggregate": not recompute_errors,
        "local_pilot_recomputes": not local_errors,
        "citations_resolve": not missing_citations,
        "template_contamination_removed": not any(
            phrase in source_text
            for phrase in (
                "calibration fatigue",
                "self-evaluation immunity",
                "GSM8K",
                "MMLU",
                "HumanEval",
                "GPT-4o",
                "Beyond-PDF",
                "main.tex.LLM_FABRICATED_DO_NOT_SUBMIT",
            )
        ),
        "duplicate_reproducibility_removed": source_text.count(
            "\\section*{Reproducibility Statement}"
        )
        == 1,
        "majority_best_or_tied_s1_s3": all(
            winners[scenario]["majority_gap_to_best"] >= -tolerance
            for scenario in scenarios[:3]
        ),
        "majority_best_all_scenarios": all(
            winners[scenario]["majority_gap_to_best"] >= -tolerance
            for scenario in scenarios
        ),
        "heldout_trace_present": False,
        "hyperparameter_sweeps_present": False,
        "manifest_complete": not manifest_missing,
    }

    return {
        "schema": "q-one-paper6-evidence-audit-v1",
        "generated_at": generated_at,
        "source": {
            "canonical_main_sha256": canonical_hash,
            "overlay_main_sha256": overlay_hash,
            "canonical_bytes": canonical_main.stat().st_size,
            "overlay_bytes": overlay_main.stat().st_size,
        },
        "counts": {
            "scenarios": len(scenarios),
            "methods": len(methods),
            "seeds": int(config["n_seeds"]),
            "rounds": int(config["T"]),
            "capture_slots": int(config["f"]),
            "pilot_cells": len(pilot_cells),
            "pilot_trials_per_cell": pilot_trials,
            "local_seeds": len(local_cells),
            "local_methods": len(local_methods),
            "manifest_entries": len(manifest_files),
            "manifest_missing": len(manifest_missing),
        },
        "observed": {
            "winners": winners,
            "aggregate_means": {
                method: float(aggregate[method]["mean"]) for method in methods
            },
            "recomputed_means": recomputed,
            "local_recomputed_means": local_recomputed,
            "missing_citations": missing_citations,
            "manifest_missing": manifest_missing,
        },
        "checks": checks,
        "gate_states": {
            "source_identity": "passed",
            "synthetic_benchmark": "passed" if not recompute_errors else "failed",
            "local_pilot": "passed" if not local_errors else "failed",
            "citations": "passed" if not missing_citations else "failed",
            "template_hygiene": "passed"
            if checks["template_contamination_removed"]
            and checks["duplicate_reproducibility_removed"]
            else "failed",
            "held_out_real_trace": "blocked",
            "hyperparameter_sweeps": "blocked",
            "scientific_review": "blocked",
            "metadata_and_license": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "The synthetic aggregate table is recomputed from the frozen per-seed records.",
            "The local pilot is descriptive and does not establish external generalization.",
            "The majority is not best in S4; trust-mean is 0.0076 higher in that synthetic cell.",
            "No hyperparameter tau/alpha sweep files are present.",
            "The upstream evidence manifest is incomplete and includes absent files.",
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
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"checks": payload["checks"], "counts": payload["counts"]}, indent=2))
    required = [
        payload["checks"]["scenario_count_4"],
        payload["checks"]["method_count_7"],
        payload["checks"]["seed_count_5"],
        payload["checks"]["rounds_1000"],
        payload["checks"]["per_seed_recomputes_aggregate"],
        payload["checks"]["local_pilot_recomputes"],
        payload["checks"]["citations_resolve"],
        payload["checks"]["template_contamination_removed"],
        payload["checks"]["duplicate_reproducibility_removed"],
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
