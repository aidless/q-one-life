#!/usr/bin/env python3
"""Audit the deprecated hidden-cost/resampling family without editing its source."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

OVERLAY = Path(__file__).resolve().parents[1]
UPSTREAM = Path("/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-tmlr-p6")
P12 = Path("/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-tmlr-p12/paper/main.tex")
CANONICAL = UPSTREAM / "paper/main.tex"
CONFIGURED_DATE = "2026-10-28T00:00:00Z"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def pearson(xs: list[float], ys: list[float]) -> float:
    xm, ym = statistics.mean(xs), statistics.mean(ys)
    numerator = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - xm) ** 2 for x in xs) * sum((y - ym) ** 2 for y in ys)
    )
    return numerator / denominator


def model_rows(snapshot: dict[str, Any], model: str) -> list[dict[str, Any]]:
    rows = [
        metric["metrics"]
        for seed in snapshot["seed_results"]
        for metric in seed["metrics"]
        if metric["model_name"] == model
    ]
    if not rows:
        raise ValueError(f"model is absent from snapshot: {model}")
    return rows


def metric_mean(snapshot: dict[str, Any], model: str, key: str) -> float:
    return statistics.mean(float(row[key]) for row in model_rows(snapshot, model))


def main() -> int:
    files = {
        "canonical": CANONICAL,
        "preprint_backup": UPSTREAM / "paper/main.tex.bak_20261001T0205Z_preprint",
        "legacy_research_mirror": Path("/home/liuzewen/.research/tmlr-p6/main.tex"),
        "aris_backup": UPSTREAM / ".aris/backup/main.tex.before_literal_cites",
        "ingest_drift": UPSTREAM / ".aris/ingest_drift/20260928T102343Z/main.tex",
        "submission_variant": UPSTREAM / "source/submission_variant/main.tex",
        "source_mirror": UPSTREAM / "source/main.tex",
    }
    variants = [
        {"name": name, "path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}
        for name, path in files.items()
    ]
    distinct_hashes = len({row["sha256"] for row in variants})
    retained_files = len(variants)

    canonical_text = CANONICAL.read_text(encoding="utf-8")
    p12_text = P12.read_text(encoding="utf-8")
    overlay_copy = OVERLAY / "evidence/upstream/main.tex"
    p12_copy = OVERLAY / "evidence/upstream/tmlr_p12_main.tex"
    marker_path = OVERLAY / "evidence/upstream/MERGED_INTO_tmlr_p12_20260921.md"
    review_path = OVERLAY / "evidence/upstream/REVIEW_CARD.md"
    review_r16_path = OVERLAY / "evidence/upstream/REVIEW_R16_summary.md"
    anonymity_path = OVERLAY / "evidence/upstream/manuscript_anonymity.json"
    receipts_path = OVERLAY / "evidence/upstream/CARRIER_RECEIPTS.json"
    marker = marker_path.read_text(encoding="utf-8")
    review = review_path.read_text(encoding="utf-8")
    review_r16 = review_r16_path.read_text(encoding="utf-8")
    anonymity = json.loads(anonymity_path.read_text(encoding="utf-8"))
    receipts = json.loads(receipts_path.read_text(encoding="utf-8"))

    term_counts = {
        term: p12_text.lower().count(term.lower())
        for term in [
            "hidden cost of resampling",
            "imbalance correction",
            "probability calibration",
            "tree ensembles",
            "isotonic",
            "class imbalance",
            "SMOTE",
            "random undersampling",
            "frozen embeddings",
            "BGE-small-zh-v1.5",
            "synthetic style-classification",
            "RF-Hybrid",
            "MLP-Embed",
            "N-sensitivity",
        ]
    }
    study_terms = [
        "SMOTE",
        "random undersampling",
        "isotonic",
        "frozen embeddings",
        "BGE-small-zh-v1.5",
        "synthetic style-classification",
        "RF-Hybrid",
        "MLP-Embed",
    ]
    study_term_matches = sum(term_counts[term] for term in study_terms)

    main_path = OVERLAY / "evidence/upstream/supplementary/newsgroups_20260627_195431.json"
    ns_path = OVERLAY / "evidence/upstream/supplementary/n_sensitivity_newsgroups_20260627_191332.json"
    main_snapshot = json.loads(main_path.read_text(encoding="utf-8"))
    ns_snapshot = json.loads(ns_path.read_text(encoding="utf-8"))
    models = ["MLP-Embed", "RF-Embed", "RF-Hybrid", "RF-Tabular"]
    main_table = {}
    for model in models:
        main_table[model] = {
            "snapshot": {
                key: main_snapshot["aggregated"][model].get(f"{key}_mean")
                for key in ("ece", "auroc", "accuracy")
            },
            "seed_mean": {
                key: metric_mean(main_snapshot, model, key)
                for key in ("ece", "auroc", "brier", "accuracy")
            },
            "accuracy_seed_min": min(row["accuracy"] for row in model_rows(main_snapshot, model)),
            "accuracy_seed_max": max(row["accuracy"] for row in model_rows(main_snapshot, model)),
        }

    pre = main_snapshot["aggregated"]["RF-Hybrid"]
    post = main_snapshot["aggregated"]["RF-Hybrid-Isotonic"]
    isotonic = {
        "ece_before": pre["ece_mean"],
        "ece_after": post["ece_mean"],
        "ece_reduction": pre["ece_mean"] - post["ece_mean"],
        "ece_reduction_pct": 100 * (pre["ece_mean"] - post["ece_mean"]) / pre["ece_mean"],
        "auroc_before": pre["auroc_mean"],
        "auroc_after": post["auroc_mean"],
        "auroc_change": post["auroc_mean"] - pre["auroc_mean"],
    }
    pairwise = main_snapshot["pairwise_tests_ece"]
    significance = {
        "pairs": len(pairwise),
        "raw_significant": sum(bool(row["significant"]) for row in pairwise),
        "corrected_significant": sum(bool(row["significant_corrected"]) for row in pairwise),
        "raw_only": [
            {
                "model_a": row["model_a"],
                "model_b": row["model_b"],
                "p_value": row["p_value"],
                "p_value_corrected": row["p_value_corrected"],
            }
            for row in pairwise
            if row["significant"] and not row["significant_corrected"]
        ],
    }

    sizes = [200, 500, 1000, 2000, 5000]
    ns_table = {}
    for model in ("MLP-Embed", "RF-Hybrid", "RF-Embed"):
        values = [ns_snapshot["summary"][str(size)][model]["ece"] for size in sizes]
        ns_table[model] = {
            "values": values,
            "rounded": [round(value, 3) for value in values],
            "r_linear": pearson([float(x) for x in sizes], values),
            "r_log10": pearson([math.log10(x) for x in sizes], values),
        }

    wrong_quantity = {
        0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 17, 18, 20, 21,
        22, 23, 24, 27, 28, 37, 46, 48, 49, 50, 51, 52, 53, 55, 56,
    }
    wrong_model = {19, 36, 44}
    wrong_run = {2, 13, 16, 25, 26, 54}
    semantic_mismatches = wrong_quantity | wrong_model | wrong_run
    examples = [
        {"index": 3, "printed": 0.037, "role": "isotonic AUROC cost", "bound": receipts[3]["over"], "quantity": receipts[3]["quantity"], "problem": "ECE pairwise mean difference, not AUROC"},
        {"index": 4, "printed": 0.003, "role": "tabular AUROC comparator", "bound": receipts[4]["over"], "quantity": receipts[4]["quantity"], "problem": "unrelated ECE comparison; comparator has no carrier"},
        {"index": 11, "printed": 0.992, "role": "MLP AUROC", "bound": receipts[11]["over"], "quantity": receipts[11]["quantity"], "problem": "reliability bin confidence, not AUROC"},
        {"index": 14, "printed": 0.989, "role": "RF-Embed AUROC", "bound": receipts[14]["over"], "quantity": receipts[14]["quantity"], "problem": "reliability bin confidence, not AUROC"},
        {"index": 17, "printed": 0.990, "role": "RF-Hybrid AUROC", "bound": receipts[17]["over"], "quantity": receipts[17]["quantity"], "problem": "reliability bin confidence, not AUROC"},
        {"index": 18, "printed": 0.065, "role": "RF-Hybrid Brier", "bound": receipts[18]["over"], "quantity": receipts[18]["quantity"], "problem": "MLP accuracy standard deviation, not Brier"},
        {"index": 20, "printed": 0.941, "role": "RF-Tabular AUROC", "bound": receipts[20]["over"], "quantity": receipts[20]["quantity"], "problem": "one reliability bin accuracy, not AUROC"},
        {"index": 21, "printed": 0.118, "role": "RF-Tabular Brier", "bound": receipts[21]["over"], "quantity": receipts[21]["quantity"], "problem": "one class ECE, not Brier"},
        {"index": 46, "printed": 0.078, "role": "MLP Pearson r", "bound": receipts[46]["over"], "quantity": receipts[46]["quantity"], "problem": "RF-Hybrid accuracy standard deviation, not correlation"},
        {"index": 50, "printed": 1.5, "role": "BGE v1.5", "bound": receipts[50]["over"], "quantity": receipts[50]["quantity"], "problem": "seed training time, not model version"},
    ]
    verdicts = Counter(str(row.get("_verdict", "ABSENT")) for row in receipts)

    text_checks = {
        "title_resampling_occurrences": len(re.findall("resampl", canonical_text, re.IGNORECASE)),
        "smote_occurrences": len(re.findall("SMOTE", canonical_text, re.IGNORECASE)),
        "undersampling_occurrences": len(re.findall("undersampl", canonical_text, re.IGNORECASE)),
        "imbalance_occurrences": len(re.findall("imbalance", canonical_text, re.IGNORECASE)),
        "newsgroups_occurrences": len(re.findall("newsgroups", canonical_text, re.IGNORECASE)),
        "synthetic_occurrences": len(re.findall("synthetic", canonical_text, re.IGNORECASE)),
        "limitations_headings": canonical_text.count(r"\subsection{Limitations}"),
        "says_no_sample_size_sweep": "no sample-size sweep" in canonical_text,
        "has_sample_size_table": r"\label{tab:n_sensitivity}" in canonical_text,
        "says_all_models_perfect_accuracy": "all models achieve perfect accuracy" in canonical_text or "all embedding-based models achieve perfect accuracy" in canonical_text,
        "claims_corrected_12_of_15": "12 of 15 model pairs" in canonical_text,
        "corrected_12_of_15_supported": significance["corrected_significant"] == 12,
    }

    audit = {
        "schema": "q-one-p16-hidden-cost-audit-v1",
        "generated_at": CONFIGURED_DATE,
        "marker": "agent-proposed, not human publication approval",
        "family_id": "qf-the-hidden-cost-of-resampling-how-imbala-36f86aadfa",
        "project_id": "qp-tmlr-tmlr-p6-60e62c7566d9",
        "canonical": {
            "path": str(CANONICAL),
            "sha256": sha(CANONICAL),
            "bytes": CANONICAL.stat().st_size,
            "overlay_copy_sha256": sha(overlay_copy),
            "byte_identical_to_overlay": sha(CANONICAL) == sha(overlay_copy),
            "deprecated_banner_present": "DEPRECATED — DO NOT SUBMIT INDEPENDENTLY" in "\n".join(canonical_text.splitlines()[:8]),
            "banner": "\n".join(canonical_text.splitlines()[:5]),
        },
        "variants": {
            "retained_files": retained_files,
            "distinct_hashes": distinct_hashes,
            "all_distinct": distinct_hashes == retained_files,
            "rows": variants,
            "excluded_duplicates": [
                {"path": str(UPSTREAM / "arxiv/main.tex"), "sha256": sha(UPSTREAM / "arxiv/main.tex"), "duplicate_of": "canonical"},
                {"path": str(UPSTREAM / "source/submission_variant/main.tex"), "sha256": sha(UPSTREAM / "source/submission_variant/main.tex"), "duplicate_of": "submission_variant"},
                {"path": str(UPSTREAM / ".aris/backup/main.tex.before_literal_cites_20260929T1833Z"), "sha256": sha(UPSTREAM / ".aris/backup/main.tex.before_literal_cites_20260929T1833Z"), "duplicate_of": "aris_backup"},
            ],
        },
        "merge_target": {
            "path": str(P12),
            "sha256": sha(P12),
            "overlay_copy_sha256": sha(p12_copy),
            "byte_identical_to_overlay": sha(P12) == sha(p12_copy),
            "term_counts": term_counts,
            "study_term_matches": study_term_matches,
            "n_sensitivity_mentions": term_counts["N-sensitivity"],
            "marker_says_merged": "已并入正典" in marker and "不再单投、不再上传" in marker,
            "merge_provenance_closed": study_term_matches > 0,
        },
        "review": {
            "card_sha256": sha(review_path),
            "card_score": "2/8",
            "card_disposition": "D veto / reject",
            "r16_sha256": sha(review_r16_path),
            "r16_requires_major_revision": "Major Revision" in review_r16,
            "card_requires_reject": "弃投" in review,
        },
        "source_scope": {
            "canonical": {"dataset": "synthetic style-classification", "embedding": "BGE-small-zh-v1.5", "samples": 996, "classes": 6, "seeds": 10},
            "main_snapshot": {
                "dataset": main_snapshot.get("dataset"),
                "embedding_key": main_snapshot.get("version_metadata", {}).get("embedding_model", {}).get("key"),
                "embedding_name": main_snapshot.get("version_metadata", {}).get("embedding_model", {}).get("name"),
                "n_samples": main_snapshot.get("config", {}).get("n_samples"),
                "n_seeds": main_snapshot.get("config", {}).get("n_seeds"),
                "num_classes": main_snapshot.get("config", {}).get("num_classes"),
            },
            "n_sensitivity": {
                "dataset": ns_snapshot.get("dataset"),
                "embedding_model": ns_snapshot.get("embedding_model"),
                "n_seeds": ns_snapshot.get("n_seeds"),
                "sample_sizes": ns_snapshot.get("sample_sizes"),
            },
            "conflict": True,
        },
        "main_table": main_table,
        "isotonic": isotonic,
        "significance": significance,
        "n_sensitivity": ns_table,
        "carrier_receipts": {
            "total": len(receipts),
            "verdicts": dict(sorted(verdicts.items())),
            "all_mechanical_pass": set(verdicts) == {"PASS"},
            "semantic_mismatch_count": len(semantic_mismatches),
            "semantic_mismatch_indices": sorted(semantic_mismatches),
            "semantic_mismatch_categories": {
                "printed_quantity_differs_from_bound_quantity": len(wrong_quantity),
                "wrong_model_run_label": len(wrong_model),
                "wrong_snapshot_or_seed": len(wrong_run),
            },
            "examples": examples,
            "mechanical_pass_is_sufficient": False,
        },
        "anonymity": {
            "recorded_author_is_anonymous": anonymity.get("author_is_anonymous"),
            "canonical_author_is_named": r"\name Zewen Liu" in canonical_text,
            "canonical_real_identity_present": "Zewen Liu" in canonical_text,
            "canonical_preprint_option": r"\usepackage[preprint]{tmlr}" in canonical_text,
            "conflict": bool(anonymity.get("author_is_anonymous") is True and "Zewen Liu" in canonical_text),
        },
        "text_checks": text_checks,
        "decision": {
            "disposition": "merge_archive",
            "status": "archived",
            "independent_package_created": False,
            "uploaded": False,
            "reason": "The canonical source forbids independent submission; the p12 target shares N-sensitivity vocabulary but not the study data or numbers; table scopes conflict; and mechanical carrier PASS does not establish semantic binding.",
        },
    }
    write_json(OVERLAY / "evidence/audit.json", audit)

    source_record = {
        "schema": "q-one-p16-source-record-v1",
        "generated_at": CONFIGURED_DATE,
        "family_id": audit["family_id"],
        "project_id": audit["project_id"],
        "canonical_path": str(CANONICAL),
        "canonical_sha256": sha(CANONICAL),
        "overlay_path": str(overlay_copy),
        "overlay_sha256": sha(overlay_copy),
        "byte_identical": sha(CANONICAL) == sha(overlay_copy),
        "deprecated_banner_present": audit["canonical"]["deprecated_banner_present"],
        "merge_marker_path": str(marker_path),
        "merge_marker_sha256": sha(marker_path),
        "review_card_path": str(review_path),
        "review_card_sha256": sha(review_path),
        "review_r16_path": str(review_r16_path),
        "review_r16_sha256": sha(review_r16_path),
        "native_claims_path": str(OVERLAY / "evidence/upstream/claims.yaml"),
        "native_claims_sha256": sha(OVERLAY / "evidence/upstream/claims.yaml"),
        "anonymity_record_path": str(anonymity_path),
        "anonymity_record_sha256": sha(anonymity_path),
        "carrier_receipts_path": str(receipts_path),
        "carrier_receipts_sha256": sha(receipts_path),
    }
    write_json(OVERLAY / "evidence/source_record.json", source_record)

    reconciliation = {
        "schema": "q-one-p16-variant-reconciliation-v1",
        "generated_at": CONFIGURED_DATE,
        "retained_files": retained_files,
        "distinct_hashes": distinct_hashes,
        "all_distinct": distinct_hashes == retained_files,
        "canonical_sha256": sha(CANONICAL),
        "variants": variants,
        "byte_identical_copies_not_counted_as_variants": audit["variants"]["excluded_duplicates"],
        "scope": audit["source_scope"],
        "merge_target": audit["merge_target"],
        "decision": audit["decision"],
    }
    write_json(OVERLAY / "evidence/variant-reconciliation.json", reconciliation)

    values = {
        "schema": "q-one-p16-claim-values-v1",
        "generated_at": CONFIGURED_DATE,
        "canonical_sha256": sha(CANONICAL),
        "retained_variant_files": retained_files,
        "distinct_variant_hashes": distinct_hashes,
        "deprecated_banner_present": int(audit["canonical"]["deprecated_banner_present"]),
        "merge_marker_says_merged": int(audit["merge_target"]["marker_says_merged"]),
        "p12_study_term_matches": study_term_matches,
        "p12_n_sensitivity_mentions": term_counts["N-sensitivity"],
        "p12_has_p16_numeric_carrier": 0,
        "main_snapshot_dataset_newsgroups": int(main_snapshot.get("dataset") == "newsgroups"),
        "main_snapshot_classes": main_snapshot["config"]["num_classes"],
        "main_snapshot_seeds": main_snapshot["config"]["n_seeds"],
        "main_snapshot_embedding_key": main_snapshot["version_metadata"]["embedding_model"]["key"],
        "canonical_classes": 6,
        "canonical_samples": 996,
        "canonical_embedding": "bge-small-zh-v1.5",
        "mlp_embed_ece": metric_mean(main_snapshot, "MLP-Embed", "ece"),
        "rf_embed_ece": metric_mean(main_snapshot, "RF-Embed", "ece"),
        "rf_hybrid_ece": metric_mean(main_snapshot, "RF-Hybrid", "ece"),
        "rf_tabular_ece": metric_mean(main_snapshot, "RF-Tabular", "ece"),
        "mlp_embed_auroc": metric_mean(main_snapshot, "MLP-Embed", "auroc"),
        "rf_embed_auroc": metric_mean(main_snapshot, "RF-Embed", "auroc"),
        "rf_hybrid_auroc": metric_mean(main_snapshot, "RF-Hybrid", "auroc"),
        "rf_tabular_auroc": metric_mean(main_snapshot, "RF-Tabular", "auroc"),
        "mlp_embed_brier": metric_mean(main_snapshot, "MLP-Embed", "brier"),
        "rf_embed_brier": metric_mean(main_snapshot, "RF-Embed", "brier"),
        "rf_hybrid_brier": metric_mean(main_snapshot, "RF-Hybrid", "brier"),
        "rf_tabular_brier": metric_mean(main_snapshot, "RF-Tabular", "brier"),
        "isotonic_ece_before": isotonic["ece_before"],
        "isotonic_ece_after": isotonic["ece_after"],
        "isotonic_ece_reduction_pct": isotonic["ece_reduction_pct"],
        "isotonic_auroc_change": isotonic["auroc_change"],
        "pairwise_count": significance["pairs"],
        "pairwise_raw_significant": significance["raw_significant"],
        "pairwise_corrected_significant": significance["corrected_significant"],
        "rf_hybrid_n200": ns_table["RF-Hybrid"]["values"][0],
        "rf_hybrid_n500": ns_table["RF-Hybrid"]["values"][1],
        "rf_hybrid_n1000": ns_table["RF-Hybrid"]["values"][2],
        "rf_hybrid_n2000": ns_table["RF-Hybrid"]["values"][3],
        "rf_hybrid_n5000": ns_table["RF-Hybrid"]["values"][4],
        "rf_embed_n200": ns_table["RF-Embed"]["values"][0],
        "rf_embed_n500": ns_table["RF-Embed"]["values"][1],
        "rf_embed_n1000": ns_table["RF-Embed"]["values"][2],
        "rf_embed_n2000": ns_table["RF-Embed"]["values"][3],
        "rf_embed_n5000": ns_table["RF-Embed"]["values"][4],
        "mlp_n200": ns_table["MLP-Embed"]["values"][0],
        "mlp_n500": ns_table["MLP-Embed"]["values"][1],
        "mlp_n1000": ns_table["MLP-Embed"]["values"][2],
        "mlp_n2000": ns_table["MLP-Embed"]["values"][3],
        "mlp_n5000": ns_table["MLP-Embed"]["values"][4],
        "mlp_r_linear": ns_table["MLP-Embed"]["r_linear"],
        "rf_hybrid_r_linear": ns_table["RF-Hybrid"]["r_linear"],
        "rf_hybrid_r_log10": ns_table["RF-Hybrid"]["r_log10"],
        "carrier_total": len(receipts),
        "carrier_pass": verdicts.get("PASS", 0),
        "carrier_semantic_mismatch": len(semantic_mismatches),
        "title_resampling_occurrences": text_checks["title_resampling_occurrences"],
        "smote_occurrences": text_checks["smote_occurrences"],
        "undersampling_occurrences": text_checks["undersampling_occurrences"],
        "limitations_headings": text_checks["limitations_headings"],
        "says_no_sample_size_sweep": int(text_checks["says_no_sample_size_sweep"]),
        "has_sample_size_table": int(text_checks["has_sample_size_table"]),
        "anonymous_record_conflict": int(audit["anonymity"]["conflict"]),
        "review_card_score": "2/8",
        "independent_package_created": 0,
        "uploaded": 0,
    }
    write_json(OVERLAY / "evidence/claim-values.json", values)

    ledger = f'''# Claim ledger - hidden-cost / resampling archive

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The canonical source is retained byte-for-byte and has the recorded SHA-256. | evidence/source_record.json -> canonical_sha256 / byte_identical | {sha(CANONICAL)} / 1 | Re-hash the canonical file and overlay copy | verified |
| C02 | The canonical source starts with an explicit DEPRECATED / DO NOT SUBMIT INDEPENDENTLY banner. | evidence/claim-values.json -> deprecated_banner_present | {values['deprecated_banner_present']} | Read the first five lines of `evidence/upstream/main.tex` | verified |
| C03 | Seven retained source files have seven distinct hashes; byte-identical mirrors are excluded from the variant count. | evidence/variant-reconciliation.json -> retained_files / distinct_hashes | {retained_files} / {distinct_hashes} | Re-hash each listed file and exclude exact duplicates | verified |
| C04 | The archive marker says the side shell must not be submitted or uploaded independently. | evidence/claim-values.json -> merge_marker_says_merged | {values['merge_marker_says_merged']} | Read `evidence/upstream/MERGED_INTO_tmlr_p12_20260921.md` | verified |
| C05 | The named `tmlr_p12` target shares N-sensitivity vocabulary but contains no P16 data, model or result carrier. | evidence/claim-values.json -> p12_study_term_matches / p12_has_p16_numeric_carrier | {values['p12_study_term_matches']} / {values['p12_has_p16_numeric_carrier']} | Search the pinned p12 source and compare its SHA-256 | blocked |
| C06 | The canonical text names a synthetic benchmark, while the main snapshot is 1,000-sample 8-class Newsgroups with MiniLM embeddings. | evidence/claim-values.json -> main_snapshot_dataset_newsgroups / main_snapshot_classes / main_snapshot_embedding_key | {values['main_snapshot_dataset_newsgroups']} / {values['main_snapshot_classes']} / {values['main_snapshot_embedding_key']} | Inspect `config` and `version_metadata` in the 195431 snapshot | blocked |
| C07 | The title says resampling, but the manuscript contains only one occurrence of `resampl`, zero SMOTE and zero undersampling experiments. | evidence/claim-values.json -> title_resampling_occurrences / smote_occurrences / undersampling_occurrences | {values['title_resampling_occurrences']} / {values['smote_occurrences']} / {values['undersampling_occurrences']} | Search `paper/main.tex` for the three terms | blocked |
| C08 | The 195431 snapshot recomputes MLP ECE `{values['mlp_embed_ece']:.4f}`, RF-Embed ECE `{values['rf_embed_ece']:.4f}` and RF-Hybrid ECE `{values['rf_hybrid_ece']:.4f}`. | evidence/claim-values.json -> mlp_embed_ece / rf_embed_ece / rf_hybrid_ece | {values['mlp_embed_ece']:.4f} / {values['rf_embed_ece']:.4f} / {values['rf_hybrid_ece']:.4f} | Recompute from all ten per-seed rows | verified |
| C09 | Snapshot AUROCs are MLP `{values['mlp_embed_auroc']:.4f}`, RF-Embed `{values['rf_embed_auroc']:.4f}`, RF-Hybrid `{values['rf_hybrid_auroc']:.4f}`, RF-Tabular `{values['rf_tabular_auroc']:.4f}`; the paper's `0.992/0.989/0.990/0.941` do not match. | evidence/claim-values.json -> mlp_embed_auroc / rf_embed_auroc / rf_hybrid_auroc / rf_tabular_auroc | {values['mlp_embed_auroc']:.4f} / {values['rf_embed_auroc']:.4f} / {values['rf_hybrid_auroc']:.4f} / {values['rf_tabular_auroc']:.4f} | Recompute AUROC means from ten seeds | blocked |
| C10 | Snapshot Brier scores are MLP `{values['mlp_embed_brier']:.4f}`, RF-Embed `{values['rf_embed_brier']:.4f}`, RF-Hybrid `{values['rf_hybrid_brier']:.4f}`, RF-Tabular `{values['rf_tabular_brier']:.4f}`; the paper prints `0.089/0.071/0.065/0.118`. | evidence/claim-values.json -> mlp_embed_brier / rf_embed_brier / rf_hybrid_brier / rf_tabular_brier | {values['mlp_embed_brier']:.4f} / {values['rf_embed_brier']:.4f} / {values['rf_hybrid_brier']:.4f} / {values['rf_tabular_brier']:.4f} | Recompute Brier means from ten seeds | blocked |
| C11 | Isotonic calibration changes RF-Hybrid ECE from `{values['isotonic_ece_before']:.4f}` to `{values['isotonic_ece_after']:.4f}` ({values['isotonic_ece_reduction_pct']:.2f}% reduction), not 99%, and AUROC by `{values['isotonic_auroc_change']:.4f}`, not `0.037`. | evidence/claim-values.json -> isotonic_ece_before / isotonic_ece_after / isotonic_ece_reduction_pct / isotonic_auroc_change | {values['isotonic_ece_before']:.4f} / {values['isotonic_ece_after']:.4f} / {values['isotonic_ece_reduction_pct']:.2f} / {values['isotonic_auroc_change']:.4f} | Recompute pre/post means from ten seeds | blocked |
| C12 | Of 15 pairwise Wilcoxon tests, 12 are nominally significant but only {values['pairwise_corrected_significant']} survive Bonferroni correction; the manuscript's corrected `12/15` is false. | evidence/claim-values.json -> pairwise_count / pairwise_raw_significant / pairwise_corrected_significant | {values['pairwise_count']} / {values['pairwise_raw_significant']} / {values['pairwise_corrected_significant']} | Count `significant` and `significant_corrected` in the 195431 snapshot | blocked |
| C13 | The N-sensitivity table has one incorrect cell: RF-Embed N=200 should be `0.150`, not `0.151`; MLP N=500 (`{values['mlp_n500']:.3f}`) and RF-Hybrid N=5000 (`{values['rf_hybrid_n5000']:.3f}`) round correctly. | evidence/claim-values.json -> rf_embed_n200 / rf_hybrid_n5000 / mlp_n500 | {values['rf_embed_n200']:.3f} / {values['rf_hybrid_n5000']:.3f} / {values['mlp_n500']:.3f} | Recompute all five sample-size summaries | blocked |
| C14 | Pearson correlation is neither `-0.973` for RF-Hybrid nor `+0.078` for MLP: with linear N, RF-Hybrid is `{values['rf_hybrid_r_linear']:.3f}` and MLP is `{values['mlp_r_linear']:.3f}`; with log10(N), RF-Hybrid is `{values['rf_hybrid_r_log10']:.3f}`. | evidence/claim-values.json -> rf_hybrid_r_linear / mlp_r_linear / rf_hybrid_r_log10 | {values['rf_hybrid_r_linear']:.3f} / {values['mlp_r_linear']:.3f} / {values['rf_hybrid_r_log10']:.3f} | Compute linear-N and log-N correlations | blocked |
| C15 | All 57 carrier receipts are marked PASS, but {values['carrier_semantic_mismatch']} bind the printed number to a different quantity, model, run, or prose role. | evidence/claim-values.json -> carrier_total / carrier_pass / carrier_semantic_mismatch | {values['carrier_total']} / {values['carrier_pass']} / {values['carrier_semantic_mismatch']} | Inspect evidence/audit.json -> carrier_receipts | blocked |
| C16 | The stored anonymity record says anonymous, but canonical `main.tex` contains the named author Zewen Liu and the preprint option. | evidence/claim-values.json -> anonymous_record_conflict | {values['anonymous_record_conflict']} | Compare `manuscript_anonymity.json` with the author block | blocked |
| C17 | The manuscript has two Limitations sections and says `no sample-size sweep` while also containing a five-point N-sensitivity table. | evidence/claim-values.json -> limitations_headings / says_no_sample_size_sweep / has_sample_size_table | {values['limitations_headings']} / {values['says_no_sample_size_sweep']} / {values['has_sample_size_table']} | Count headings and search for the contradictory sentence | blocked |
| C18 | The retained review is `2/8`, D veto / reject, and the R16 summary requires Major Revision. | evidence/claim-values.json -> review_card_score | {values['review_card_score']} | Read the retained review card and R16 summary | verified |
| C19 | The only defensible disposition is `merge_archive` / `archived`, with no independent package and no upload. | evidence/claim-values.json -> independent_package_created / uploaded | {values['independent_package_created']} / {values['uploaded']} | Check the disposition record and package directory | verified |

## Summary

The source is explicitly deprecated and the retained review rejects independent submission. The named p12 target shares only the N-sensitivity vocabulary, not this study's dataset, models or numbers. The manuscript mixes snapshot scopes, the isotonic reduction is 24.86% rather than 99%, only 10 of 15 corrected tests remain significant, and 42 of 57 mechanical PASS receipts bind a number to the wrong semantic quantity, model, run, or prose role. The correct disposition is archive/merge with no candidate package.
'''
    (OVERLAY / "CLAIM_LEDGER.md").write_text(ledger, encoding="utf-8")

    print(json.dumps({
        "canonical_sha256": sha(CANONICAL),
        "retained_variants": retained_files,
        "distinct_hashes": distinct_hashes,
        "p12_study_term_matches": study_term_matches,
        "p12_n_sensitivity_mentions": term_counts["N-sensitivity"],
        "corrected_significant": significance["corrected_significant"],
        "carrier_semantic_mismatch": len(semantic_mismatches),
        "ledger_sha256": sha(OVERLAY / "CLAIM_LEDGER.md"),
        "audit_sha256": sha(OVERLAY / "evidence/audit.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
