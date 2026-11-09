#!/usr/bin/env python3
"""Promote narrow full10 leaves only when receipts and free judge agree.

This script never edits the original ledger. It writes a promoted copy and a
deterministic promotion receipt so a failed batch leaves zero partial scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_MODELS = (
    "opencode-zen-free/deepseek-v4.1-flash-free",
    "openrouter/recursive/flint-v1.0:free",
    "openrouter/xingchen-agi/xing4.0-29b-a4b:free",
)


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--min-mean-score", type=float, default=0.8)
    parser.add_argument("--max-score-spread", type=float, default=0.25)
    args = parser.parse_args()

    ledger_path = args.root / "leaf-ledger.json"
    ledger = load_json(ledger_path)
    batch = load_json(args.batch)
    receipt = load_json(args.receipt)
    leaves = {leaf["leaf_id"]: leaf for leaf in ledger["leaves"]}
    by_key = {}
    for row in receipt.get("results", []):
        by_key[(row.get("leaf_id"), row.get("model_id"))] = row

    promotions = []
    blocked = []
    for request in batch["leaves"]:
        leaf_id = request["leaf_id"]
        leaf = leaves.get(leaf_id)
        if leaf is None:
            blocked.append({"leaf_id": leaf_id, "reason": "unknown_leaf_id"})
            continue
        scores = {}
        for model_id in EXPECTED_MODELS:
            row = by_key.get((leaf_id, model_id), {})
            if row.get("status") != "scored" or not isinstance(row.get("score"), (int, float)):
                blocked.append({"leaf_id": leaf_id, "reason": f"missing_judge:{model_id}"})
                break
            scores[model_id] = float(row["score"])
        if len(scores) != 3:
            continue
        spread = max(scores.values()) - min(scores.values())
        mean = sum(scores.values()) / len(scores)
        if receipt.get("complete") is not True or receipt.get("official") is not False \
                or receipt.get("judge_type") != "free_multimodel" \
                or tuple(receipt.get("model_ids") or ()) != EXPECTED_MODELS:
            blocked.append({"leaf_id": leaf_id, "reason": "panel_contract_invalid"})
            continue
        if spread > args.max_score_spread or mean < args.min_mean_score:
            blocked.append({"leaf_id": leaf_id, "reason": "judge_spread_or_mean",
                            "scores": scores, "spread": spread, "mean": mean})
            continue
        carrier_paths = request["carrier_paths"]
        carrier_sha256 = []
        missing = []
        for relative in carrier_paths:
            path = Path(relative)
            if not path.is_absolute():
                path = args.root.parent / relative
            if not path.is_file():
                missing.append(relative)
            else:
                carrier_sha256.append(sha256_file(path))
        if missing:
            blocked.append({"leaf_id": leaf_id, "reason": "missing_carriers",
                            "carriers": missing})
            continue
        leaf["terminal_state"] = "verified"
        leaf["carrier_paths"] = carrier_paths
        leaf["carrier_sha256"] = carrier_sha256
        leaf["recompute_command"] = request["recompute_command"]
        leaf["judge_scores"] = scores
        leaf["waiver"] = {}
        leaf["blocked_reason"] = ""
        leaf["judge_panel_receipt"] = str(args.receipt.relative_to(args.root))
        leaf["judge_panel_complete"] = True
        promotions.append({"leaf_id": leaf_id, "scores": scores,
                           "spread": spread, "mean": mean})

    if blocked:
        report = {"schema": "qone-full10-promotion-v1", "status": "BLOCKED",
                  "promotions": 0, "blocked": blocked,
                  "note": "No ledger copy written; no partial scores published."}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(json.dumps(report["status"]))
        return 4

    states = {}
    for leaf in ledger["leaves"]:
        states[leaf["terminal_state"]] = states.get(leaf["terminal_state"], 0) + 1
    ledger["summary"] = {
        "total_leaves": len(ledger["leaves"]),
        "verified": states.get("verified", 0),
        "out_of_scope_waived": states.get("out_of_scope_waived", 0),
        "blocked": states.get("blocked", 0),
        "unverified": states.get("unverified", 0),
        "gate": "BLOCKED",
    }
    body = {key: value for key, value in ledger.items() if key != "canonical_sha256"}
    ledger["canonical_sha256"] = canonical_sha256(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    report = {"schema": "qone-full10-promotion-v1", "status": "PROMOTED",
              "promotions": len(promotions), "details": promotions,
              "blocked": [], "output": str(args.output),
              "ledger_sha256": ledger["canonical_sha256"],
              "note": "Apply this copy to leaf-ledger.json only after all other gates pass."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": report["status"], "promotions": len(promotions)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
