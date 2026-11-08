#!/usr/bin/env python3
"""Gate for the full 10-task PaperBench reproduction program.

PASS requires every one of the 2776 leaves to be `verified` or
`out_of_scope_waived`, every task to have an asset manifest and panel receipt,
three locked free judge models with per-model GO, no dummy scores, and no
secret-shaped literals in tracked evidence files.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_NOT_EXECUTED = 3
EXIT_BLOCKED = 4
EXPECTED_LEAVES = 2776
EXPECTED_TASKS = 10
SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9_.-]{12,}|"
    r"(?:GRADER_OPENAI_API_KEY|OPENAI_API_KEY)\s*[:=]\s*['\"][^'\"]{12,}['\"]",
    re.IGNORECASE,
)


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def check(name: str, expected, actual) -> dict:
    return {"check": name, "expected": expected, "actual": actual, "passed": expected == actual}


def verify(root: Path) -> dict:
    problems: list[str] = []
    ledger_path = root / "leaf-ledger.json"
    if not ledger_path.is_file():
        return {"checks": [check("leaf_ledger_exists", True, False)],
                "problems": ["leaf_ledger_missing"], "summary": {"gate": "NOT_EXECUTED"}}
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    body = {k: v for k, v in ledger.items() if k != "canonical_sha256"}
    if ledger.get("canonical_sha256") != canonical_sha256(body):
        problems.append("ledger_canonical_mismatch")

    leaves = ledger.get("leaves") or []
    tasks = ledger.get("tasks") or []
    states = {}
    for leaf in leaves:
        states[leaf.get("terminal_state")] = states.get(leaf.get("terminal_state"), 0) + 1
        if leaf.get("terminal_state") == "verified":
            if not leaf.get("carrier_paths") or not leaf.get("carrier_sha256"):
                problems.append(f"verified_without_carrier:{leaf.get('leaf_id')}")
            if not leaf.get("recompute_command"):
                problems.append(f"verified_without_recompute:{leaf.get('leaf_id')}")
            if len(leaf.get("judge_scores") or {}) != 3:
                problems.append(f"verified_without_three_judges:{leaf.get('leaf_id')}")
        elif leaf.get("terminal_state") == "out_of_scope_waived":
            waiver = leaf.get("waiver") or {}
            if not waiver.get("addendum_path") or not waiver.get("quote") or not waiver.get("sha256"):
                problems.append(f"waiver_without_citation:{leaf.get('leaf_id')}")
        elif leaf.get("terminal_state") == "blocked":
            if not leaf.get("blocked_reason"):
                problems.append(f"blocked_without_reason:{leaf.get('leaf_id')}")
        else:
            problems.append(f"nonterminal_state:{leaf.get('leaf_id')}:{leaf.get('terminal_state')}")

    panel = ledger.get("panel") or {}
    if panel.get("official") is not False or panel.get("judge_type") != "free_multimodel":
        problems.append("panel_not_free_multimodel")
    model_ids = panel.get("model_ids") or []
    if len(model_ids) != 3 or not panel.get("locked"):
        problems.append("panel_not_locked_to_three_models")
    go = panel.get("user_go") or {}
    for model_id in model_ids:
        if go.get(model_id, {}).get("go") is not True:
            problems.append(f"missing_user_go:{model_id}")

    for task in tasks:
        task_id = task.get("task_id") or ""
        task_root = root / "tasks" / task_id
        asset_manifest = task.get("asset_manifest")
        if asset_manifest:
            candidate = Path(asset_manifest)
            asset_path = candidate if candidate.is_absolute() else root / candidate
        else:
            asset_path = task_root / "ASSETS.json"
        if not asset_path.is_file():
            problems.append(f"missing_asset_manifest:{task_id}")
        checkpoint = task.get("checkpoint")
        if checkpoint:
            candidate = Path(checkpoint)
            checkpoint_path = candidate if candidate.is_absolute() else root / candidate
        else:
            checkpoint_path = task_root / "CHECKPOINT.json"
        if not checkpoint_path.is_file():
            problems.append(f"missing_checkpoint:{task_id}")
        receipt_path = task_root / "panel-receipt.json"
        if not receipt_path.is_file():
            problems.append(f"missing_panel_receipt:{task_id}")
        else:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("judge_type") != "free_multimodel" or receipt.get("official") is not False:
                problems.append(f"receipt_not_free:{task_id}")
            if not receipt.get("complete") or len(receipt.get("model_ids") or []) != 3:
                problems.append(f"receipt_incomplete:{task_id}")
            if receipt.get("model_ids") != model_ids:
                problems.append(f"receipt_panel_mismatch:{task_id}")

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in {".json", ".jsonl", ".md", ".txt", ".log", ".py", ".sh"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_PATTERN.search(text) and "PLACEHOLDER" not in text.upper():
            problems.append(f"secret_shaped_literal:{path.relative_to(root)}")

    checks = [
        check("leaf_count", EXPECTED_LEAVES, len(leaves)),
        check("task_count", EXPECTED_TASKS, len(tasks)),
        check("verified_leaves", EXPECTED_LEAVES, states.get("verified", 0) + states.get("out_of_scope_waived", 0)),
        check("blocked_leaves", 0, states.get("blocked", 0)),
        check("unverified_leaves", 0, sum(v for k, v in states.items() if k != "verified" and k != "out_of_scope_waived")),
        check("panel_models", 3, len(model_ids)),
        check("panel_official", False, panel.get("official")),
        check("problems", 0, len(problems)),
    ]
    passed = all(row["passed"] for row in checks) and not problems
    blocked = (not passed and states.get("blocked", 0) > 0
               and sum(value for key, value in states.items() if key not in {"blocked", "verified", "out_of_scope_waived"}) == 0
               and all(not problem.startswith("nonterminal_state:") for problem in problems))
    return {
        "checks": checks,
        "problems": problems,
        "state_counts": states,
        "summary": {
            "gate": "PASS" if passed else ("BLOCKED" if blocked else "FAIL"),
            "passed": passed,
            "blocked": blocked,
        },
    }


def selftest(root: Path) -> dict:
    ledger_path = root / "leaf-ledger.json"
    original = json.loads(ledger_path.read_text(encoding="utf-8"))

    direction_a = copy.deepcopy(original)
    direction_a["leaves"] = direction_a["leaves"][:-1]
    direction_a["canonical_sha256"] = canonical_sha256(
        {k: v for k, v in direction_a.items() if k != "canonical_sha256"})
    a_path = root / "leaf-ledger.selftest-a.json"
    a_path.write_text(json.dumps(direction_a, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_root = root / "selftest-a"
    temp_root.mkdir(exist_ok=True)
    (temp_root / "leaf-ledger.json").write_text(json.dumps(direction_a, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    a = verify(temp_root)
    a_path.unlink()

    direction_b = copy.deepcopy(original)
    direction_b["panel"]["official"] = True
    direction_b["canonical_sha256"] = canonical_sha256(
        {k: v for k, v in direction_b.items() if k != "canonical_sha256"})
    temp_root_b = root / "selftest-b"
    temp_root_b.mkdir(exist_ok=True)
    (temp_root_b / "leaf-ledger.json").write_text(json.dumps(direction_b, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    b = verify(temp_root_b)
    restored = verify(root)
    return {
        "summary": {
            "passed": (not a["summary"]["passed"]) and (not b["summary"]["passed"]),
            "direction_a_problems": len(a["problems"]) + sum(not c["passed"] for c in a["checks"]),
            "direction_b_problems": len(b["problems"]) + sum(not c["passed"] for c in b["checks"]),
            "restored_problems": len(restored["problems"]) + sum(not c["passed"] for c in restored["checks"]),
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not args.root.is_dir():
        print("NOT_EXECUTED: missing root", args.root)
        return EXIT_NOT_EXECUTED
    report = verify(args.root)
    if args.selftest:
        report["selftest"] = selftest(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(report["summary"]))
    if report["summary"].get("passed"):
        return EXIT_OK
    if report["summary"].get("blocked"):
        return EXIT_BLOCKED
    return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
