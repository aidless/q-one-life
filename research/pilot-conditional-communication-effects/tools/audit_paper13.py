#!/usr/bin/env python3
"""Audit the conditional-communication merged paper without promoting claims."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from collections import Counter
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


def numeric_hits(root: Path, targets: list[float], tolerance: float = 5e-4) -> dict:
    hits: dict[str, list[dict[str, Any]]] = {str(target): [] for target in targets}

    def walk(value: Any, path: str):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from walk(child, f"{path}[{index}]")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            yield path, float(value)

    for path in sorted(root.rglob("*.json")):
        try:
            payload = load_json(path)
        except (OSError, ValueError):
            continue
        for leaf_path, value in walk(payload, "$"):
            for target in targets:
                if abs(value - target) <= tolerance:
                    hits[str(target)].append(
                        {
                            "file": str(path.relative_to(root)),
                            "path": leaf_path,
                            "value": value,
                        }
                    )
    return {
        "targets": targets,
        "tolerance": tolerance,
        "hit_count": sum(len(items) for items in hits.values()),
        "hits": hits,
    }


def load_recompute_module(path: Path):
    spec = importlib.util.spec_from_file_location("paper13_recompute_joint_anova", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    upstream = root / "evidence" / "upstream"
    paper = upstream / "paper"
    source = paper / "main.tex"
    source_text = source.read_text(encoding="utf-8")
    labels = re.findall(r"\\label\{([^}]+)\}", source_text)
    references = re.findall(r"\\ref\{([^}]+)\}", source_text)
    labels_counter = Counter(labels)
    cited = citation_keys(source_text)
    bib = bib_keys((paper / "refs.bib").read_text(encoding="utf-8"))

    joint = load_json(paper / "evidence" / "joint_full_F_v10_results.json")
    rows = [
        row
        for row in joint["sessions"]
        if row.get("T") in (10, 20) and row.get("final_ECE") is not None
    ]
    recompute = load_recompute_module(root / "tools" / "recompute_joint_anova.py")
    subset = recompute.documented_subset(rows, 15)
    anova = recompute.anova2_balanced(subset)

    e4 = load_json(upstream / "source" / "evidence" / "e4_30seed_calibrated.json")
    gtv_reduction = (
        (float(e4["uncalibrated"]["gTV"]) - float(e4["calibrated"]["gTV"]))
        / float(e4["uncalibrated"]["gTV"])
        * 100
    )
    gvt_reduction = (
        (float(e4["uncalibrated"]["gVT"]) - float(e4["calibrated"]["gVT"]))
        / float(e4["uncalibrated"]["gVT"])
        * 100
    )
    heldout = load_json(
        upstream
        / "source"
        / "evidence"
        / "analyses"
        / "p1_heldout_v4pro_20260813.json"
    )
    heldout_by_seed: dict[int, dict[int, float]] = {}
    for row in heldout["results"]:
        heldout_by_seed.setdefault(int(row["seed"]), {})[
            int(row["n_rounds"])
        ] = float(row["final_ece"])
    heldout_deltas = [
        values[20] - values[10]
        for _, values in sorted(heldout_by_seed.items())
    ]
    heldout_mean_delta = float(np.mean(heldout_deltas))

    landscape = load_json(upstream / "evidence" / "landscape_5conditions.json")
    conditions = landscape["conditions"]
    gamma = np.array([float(row["gamma"]) for row in conditions], dtype=float)
    entropy = np.array([float(row["H"]) for row in conditions], dtype=float)
    cv = np.array([float(row["CV_N5"]) for row in conditions], dtype=float)
    r_h_gamma = float(np.corrcoef(entropy, gamma)[0, 1])
    r_cv_gamma = float(np.corrcoef(cv, gamma)[0, 1])

    caf_hits = numeric_hits(
        upstream,
        [1.243, 1.35, 1.416, 1.518, 1.088, 1.204],
    )
    legacy_values = {
        value: source_text.count(value)
        for value in ("8.16", "7.845", "7.84", "15.37")
    }
    source_mirror = (
        root / "evidence" / "variants" / "paper13-source-mirror" / "main.tex"
    ).read_text(encoding="utf-8")
    source_legacy_values = {
        value: source_mirror.count(value)
        for value in ("8.16", "7.845", "7.84", "15.37")
    }

    checks = {
        "single_title_and_author": source_text.count("\\title{") == 1
        and source_text.count("\\author{") == 1,
        "single_end_document": source_text.count("\\end{document}") == 1,
        "single_broader_impact": source_text.count("\\section*{Broader Impact") == 1,
        "single_reproducibility": source_text.count("\\section*{Reproducibility") == 1,
        "labels_unique": all(count == 1 for count in labels_counter.values()),
        "references_resolve": not (set(references) - set(labels)),
        "citations_resolve": not (cited - bib),
        "current_paper_uses_reproducible_anova": all(
            value in source_text for value in ("6.61", "2.95", "2.22")
        ),
        "current_paper_excludes_legacy_anova": all(
            count == 0 for count in legacy_values.values()
        ),
        "source_mirror_contains_legacy_anova": all(
            source_legacy_values[value] > 0 for value in ("8.16", "7.84", "15.37")
        ),
        "joint_metadata_4000_calls_125_sessions": int(joint["metadata"]["total_calls"])
        == 4000
        and int(joint["metadata"]["total_cells_completed"]) == 125,
        "balanced_alpha_recomputed": abs(anova["F_A"] - 6.61) <= 0.005
        and abs(anova["p_A"] - 0.0022) <= 5e-5,
        "temporal_and_interaction_not_significant": anova["p_T"] > 0.05
        and anova["p_AB"] > 0.05,
        "face1_caf_raw_carrier_absent": caf_hits["hit_count"] == 0,
        "e4_30seed_reduction_29_4_to_30_8": min(gtv_reduction, gvt_reduction) >= 29.3
        and max(gtv_reduction, gvt_reduction) <= 30.9,
        "heldout_n3_delta_minus_0_007": len(heldout_deltas) == 3
        and abs(heldout_mean_delta - (-0.007)) <= 5e-4,
        "landscape_correlations_recompute": abs(r_h_gamma + 0.989) <= 5e-4
        and abs(r_cv_gamma + 0.916) <= 5e-4,
    }
    return {
        "schema": "q-one-conditional-communication-audit-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "source": {
            "path": str(source),
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
        },
        "structure": {
            "labels": len(labels),
            "duplicate_labels": [
                key for key, count in labels_counter.items() if count > 1
            ],
            "references": len(references),
            "missing_references": sorted(set(references) - set(labels)),
            "citation_keys": len(cited),
            "bib_keys": len(bib),
            "missing_citations": sorted(cited - bib),
            "legacy_anova_counts_current": legacy_values,
            "legacy_anova_counts_source_mirror": source_legacy_values,
        },
        "joint_experiment": {
            "metadata": joint["metadata"],
            "stored_anova": joint["summary"]["anova_ECE"],
            "balanced_recompute": anova,
            "stored_anova_reproducible": False,
            "reason": "Stored SS_within=2.8975 is unreachable; documented subset gives SS_within=2.3917.",
        },
        "e4": {
            "n_seeds": e4["n_seeds"],
            "uncalibrated_gTV": e4["uncalibrated"]["gTV"],
            "calibrated_gTV": e4["calibrated"]["gTV"],
            "gTV_reduction_pct": gtv_reduction,
            "gVT_reduction_pct": gvt_reduction,
        },
        "heldout_v4pro": {
            "n_seeds": heldout["n_seeds"],
            "model": heldout["model"],
            "per_seed_delta_ece": heldout_deltas,
            "mean_delta_ece": heldout_mean_delta,
            "interpretation": "The held-out run did not reproduce the original GPT-4o temporal-fatigue contrast; n=3 is only a small non-replication probe.",
        },
        "landscape": {
            "n": landscape["n"],
            "r_H_gamma": r_h_gamma,
            "r_CV_gamma": r_cv_gamma,
        },
        "face1_caf_carrier_search": caf_hits,
        "checks": checks,
        "gate_states": {
            "source_structure": "passed"
            if all(
                checks[key]
                for key in (
                    "single_title_and_author",
                    "single_end_document",
                    "single_broader_impact",
                    "single_reproducibility",
                    "labels_unique",
                    "references_resolve",
                )
            )
            else "failed",
            "citations": "passed" if checks["citations_resolve"] else "failed",
            "face1_caf_raw": "blocked"
            if checks["face1_caf_raw_carrier_absent"]
            else "candidate",
            "joint_anova": "blocked",
            "e4_30seed": "passed"
            if checks["e4_30seed_reduction_29_4_to_30_8"]
            else "failed",
            "landscape": "passed"
            if checks["landscape_correlations_recompute"]
            else "failed",
            "independent_review": "blocked",
            "package": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "The current canonical paper uses the reproducible balanced ANOVA values.",
            "The old source mirror still carries legacy values and must not be used independently.",
            "Face-1 CAF values have no retained per-seed carrier.",
            "The paper remains a blocked multi-lineage synthesis, not an arXiv-ready manuscript.",
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
    required = [
        payload["checks"]["single_title_and_author"],
        payload["checks"]["single_end_document"],
        payload["checks"]["single_broader_impact"],
        payload["checks"]["single_reproducibility"],
        payload["checks"]["labels_unique"],
        payload["checks"]["references_resolve"],
        payload["checks"]["citations_resolve"],
        payload["checks"]["current_paper_excludes_legacy_anova"],
        payload["checks"]["source_mirror_contains_legacy_anova"],
        payload["checks"]["joint_metadata_4000_calls_125_sessions"],
        payload["checks"]["balanced_alpha_recomputed"],
        payload["checks"]["temporal_and_interaction_not_significant"],
        payload["checks"]["face1_caf_raw_carrier_absent"],
        payload["checks"]["e4_30seed_reduction_29_4_to_30_8"],
        payload["checks"]["heldout_n3_delta_minus_0_007"],
        payload["checks"]["landscape_correlations_recompute"],
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
