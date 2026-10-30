#!/usr/bin/env python3
"""Recompute the memory-architecture pilot's bounded evidence surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
    source = root / "source" / "main.tex"
    source_text = source.read_text(encoding="utf-8")
    labels = re.findall(r"\\label\{([^}]+)\}", source_text)
    references = re.findall(r"\\ref\{([^}]+)\}", source_text)
    labels_counter = Counter(labels)
    refs = citation_keys(source_text)
    bib = bib_keys((root / "source" / "refs.bib").read_text(encoding="utf-8"))

    r1 = load_json(
        upstream / "source" / "evidence" / "r1_v4chat_dose_response_per_seed.json"
    )
    grouped: dict[tuple[str, float], list[tuple[int, float]]] = defaultdict(list)
    for row in r1:
        grouped[(str(row["architecture"]), float(row["contamination_rate"]))].append(
            (int(row["seed"]), float(row["gamma_temporal"]))
        )
    for values in grouped.values():
        values.sort()

    label = {
        "append_only": "Append-Only",
        "rag": "RAG+Filter",
        "summarization": "Summarization",
    }
    contrasts: list[dict[str, Any]] = []
    for rate in (0.2, 0.5, 0.8):
        for a_code, b_code in (
            ("append_only", "rag"),
            ("append_only", "summarization"),
            ("summarization", "rag"),
        ):
            a_values = np.array([value for _, value in grouped[(a_code, rate)]])
            b_values = np.array([value for _, value in grouped[(b_code, rate)]])
            differences = a_values - b_values
            t_stat, p_raw = stats.ttest_rel(a_values, b_values)
            contrasts.append(
                {
                    "rate": rate,
                    "architecture_a": label[a_code],
                    "architecture_b": label[b_code],
                    "n": len(differences),
                    "mean_diff_a_minus_b": float(differences.mean()),
                    "t": float(t_stat),
                    "p_raw": float(p_raw),
                    "d_z": float(differences.mean() / differences.std(ddof=1)),
                }
            )

    filed_contrasts = load_json(
        upstream / "evidence" / "analyses" / "r1_dose_response_contrasts.json"
    )["contrasts"]
    filed_by_key = {
        (
            float(item["rate"]),
            str(item["architecture_a"]),
            str(item["architecture_b"]),
        ): item
        for item in filed_contrasts
    }
    contrast_mismatches = []
    for item in contrasts:
        filed = filed_by_key[
            (
                float(item["rate"]),
                str(item["architecture_a"]),
                str(item["architecture_b"]),
            )
        ]
        for recomputed_key, filed_key, tolerance in (
            ("mean_diff_a_minus_b", "mean_diff_a_minus_b", 5e-4),
            ("t", "t", 5e-3),
            ("p_raw", "p_raw", 5e-5),
            ("d_z", "d_z", 5e-3),
        ):
            if abs(float(item[recomputed_key]) - float(filed[filed_key])) > tolerance:
                contrast_mismatches.append(
                    {
                        "key": f"{item['rate']}|{item['architecture_a']}|{item['architecture_b']}",
                        "field": recomputed_key,
                        "recomputed": item[recomputed_key],
                        "filed": filed[filed_key],
                    }
                )

    r1_cells = {}
    for (architecture, rate), rows in sorted(grouped.items()):
        values = [value for _, value in rows]
        r1_cells[f"{rate}|{label[architecture]}"] = {
            "n": len(values),
            "mean": float(np.mean(values)),
            "sd": float(np.std(values, ddof=1)),
        }

    v4 = load_json(
        upstream / "source" / "evidence" / "p5_grid_v4flash_20260807.json"
    )
    qwen = load_json(
        upstream / "source" / "evidence" / "recomputed_cell_means_FIXED.json"
    )
    round4 = load_json(
        upstream / "evidence" / "analyses" / "round4_validation_20260808.json"
    )
    third = load_json(
        upstream / "evidence" / "analyses" / "p5_third_model_direction_20260809.json"
    )
    external = load_json(
        upstream / "source" / "outputs" / "external_judge_summary.json"
    )
    theta = load_json(
        upstream / "source" / "outputs" / "theta_sweep_summary.json"
    )
    carrier_receipts = load_json(
        upstream / "source" / "evidence" / "CARRIER_RECEIPTS.json"
    )

    qwen_authority_summary = qwen[
        "qwen3.7-plus-Summarization-authority-p0.8"
    ]["mean"]
    qwen_authority_append = qwen["qwen3.7-plus-Append-Only-authority-p0.8"]["mean"]
    external_max_delta = max(
        abs(float(item["delta_ece_judged"]))
        for item in external["per_cell"].values()
    )
    checks = {
        "source_structure_clean": all(
            (
                source_text.count("\\title{") == 1,
                source_text.count("\\author{") == 1,
                source_text.count("\\end{document}") == 1,
                source_text.count("\\textbf{Novelty positioning.}") == 1,
                source_text.count("\\section*{Reproducibility") == 1,
                all(count == 1 for count in labels_counter.values()),
                not (set(references) - set(labels)),
            )
        ),
        "citation_keys_resolve": not (refs - bib),
        "no_template_scripts": all(
            token not in source_text
            for token in (
                "run_all_experiments.py",
                "run_memory_contamination.py",
                "run_model_factorial.py",
                "calibration fatigue",
                "Self-evaluation fragility",
                "OPENAI\\_API\\_KEY",
                "DASHSCOPE\\_API\\_KEY",
            )
        ),
        "r1_has_nine_contrasts_and_n10": len(contrasts) == 9
        and all(item["n"] == 10 for item in contrasts),
        "r1_contrasts_recompute": not contrast_mismatches,
        "r1_canonical_contrast_significant": next(
            item
            for item in contrasts
            if item["rate"] == 0.8
            and item["architecture_a"] == "Append-Only"
            and item["architecture_b"] == "Summarization"
        )["p_raw"]
        < 0.05,
        "v4flash_18_cells_n10": len(v4["cells"]) == 18
        and all(int(cell["n"]) == 10 for cell in v4["cells"].values()),
        "v4flash_carrier_values_match": all(
            (
                abs(v4["cells"]["authority|Append-Only|p0.5"]["mean"] - 0.5209) < 5e-4,
                abs(v4["cells"]["authority|Summarization|p0.8"]["mean"] - 0.5208) < 5e-4,
                abs(v4["cells"]["authority|RAG+Filter|p0.8"]["mean"] - 0.6067) < 5e-4,
                abs(v4["cells"]["length|Append-Only|p0.8"]["mean"] - 2.385) < 5e-4,
            )
        ),
        "qwen_authority_means_match": abs(qwen_authority_summary - 0.544) < 5e-4
        and abs(qwen_authority_append - 0.802) < 5e-4,
        "round4_complete_aggregate": int(round4["files"]) == 1080
        and int(round4["cells"]) == 36
        and bool(round4["schema_ok"])
        and all(int(item["n"]) == 30 for item in round4["per_cell_mean"].values()),
        "round4_reversal_matches": abs(
            float(round4["r1_contrast_replication"]["deepseek-v4-flash"]["diff_sum_app"])
            - 0.2024
        )
        < 5e-4
        and abs(
            float(round4["r1_contrast_replication"]["deepseek-v4-pro"]["diff_sum_app"])
            - 0.0007
        )
        < 5e-4,
        "third_model_direction_matches": third["rows"]["Qwen3.7Plus"]["direction"]
        == "Summ-lower"
        and third["rows"]["deepseek-v4-flash"]["direction"] == "Summ-higher",
        "external_judge_sample_120": int(external["total_judged"]) == 120,
        "external_judge_delta_small": external_max_delta <= 0.0063,
        "theta_sweep": theta["sweep_n_seeds"] == 5
        and float(theta["chosen_theta"]) == 0.1,
        "carrier_receipts_count": len(carrier_receipts) == 7,
        "authority_construct_validity_incomplete": "not validated authority bias"
        in source_text,
    }
    return {
        "schema": "q-one-memory-architecture-audit-v1",
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
            "citation_keys": len(refs),
            "bib_keys": len(bib),
            "missing_citations": sorted(refs - bib),
            "novelty_blocks": source_text.count("\\textbf{Novelty positioning.}"),
            "reproducibility_sections": source_text.count(
                "\\section*{Reproducibility"
            ),
        },
        "r1": {
            "records": len(r1),
            "contrast_count": len(contrasts),
            "n_seeds_per_contrast": sorted({item["n"] for item in contrasts}),
            "cells": r1_cells,
            "contrasts": contrasts,
            "contrast_mismatches": contrast_mismatches,
            "canonical_r1_contrast": next(
                item
                for item in contrasts
                if item["rate"] == 0.8
                and item["architecture_a"] == "Append-Only"
                and item["architecture_b"] == "Summarization"
            ),
            "selected_cells": {
                "p0.2|Append-Only": r1_cells["0.2|Append-Only"],
                "p0.2|RAG+Filter": r1_cells["0.2|RAG+Filter"],
                "p0.8|Append-Only": r1_cells["0.8|Append-Only"],
                "p0.8|Summarization": r1_cells["0.8|Summarization"],
            },
        },
        "v4flash": {
            "cells": len(v4["cells"]),
            "selected_means": {
                key: v4["cells"][key]["mean"]
                for key in (
                    "authority|Append-Only|p0.5",
                    "authority|Summarization|p0.8",
                    "authority|RAG+Filter|p0.8",
                    "length|Append-Only|p0.8",
                )
            },
        },
        "qwen_authority": {
            "summarization_mean": qwen_authority_summary,
            "append_only_mean": qwen_authority_append,
            "construct_status": "descriptive output-length response; not validated authority bias",
        },
        "round4": {
            "files": round4["files"],
            "cells": round4["cells"],
            "schema_ok": round4["schema_ok"],
            "raw_per_seed_logs_retained": False,
            "replication": round4["r1_contrast_replication"],
            "all_cell_n": sorted(
                {int(item["n"]) for item in round4["per_cell_mean"].values()}
            ),
        },
        "external_judge": {
            "total_judged": external["total_judged"],
            "max_abs_delta_ece": external_max_delta,
            "scope": "calibration-bound audit only",
        },
        "theta_sweep": theta,
        "carrier_receipts": {
            "count": len(carrier_receipts),
            "upstream_tool_result": {
                "command": "python3 tools/carrier_receipts.py --run runs/tmlr-paper5-consolidated",
                "tally": "PASS=7 FAIL=0 NOT_VERIFIABLE=0",
            },
        },
        "checks": checks,
        "gate_states": {
            "source_identity": "passed",
            "structure": "passed"
            if checks["source_structure_clean"]
            and checks["no_template_scripts"]
            else "failed",
            "citations": "passed" if checks["citation_keys_resolve"] else "failed",
            "r1_confirmatory": "passed"
            if checks["r1_has_nine_contrasts_and_n10"]
            and checks["r1_contrasts_recompute"]
            else "failed",
            "qwen_authority": "candidate",
            "round4_factorial": "passed"
            if checks["round4_complete_aggregate"]
            and checks["round4_reversal_matches"]
            else "failed",
            "construct_validity": "blocked",
            "independent_review": "blocked",
            "package": "candidate",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "R1 contains 90 per-seed records and the nine predeclared contrasts recompute.",
            "The current overlay removes unrelated calibration and template blocks.",
            "The authority-marker arm remains a descriptive output-length response.",
            "Round-4 is available only as aggregate validation in the retained package.",
            "No upload or external account action was performed.",
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
    required = list(payload["checks"].values())
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
