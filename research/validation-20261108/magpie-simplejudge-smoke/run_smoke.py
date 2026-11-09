"""Single-leaf SimpleJudge smoke through the local Magpie free gateway (official=false).

Run with the PaperBench uv environment:
  cd /tmp/paperbench-upstream/project/paperbench
  GRADER_OPENAI_API_KEY=... OPENAI_BASE_URL=http://127.0.0.1:3425/v1 \
    uv run python /path/to/run_smoke.py --model <id>
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path

PAPER_DIR = Path("/tmp/paperbench-upstream/project/paperbench/data/papers/semantic-self-consistency")
REPO = Path("/home/liuzewen/qone-life-work")
SUBMISSION = REPO / "research/paperbench-submissions/semantic-self-consistency"
OUT = REPO / "research/validation-20261108/magpie-simplejudge-smoke"
LEAF_ID = "43f23e0e-2c5b-4a2b-80ab-6cc9c62723f1"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def amain(model: str, max_tokens: int, paper_chars: int) -> dict:
    from preparedness_turn_completer import utils as tc_utils
    from preparedness_turn_completer.oai_completions_turn_completer import (
        OpenAICompletionsTurnCompleter,
    )
    from preparedness_turn_completer.utils import RetryConfig
    from paperbench.judge.simple import (
        ParsedJudgeResponseFloat,
        ParsedJudgeResponseInt,
        SimpleJudge,
    )
    from paperbench.rubric.tasks import TaskNode

    tc_utils.CONTEXT_WINDOW_LENGTHS[model] = 32768

    rubric = TaskNode.from_dict(json.loads((PAPER_DIR / "rubric.json").read_text()))

    def find(node):
        if node.id == LEAF_ID:
            return node
        for child in node.sub_tasks:
            found = find(child)
            if found:
                return found
        return None

    leaf = find(rubric)
    assert leaf is not None and leaf.is_leaf(), "leaf not found"

    paper_full = (PAPER_DIR / "paper.md").read_text()
    paper_md_path = OUT / "paper-truncated.md"
    paper_md_path.write_text(paper_full[:paper_chars])

    retry = RetryConfig(wait_min=2, wait_max=10, stop_after=240)
    main_cfg = OpenAICompletionsTurnCompleter.Config(model=model, max_tokens=max_tokens, retry_config=retry)
    int_cfg = OpenAICompletionsTurnCompleter.Config(
        model=model,
        response_format=ParsedJudgeResponseInt,
        max_tokens=max(512, max_tokens // 2),
        retry_config=retry,
    )
    float_cfg = OpenAICompletionsTurnCompleter.Config(
        model=model,
        response_format=ParsedJudgeResponseFloat,
        max_tokens=max(512, max_tokens // 2),
        retry_config=retry,
    )

    judge = SimpleJudge(
        paper_path=PAPER_DIR / "paper.pdf",
        rubric=rubric,
        addendum=(PAPER_DIR / "addendum.md").read_text(),
        judge_addendum=(PAPER_DIR / "judge.addendum.md").read_text(),
        submission_dir=SUBMISSION,
        paper_md=paper_md_path,
        completer_config=main_cfg,
        int_completer_config=int_cfg,
        float_completer_config=float_cfg,
        code_only=True,
    )

    receipt = {
        "smoke_id": "magpie-simplejudge-single-leaf-20261108",
        "official": False,
        "panel": "free_magpie_parse",
        "judge_type_expected": "simple",
        "model": model,
        "task_id": "semantic-self-consistency",
        "leaf_id": LEAF_ID,
        "leaf_requirements": leaf.requirements,
        "paper_md_original_sha256": hashlib.sha256(paper_full.encode()).hexdigest(),
        "paper_md_truncated_chars": paper_chars,
        "submission_dir": str(SUBMISSION),
        "submission_sha256_manifest": {},
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for path in sorted(SUBMISSION.rglob("*")):
        if path.is_file():
            receipt["submission_sha256_manifest"][str(path.relative_to(SUBMISSION))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

    t0 = time.monotonic()
    await judge.before_grading()
    receipt["before_grading_s"] = round(time.monotonic() - t0, 2)
    receipt["judge_type_actual"] = judge.judge_type
    log(f"before_grading done in {receipt['before_grading_s']}s")

    t1 = time.monotonic()
    await judge._construct_grade_leaf_messages(leaf)
    receipt["file_selection_s"] = round(time.monotonic() - t1, 2)
    log(f"file selection + prompt build done in {receipt['file_selection_s']}s")

    t2 = time.monotonic()
    graded = await judge.grade_leaf(leaf)
    receipt["grade_leaf_s"] = round(time.monotonic() - t2, 2)
    receipt["score"] = graded.score
    receipt["valid_score"] = graded.valid_score
    receipt["explanation"] = graded.explanation
    meta = graded.judge_metadata or {}
    receipt["full_judge_response"] = meta.get("full_judge_response")
    receipt["token_usage"] = meta.get("token_usage")
    receipt["status"] = "PASS" if graded.valid_score else "INVALID_SCORE"
    log(f"grade_leaf done in {receipt['grade_leaf_s']}s status={receipt['status']}")
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--paper-chars", type=int, default=16000)
    ap.add_argument("--wall-clock-s", type=int, default=1800)
    ap.add_argument("--out-name", default="receipt.json")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    receipt: dict
    try:
        receipt = asyncio.run(asyncio.wait_for(amain(args.model, args.max_tokens, args.paper_chars), args.wall_clock_s))
    except Exception as exc:  # noqa: BLE001
        receipt = {
            "smoke_id": "magpie-simplejudge-single-leaf-20261108",
            "official": False,
            "panel": "free_magpie_parse",
            "model": args.model,
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    receipt["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    text = json.dumps(receipt, ensure_ascii=False, indent=2)
    for var in ("OPENAI_API_KEY", "GRADER_OPENAI_API_KEY"):
        secret = os.environ.get(var, "")
        if secret and secret in text:
            raise SystemExit(f"refusing to write receipt: {var} value detected")
    (OUT / args.out_name).write_text(text + "\n")
    print(json.dumps({k: receipt.get(k) for k in ("status", "model", "judge_type_actual", "score", "valid_score", "grade_leaf_s", "error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
