#!/usr/bin/env python3
"""Verify compact continuation receipts without claiming full paper reproduction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def check(name: str, expected, actual) -> dict:
    return {"check": name, "expected": expected, "actual": actual,
            "passed": expected == actual}


def canonical_sha256(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    root = args.root
    assets = json.loads((root / "public-assets.json").read_text(encoding="utf-8"))
    vision = json.loads((root / "vision-multimodel.json").read_text(encoding="utf-8"))
    toxicity = json.loads((root / "mechanistic-toxicity-dpo.json").read_text(encoding="utf-8"))
    d4rl = json.loads((root / "d4rl-multi-bc.json").read_text(encoding="utf-8"))
    linear_probe = json.loads((root / "tiny-imagenet-linear-probe.json").read_text(encoding="utf-8"))
    probe_matrix = json.loads((root / "tiny-imagenet-linear-probe-matrix.json").read_text(encoding="utf-8"))
    checkpoint_sync = json.loads((root / "full10-checkpoint-sync.json").read_text(encoding="utf-8"))
    gap_matrix = json.loads((root / "full10-gap-matrix.json").read_text(encoding="utf-8"))
    audit_verify = json.loads((root / "full10-audit-verification.json").read_text(encoding="utf-8"))
    smoke_dir = root / "magpie-simplejudge-smoke"
    smoke_text = (smoke_dir / "receipt.json").read_text(encoding="utf-8")
    smoke = json.loads(smoke_text)
    panel = json.loads((smoke_dir / "panel-readout.json").read_text(encoding="utf-8"))
    locked_panel = {"opencode-zen-free/deepseek-v4.1-flash-free",
                    "openrouter/recursive/flint-v1.0:free",
                    "openrouter/xingchen-agi/xing4.0-29b-a4b:free"}

    timm_states = {row["state"] for row in assets["timm"].values()}
    toxicity_states = {row["state"] for row in assets["toxicity_classifier"].values()}
    vision_models = {row["model"] for row in vision["models"] if row["status"] == "completed"}
    d4rl_paths = {row["path"] for row in d4rl["datasets"] if row["status"] == "completed"}
    checks = [
        check("assets_schema", "qone-full10-public-assets-v1", assets["schema"]),
        check("timm_download_states", True, timm_states <= {"downloaded", "present"}),
        check("timm_count", 3, len(assets["timm"])),
        check("toxicity_classifier_files", 6, len(assets["toxicity_classifier"])),
        check("toxicity_classifier_states", True,
              toxicity_states <= {"downloaded", "present"}),
        check("d4rl_cloud_direct_blocked", True, all(
            row.get("state") == "blocked" and "403" in row.get("error", "")
            for row in assets["d4rl"].values())),
        check("vision_schema", "qone-vision-multimodel-matrix-v1", vision["schema"]),
        check("vision_official", False, vision["official"]),
        check("vision_models", 4, len(vision_models)),
        check("vision_completed", 4, vision["completed"]),
        check("vision_blocked", 0, vision["blocked"]),
        check("vision_images", 2000, vision["images_per_model"]),
        check("vision_tiny_imagenet_sha",
              "6198c8ae015e2b3e007c7841da39ec069199b9aa3bfa943a462022fe5e43c821",
              vision["zip_sha256"]),
        check("toxicity_schema", "qone-mechanistic-toxicity-dpo-slice-v1", toxicity["schema"]),
        check("toxicity_official", False, toxicity["official"]),
        check("toxicity_rows", 128, toxicity["rows"]),
        check("toxicity_positive_samples", 128, toxicity["positive_samples_generated"]),
        check("toxicity_negative_samples", 128, toxicity["negative_samples_generated"]),
        check("toxicity_classifier_is_public_roberta", True,
              "unbiased-toxic-roberta" in toxicity["classifier"]),
        check("toxicity_dpo_not_paper_finetune", True,
              "not full paper DPO fine-tuning" in toxicity["note"]),
        check("toxicity_dpo_failure_diagnosed", True,
              toxicity["dpo"].get("enabled") is False
              and toxicity["dpo"].get("reason") == "non_finite_loss"
              and isinstance(toxicity["dpo"].get("first_loss"), (int, float))
              and toxicity["dpo"].get("steps") == 1),
        check("d4rl_schema", "qone-d4rl-multi-bc-v1", d4rl["schema"]),
        check("d4rl_official", False, d4rl["official"]),
        check("d4rl_completed", 5, d4rl["completed"]),
        check("d4rl_blocked", 0, d4rl["blocked"]),
        check("d4rl_no_rollout_claim", True,
              "no online rollout" in d4rl["note"]),
        check("d4rl_dataset_count", 5, len(d4rl_paths)),
        check("linear_probe_schema", "qone-tiny-imagenet-linear-probe-v1",
              linear_probe["schema"]),
        check("linear_probe_official", False, linear_probe["official"]),
        check("linear_probe_frozen_backbone", True,
              linear_probe["frozen_backbone"]),
        check("linear_probe_train_images", 10000,
              linear_probe["train_images"]),
        check("linear_probe_val_images", 2000, linear_probe["val_images"]),
        check("linear_probe_epochs", 3, linear_probe["epochs"]),
        check("linear_probe_trained", True,
              len(linear_probe["history"]) == 3
              and all(isinstance(row["val_accuracy"], (int, float))
                      for row in linear_probe["history"])),
        check("linear_probe_not_paper_claim", True,
              "not ImageNet-1K" in linear_probe["note"]),
        check("linear_probe_matrix_schema", "qone-tiny-imagenet-linear-probe-matrix-v1",
              probe_matrix["schema"]),
        check("linear_probe_matrix_official", False, probe_matrix["official"]),
        check("linear_probe_matrix_completed", 4, probe_matrix["completed"]),
        check("linear_probe_matrix_blocked", 0, probe_matrix["blocked"]),
        check("linear_probe_matrix_train_images", 5000,
              probe_matrix["train_images_per_model"]),
        check("linear_probe_matrix_val_images", 1000,
              probe_matrix["val_images_per_model"]),
        check("linear_probe_matrix_epochs", 2, probe_matrix["epochs"]),
        check("linear_probe_matrix_all_trained", True, all(
              row["status"] == "completed"
              and isinstance(row.get("final_val_accuracy"), (int, float))
              for row in probe_matrix["models"])),
        check("checkpoint_sync_tasks", 10, checkpoint_sync["summary"]["tasks"]),
        check("checkpoint_sync_problems", 0, checkpoint_sync["summary"]["problems"]),
        check("gap_matrix_total_leaves", 2776, gap_matrix["total_leaves"]),
        check("gap_matrix_blocked_leaves", 2751, gap_matrix["blocked_leaves"]),
        check("gap_matrix_promotions", 0, gap_matrix["summary"]["promoted_leaves"]),
        check("full10_audit_gate", "PASS", audit_verify["summary"]["gate"]),
        check("full10_audit_checks", 18, audit_verify["summary"]["checks"]),
        check("magpie_smoke_status", "PASS", smoke["status"]),
        check("magpie_smoke_official", False, smoke["official"]),
        check("magpie_smoke_panel", "free_magpie_parse", smoke["panel"]),
        check("magpie_smoke_judge_type", "simple", smoke["judge_type_actual"]),
        check("magpie_smoke_model_in_locked_panel", True, smoke["model"] in locked_panel),
        check("magpie_smoke_valid_score", True,
              smoke["valid_score"] is True and smoke["score"] in (0, 1)),
        check("magpie_smoke_paper_hash",
              "ca9eeeace43ce9cbe16db51cabb1417bd0d6ea7f65b5b63638ca0326b55865a7",
              smoke["paper_md_original_sha256"]),
        check("magpie_smoke_no_secret", True,
              not any(token in smoke_text for token in
                      ("api_key", "Authorization", "sk-proj", "Bearer "))),
        check("magpie_smoke_submission_manifest", 28,
              len(smoke["submission_sha256_manifest"])),
        check("magpie_smoke_real_data_present", True,
              "data/aqua_test.jsonl" in smoke["submission_sha256_manifest"]),
        check("magpie_panel_schema", "qone-magpie-simplejudge-panel-readout-v1",
              panel["schema"]),
        check("magpie_panel_official", False, panel["official"]),
        check("magpie_panel_scores_present", 2, panel["scores_present"]),
        check("magpie_panel_spread", 1.0, panel["spread"]),
        check("magpie_panel_decision", "BLOCKED", panel["decision"]),
        check("magpie_panel_no_promotion", 0, panel["promoted_leaves"]),
        check("magpie_panel_incompatible_model", "CHANNEL_INCOMPATIBLE",
              panel["models"][2]["status"]),
    ]
    report = {"checks": checks, "passed": all(row["passed"] for row in checks),
              "summary": {"gate": "PASS" if all(row["passed"] for row in checks) else "FAIL",
                          "checks": len(checks)}}
    if args.selftest:
        mutated = json.loads((root / "vision-multimodel.json").read_text(encoding="utf-8"))
        mutated["official"] = True
        checks_bad = [check("vision_official", False, mutated["official"])]
        mutated_smoke = json.loads(smoke_text)
        mutated_smoke["official"] = True
        mutated_smoke["judge_type_actual"] = "dummy"
        checks_bad += [check("magpie_smoke_official", False, mutated_smoke["official"]),
                       check("magpie_smoke_judge_type", "simple",
                             mutated_smoke["judge_type_actual"])]
        report["selftest"] = {"summary": {"passed": all(not row["passed"] for row in checks_bad),
                                           "direction": "official_and_dummy_mutation"}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(report["summary"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
