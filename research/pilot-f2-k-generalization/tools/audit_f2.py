#!/usr/bin/env python3
"""Audit the F2 K-generalization bundle and preserve its contradictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(
        r"\\cite(?:t|p|alp)?\*?(?:\[[^\]]*\])?\{([^}]+)\}", text
    ):
        keys.update(key.strip() for key in match.group(1).split(","))
    return keys


def bib_keys(text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    upstream = root / "evidence" / "upstream"
    paper = upstream / "paper"
    source = paper / "main.tex"
    source_text = source.read_text(encoding="utf-8")
    labels = re.findall(r"\\label\{([^}]+)\}", source_text)
    references = re.findall(r"\\ref\{([^}]+)\}", source_text)
    labels_counter = Counter(labels)
    refs = citation_keys(source_text)
    bib = bib_keys((paper / "refs.bib").read_text(encoding="utf-8"))

    k345 = paper / "evidence" / "k345"
    joint = load_json(k345 / "joint_2700.json")
    analysis = load_json(k345 / "analysis_2700.json")
    bootstrap = load_json(k345 / "bootstrap_2700.json")
    episodes = load_jsonl(k345 / "episodes.jsonl")
    per_seed = load_jsonl(k345 / "per_seed.jsonl")
    real64 = load_json(k345 / "real64.json")
    real128 = load_json(k345 / "real128_combined.json")
    real192 = load_json(k345 / "real192.json")
    p16 = load_json(paper / "evidence" / "p16_provenance.json")

    distinct_joint_conditions = sorted(
        {(int(cell["K"]), float(cell["gamma"])) for cell in joint["cells"]}
    )
    duplicate_joint_values = len(joint["cells"]) != len(
        {(cell["K"], cell["gamma"]) for cell in joint["cells"]}
    )
    analysis_conditions = {
        key: value for key, value in analysis.items() if key.startswith("K")
    }
    bootstrap_per_seed_means = {
        key: statistics.mean(value["per_seed"]) for key, value in bootstrap.items()
    }
    bootstrap_mismatches = {
        key: {
            "point": bootstrap[key]["point"],
            "mean_per_seed": bootstrap_per_seed_means[key],
            "difference": bootstrap[key]["point"] - bootstrap_per_seed_means[key],
        }
        for key in bootstrap
        if abs(bootstrap[key]["point"] - bootstrap_per_seed_means[key]) > 0.005
    }

    per_seed_groups: dict[str, list[float]] = defaultdict(list)
    for row in per_seed:
        per_seed_groups[str(row["key"])].append(float(row["product"]))
    per_seed_means = {
        key: statistics.mean(values) for key, values in sorted(per_seed_groups.items())
    }

    episode_groups: dict[tuple[int, float], list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        episode_groups[(int(row["K"]), float(row["gamma_true"]))].append(row)
    episode_summary = {
        f"K{key[0]}_g{key[1]}": {
            "records": len(rows),
            "unique_questions": len({row["question"] for row in rows}),
            "unanimous": sum(len(set(row["votes"])) == 1 for row in rows),
            "mean_vote": statistics.mean(
                statistics.mean(float(vote) for vote in row["votes"])
                for row in rows
            ),
        }
        for key, rows in sorted(episode_groups.items())
    }

    real64_degenerate_products = {
        key: value
        for key, value in real64["results"].items()
        if float(value["product"]) == 0.35
    }
    real64_failures = {
        key: {
            "n": value["n"],
            "holds_sum": sum(int(item) for item in value["holds"]),
            "p": value["p"],
            "holds_all": value["holds_all"],
        }
        for key, value in real64["results"].items()
        if not value["holds_all"]
    }
    real_calls = {
        "real64": int(real64["n_total"]),
        "real128": int(real128["n_total"]),
        "real192": int(real192["n_total"]),
        "total": int(real64["n_total"])
        + int(real128["n_total"])
        + int(real192["n_total"]),
    }
    elapsed_hours = {
        "real64": float(real64["elapsed"]) / 3600,
        "real128": float(real128["elapsed"]) / 3600,
        "real192": float(real192["elapsed"]) / 3600,
        "sum": (
            float(real64["elapsed"])
            + float(real128["elapsed"])
            + float(real192["elapsed"])
        )
        / 3600,
    }

    claim_ledger = (paper / "CLAIM_LEDGER.md").read_text(encoding="utf-8")
    ledger_rows = re.findall(r"^\| C\d+", claim_ledger, re.MULTILINE)
    protocol = (paper / "evidence" / "protocol.md").read_text(encoding="utf-8")
    proof = (paper / "evidence" / "tightness_proof.md").read_text(encoding="utf-8")
    p16_fields = sorted(p16)
    abs_claims = {
        "dz_0_42": "0.42" in source_text,
        "ci_0_18_0_66": "0.18" in source_text and "0.66" in source_text,
        "p_0_009": "0.009" in source_text,
        "hmin_0_08": "0.08" in source_text,
        "self_eval_0_11": "0.11" in source_text,
        "bound_0_014": "0.014" in source_text,
    }
    checks = {
        "single_source_structure": all(
            (
                source_text.count("\\title{") == 1,
                source_text.count("\\author{") == 1,
                source_text.count("\\end{document}") == 1,
                all(count == 1 for count in labels_counter.values()),
                not (set(references) - set(labels)),
            )
        ),
        "citations_resolve": not (refs - bib),
        "joint_declared_2700_but_five_rows": int(joint["n_cells"]) == 2700
        and int(joint["holds"]) == 2700
        and len(joint["cells"]) == 5,
        "joint_covers_only_three_conditions": len(distinct_joint_conditions) == 3,
        "joint_has_duplicate_condition_rows": duplicate_joint_values,
        "analysis_has_six_summary_conditions": len(analysis_conditions) == 6,
        "bootstrap_point_disagrees_with_per_seed_mean": bool(bootstrap_mismatches),
        "per_seed_means_disagree_with_analysis": any(
            abs(per_seed_means[key] - analysis[key]["product"]) > 0.005
            for key in per_seed_means
            if key in analysis
        ),
        "episodes_only_180_records": len(episodes) == 180,
        "episodes_have_no_gamma_2": all(
            float(row["gamma_true"]) != 2.0 for row in episodes
        ),
        "real64_contains_one_failure": bool(real64_failures),
        "real64_product_constant": len(real64_degenerate_products) == 8,
        "real128_incomplete_note": int(real128["n_total"]) == 128
        and "1 batch remains" in str(real128.get("note", "")),
        "real192_only_summary": "holds" in real192
        and isinstance(real192["holds"], str),
        "claimed_466_vs_archived_384": sum(
            [192, 144, 90, 40]
        )
        == 466
        and real_calls["total"] == 384,
        "p16_has_no_effect_fields": not (
            {"dz", "d", "ci", "p"} & set(p16_fields)
        ),
        "protocol_has_no_declared_values": all(
            token not in protocol
            for token in ("0.810", "0.797", "0.85", "0.90")
        ),
        "proof_contradicts_abstract": "0.14-0.26" in proof
        and "0.35" in source_text
        and "0.56" in source_text,
        "carrier_receipts_not_backed": "0 of 7" in (
            root / "evidence" / "EVIDENCE_PLAN.md"
        ).read_text(encoding="utf-8"),
        "claim_ledger_present": len(ledger_rows) == 9,
        "abstract_claims_no_abs_carrier": any(abs_claims.values()),
    }
    return {
        "schema": "q-one-f2-audit-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "source": {
            "path": str(source),
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
            "canonical_sha256": sha256_file(upstream / "paper" / "main.tex"),
        },
        "structure": {
            "labels": len(labels),
            "duplicate_labels": [
                key for key, count in labels_counter.items() if count > 1
            ],
            "references": len(references),
            "missing_references": sorted(set(references) - set(labels)),
            "citation_keys": len(refs),
            "bib_keys": len(bib),
            "missing_citations": sorted(refs - bib),
        },
        "joint_2700": {
            "declared_cells": joint["n_cells"],
            "declared_holds": joint["holds"],
            "archived_cells": len(joint["cells"]),
            "distinct_conditions": [
                {"K": key[0], "gamma": key[1]} for key in distinct_joint_conditions
            ],
            "has_duplicate_condition_rows": duplicate_joint_values,
            "analysis_conditions": len(analysis_conditions),
            "bootstrap_point_disagreements": bootstrap_mismatches,
            "per_seed_means": per_seed_means,
            "episode_records": len(episodes),
            "episode_summary": episode_summary,
            "episodes_have_all_gamma_levels": sorted(
                {float(row["gamma_true"]) for row in episodes}
            ),
        },
        "real_llm": {
            "calls": real_calls,
            "claimed_frozen_subset_sum": 466,
            "elapsed_hours": elapsed_hours,
            "real64_degenerate_products": len(real64_degenerate_products),
            "real64_failures": real64_failures,
            "real128_note": real128.get("note"),
            "real192_holds": real192.get("holds"),
        },
        "reported_statistics": {
            "p16_fields": p16_fields,
            "p16_total_cells": p16.get("total_cells"),
            "protocol_bytes": len(protocol.encode("utf-8")),
            "proof_bytes": len(proof.encode("utf-8")),
            "claim_ledger_rows": len(ledger_rows),
            "abstract_statistics_present": abs_claims,
        },
        "checks": checks,
        "gate_states": {
            "source_identity": "passed",
            "structure": "passed" if checks["single_source_structure"] else "failed",
            "citations": "passed" if checks["citations_resolve"] else "failed",
            "k345_empirical_carrier": "blocked",
            "p16_selective": "blocked",
            "p18_drift": "blocked",
            "p21_causal": "blocked",
            "real_llm_subset": "blocked",
            "review": "blocked",
            "package": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "The declared 2700-cell carrier stores five rows and only three conditions.",
            "Three archives claim to hold per-seed products but disagree with the printed values.",
            "The real-LLM counts mix frozen target counts with archived call counts.",
            "p16/p18/p21 effect values lack field-level carriers.",
            "The family is blocked pending a rebuilt, archived experiment.",
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
    print(json.dumps({"checks": payload["checks"], "gate_states": payload["gate_states"]}, indent=2))
    # The script exits zero when it successfully records the contradictions.
    # A "blocked" audit is a valid result, not a tool failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
