#!/usr/bin/env python3
"""Real open-model readout for Semantic Self-Consistency.

Generates genuine responses from a local HuggingFace causal LM, then applies the
same method set as the submission (top-prob / SC / CPW / SCW).

Everything here is honest about scope:
- the model is Qwen2.5-0.5B-Instruct, NOT the paper's GPT-3.5/Llama/Mistral/GPT-4o.
- prompt templates are the submission's k-shot templates, not the paper's exact text.
- embeddings default to the deterministic hash featurizer (offline); SciBERT/RoBERTa
  are opt-in via --embedder hf and require the weights to be present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_prompt(shot_prompt: str, question: str, options: list[str] | None = None) -> str:
    # AQuA is multiple-choice: the option letters must be in the prompt or the
    # model cannot emit a parseable letter answer.
    if options:
        body = "\n".join(options)
        return f"{shot_prompt}\n\nQuestion: {question}\n{body}\nA:"
    return f"{shot_prompt}\n\nQuestion: {question}\nA:"


def format_choice_prompt(question: str, options: list[str]) -> str:
    body = "\n".join(options)
    return (
        "Solve the multiple-choice question. End your reply with a final line of the form "
        "`The answer is X.` where X is a single letter from A to E.\n\n"
        f"Question: {question}\n{body}\nAnswer:"
    )


_FORMAT_LINE = (
    "Finish with exactly one line: `The answer is X.` "
    "Nothing after that line. Be concise (under 150 words)."
)


def instruction_prompt(name: str, question: str, options: list[str] | None = None) -> str:
    """Zero-shot, format-explicit prompt (no few-shot examples, no prefix to echo)."""
    if name == "aqua":
        body = "\n".join(options or [])
        return (
            "Answer this multiple-choice math question. Think briefly, then give the "
            "letter of the correct option (A, B, C, D or E).\n"
            f"{_FORMAT_LINE}\n\nQuestion: {question}\n{body}"
        )
    if name == "strategyqa":
        return (
            "Answer this yes/no commonsense question with True or False.\n"
            f"{_FORMAT_LINE}\n\nQuestion: {question}"
        )
    return (
        "Solve this elementary math word problem. Think step by step, then give the "
        "numeric answer only.\n"
        f"{_FORMAT_LINE}\n\nQuestion: {question}"
    )


# Fixed, hand-written exemplars (not from any benchmark row). Used only in
# `fewshot_replay` mode, as assistant turns, to teach the ending format.
REPLAY_EXEMPLARS = {
    "aqua": [
        ("Question: A box has 3 rows of 4 apples. How many apples?\nA) 7\nB) 12\nC) 14\nD) 16\nE) None",
         "3 * 4 = 12, which is option B.\nThe answer is B."),
        ("Question: A train covers 60 km in 45 minutes. Speed in km/h?\nA) 60\nB) 70\nC) 80\nD) 90\nE) None",
         "45 minutes = 0.75 h; 60 / 0.75 = 80.\nThe answer is C."),
        ("Question: What is 15% of 200?\nA) 15\nB) 20\nC) 30\nD) 35\nE) None",
         "0.15 * 200 = 30.\nThe answer is C."),
    ],
    "strategyqa": [
        ("Question: Could a candle burn underwater without any equipment?", "No, water removes the oxygen it needs.\nThe answer is False."),
        ("Question: Is a dog a mammal?", "Dogs give birth to live young and nurse them.\nThe answer is True."),
        ("Question: Can a bicycle have three wheels?", "Tricycles exist and are bicycles with three wheels.\nThe answer is True."),
    ],
    "svamp": [
        ("Question: Sam had 9 marbles and lost 4. How many remain?", "9 - 4 = 5.\nThe answer is 5."),
        ("Question: Six boxes hold 5 pens each. How many pens?", "6 * 5 = 30.\nThe answer is 30."),
        ("Question: A rope is 12 m long; 3 m is cut off. How long is it?", "12 - 3 = 9.\nThe answer is 9."),
    ],
}


def replay_messages(name: str, question: str, options: list[str] | None) -> list[dict]:
    if name == "aqua":
        body = "\n".join(options or [])
        ask = f"Question: {question}\n{body}"
    else:
        ask = f"Question: {question}"
    messages: list[dict] = []
    for q, a in REPLAY_EXEMPLARS[name]:
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": ask})
    return messages


_LETTER_TAG = re.compile(
    r"(?:the answer is|answer\s*[:=]|option|choice)\s*[\(\*\s]*([A-E])\b", re.IGNORECASE
)
_LETTER_BOX = re.compile(r"\\boxed\{\s*[\(\s]*([A-E])[\s\)]*\}")
_NUM_BOX = re.compile(r"\\boxed\{\s*(-?[\d.,]+)\s*\}")
_NUM_TAIL = re.compile(r"(?:the answer is|answer\s*[:=])\s*\$?(-?[\d.,]+)", re.IGNORECASE)
_TF = re.compile(
    r"(?:the answer is|answer\s*[:=])\s*\**\s*(true|false)\b", re.IGNORECASE
)
_TF_TAIL = re.compile(r"\b(true|false)\b[^.]*\.?\s*$", re.IGNORECASE)
_LAST_SENTENCE = re.compile(r"([A-Z][^.!?\n]{10,400}[.!?])\s*$")


def _squared_false_prefix(text: str) -> tuple[str | None, str]:
    """Small instruct models often open with the answer instead of closing with it.

    Only accepts a *leading* 'True.'/'False.' with a period, and only when the
    rest of the reply is non-empty (so an empty echo of the few-shot prefix does
    not count as an answer).
    """
    m = re.match(r"\s*\**\s*(true|false)\**\s*\.", text, re.IGNORECASE)
    if m and len(text.strip()) > len(m.group(0)) + 5:
        return m.group(1).lower(), "tf_leading"
    return None, "unparsed"


def extract_answer(text: str, kind: str) -> tuple[str | None, str]:
    """Tolerant extraction for real model output.

    Returns (answer, how). `how` records which rule fired so the report can show
    that most of the parse rate is not the paper's exact 'The answer is X' format.
    """
    if not text:
        return None, "empty"
    if kind == "aqua_rat":
        hits = _LETTER_TAG.findall(text) or _LETTER_BOX.findall(text)
        if hits:
            return hits[-1].upper(), "letter_tag"
        return None, "unparsed"
    if kind == "strategyqa":
        hits = _TF.findall(text)
        if hits:
            return hits[-1].lower(), "tf_tag"
        hits = _TF_TAIL.findall(text)
        if hits:
            return hits[-1].lower(), "tf_tail"
        lead, how = _squared_false_prefix(text)
        if lead:
            return lead, how
        return None, "unparsed"
    hits = _NUM_BOX.findall(text) or _NUM_TAIL.findall(text)
    if hits:
        return hits[-1].replace(",", "").rstrip("."), "num_tag"
    m = _LAST_SENTENCE.search(text)
    if m:
        nums = re.findall(r"(-?\d+(?:\.\d+)?)", m.group(1))
        if nums:
            return nums[-1], "num_last_sentence"
    return None, "unparsed"


def generate(model, tok, prompt: str, max_new_tokens: int, temperature: float, seed: int) -> str:
    return generate_messages(model, tok, [{"role": "user", "content": prompt}],
                             max_new_tokens, temperature, seed)


def generate_messages(model, tok, messages: list[dict], max_new_tokens: int,
                      temperature: float, seed: int) -> str:
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        device = "cuda"
    else:
        device = "cpu"
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok([text], return_tensors="pt").to(device)
    kwargs = dict(
        max_new_tokens=max_new_tokens,
        do_sample=temperature > 0,
        pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    if temperature > 0:
        kwargs.update(temperature=temperature, top_p=1.0)
    with torch.no_grad():
        out = model.generate(**inputs, **kwargs)
    gen = out[0][inputs["input_ids"].shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-root", type=Path, required=True)
    parser.add_argument("--model", default="/root/models/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--datasets", default="aqua,svamp,strategyqa")
    parser.add_argument("--limit", type=int, default=20, help="rows per dataset")
    parser.add_argument(
        "--max-tokens-override",
        type=int,
        default=0,
        help="if > 0, use this as max_new_tokens for every dataset (AQuA needs more)",
    )
    parser.add_argument("--k", type=int, default=5, help="SC samples (paper uses 10)")
    parser.add_argument(
        "--max-token-scale",
        type=float,
        default=2.0,
        help="multiplier on the submission's MAX_TOKENS; small models over-explain",
    )
    parser.add_argument(
        "--prompt-mode",
        choices=("fewshot", "instruction", "fewshot_replay"),
        default="fewshot",
        help=(
            "fewshot = submission's k-shot prompt (paper style, same as submission); "
            "instruction = zero-shot with an explicit output-format line. "
            "fewshot_replay = three fixed exemplars A/B/C injected as assistant turns, "
            "which keeps the paper's style but stops the model from echoing the prefix. "
            "Both are reported separately; fewshot carries prefix-contamination risk."
        ),
    )
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--progress-every", type=int, default=10,
                        help="print a progress line every N rows")
    parser.add_argument("--embedder", choices=("hash", "hf"), default="hash")
    parser.add_argument("--host-label", default="cloud")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.submission_root.resolve()
    sys.path.insert(0, str(root))
    from src.datasets import (  # noqa: E402
        AQUA_SHOT_PROMPT,
        MAX_TOKENS,
        STRATEGYQA_SHOT_PROMPT,
        SVAMP_SHOT_PROMPT,
        load_aqua_rat_test,
        load_strategyqa_test,
        load_svamp_full,
    )
    from src import methods as M  # noqa: E402

    # AQuA rows carry options; the submission's loader drops them, so read them
    # straight from the verified file for prompt construction only.
    aqua_raw = [
        json.loads(line)
        for line in (root / "data" / "aqua_test.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    aqua_options = [row["options"] for row in aqua_raw]

    os.environ["HF_HUB_OFFLINE"] = "0" if args.embedder == "hf" else "1"

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.model)
    dtype = "float16"
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=dtype, device_map="auto"
    )
    model.eval()

    wanted = [d.strip() for d in args.datasets.split(",") if d.strip()]
    loaders = {
        "aqua": (load_aqua_rat_test, AQUA_SHOT_PROMPT, "aqua_rat", 0),
        "svamp": (load_svamp_full, SVAMP_SHOT_PROMPT, "svamp", 0),
        "strategyqa": (load_strategyqa_test, STRATEGYQA_SHOT_PROMPT, "strategyqa", 0),
    }
    start = time.monotonic()
    results: dict[str, dict] = {}
    raw_records: list[dict] = []
    checkpoint_path: Path | None = None

    for name in wanted:
        loader, shot, tok_key, offset = loaders[name]
        rows = loader()
        subset = rows[offset: offset + args.limit]
        correct_top = correct_sc_tie_first = correct_cpw = correct_scw = parsed_sc = 0
        sample_answers: list[str | None] = []
        extract_how: dict[str, int] = {}
        checkpoint_path = args.output.parent / f"checkpoint-{name}.jsonl"
        for i, row in enumerate(subset):
            q = row["question"]
            gold = str(row["correct"]).strip().lower()
            opts = aqua_options[offset + i] if name == "aqua" else None
            if args.prompt_mode == "instruction":
                prompt, msgs = instruction_prompt(name, q, opts), None
            elif args.prompt_mode == "fewshot_replay":
                prompt, msgs = replay_messages(name, q, opts), "replay"
            else:
                prompt = build_prompt(shot, q, opts)
                msgs = None
            mt = int(MAX_TOKENS[tok_key] * args.max_token_scale)
            if args.max_tokens_override:
                mt = args.max_tokens_override
            def run(temp: float, seed: int) -> str:
                if msgs == "replay":
                    return generate_messages(model, tok, prompt, mt, temp, seed)
                return generate(model, tok, prompt, mt, temp, seed)

            greedy = run(0.0, args.seed + i)
            samples = [run(0.8, args.seed * 1000 + i * 10 + j) for j in range(args.k)]
            g_ans, g_how = extract_answer(greedy, tok_key)
            extract_how[f"greedy:{g_how}"] = extract_how.get(f"greedy:{g_how}", 0) + 1
            parsed = [extract_answer(s, tok_key) for s in samples]
            s_ans = [a for a, _ in parsed]
            for _, how in parsed:
                extract_how[how] = extract_how.get(how, 0) + 1
            parsed_sc += sum(1 for a in s_ans if a is not None)
            sc = M.modal_answer(s_ans)
            cpw = M.cpw_answer(samples, None, tok_key if tok_key != "aqua_rat" else "scibert")
            scw = M.scw_answer(samples, None, tok_key if tok_key != "aqua_rat" else "scibert")

            def norm(x):
                return None if x is None else str(x).strip().lower().rstrip(".")

            correct_top += int(norm(g_ans) == gold)
            correct_sc_tie_first += int(norm(sc) == gold)
            correct_cpw += int(norm(cpw) == gold)
            correct_scw += int(norm(scw) == gold)
            raw_records.append({
                "dataset": name,
                "index": offset + i,
                "question": q,
                "gold": gold,
                "greedy": greedy,
                "samples": samples,
                "top_prob_answer": g_ans,
                "sc_answer": sc,
                "cpw_answer": cpw,
                "scw_answer": scw,
            })
            sample_answers.append(sc)
            if (i + 1) % args.progress_every == 0:
                print(f"[{name}] progress {i + 1}/{len(subset)}", flush=True)
            checkpoint_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False)
                          for r in raw_records if r["dataset"] == name) + "\n",
                encoding="utf-8",
            )

        n = len(subset)
        results[name] = {
            "rows": n,
            "k": args.k,
            "accuracy_top_prob": correct_top / n if n else 0.0,
            "accuracy_sc": correct_sc_tie_first / n if n else 0.0,
            "accuracy_cpw": correct_cpw / n if n else 0.0,
            "accuracy_scw": correct_scw / n if n else 0.0,
            "parse_rate_sc": parsed_sc / (n * args.k) if n else 0.0,
            "extract_rules": extract_how,
        }
        print(f"[{name}] n={n} " + json.dumps(results[name]), flush=True)

    elapsed = time.monotonic() - start
    summary = {
        "host_label": args.host_label,
        "model": args.model,
        "model_family": "Qwen2.5-0.5B-Instruct (open, NOT the paper's models)",
        "embedder": args.embedder,
        "prompt_mode": args.prompt_mode,
        "datasets": results,
        "k": args.k,
        "seed": args.seed,
        "limit_per_dataset": args.limit,
        "elapsed_seconds": round(elapsed, 2),
        "note": (
            "Accuracy here is a real open-model readout on a subset, using the "
            "submission's k-shot prompts. It is not comparable to the paper's reported "
            "numbers for GPT-3.5/Llama/Mistral/GPT-4o-mini."
        ),
    }
    summary["canonical_sha256"] = canonical_sha256(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raw_path = args.output.with_suffix(".raw.jsonl")
    raw_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in raw_records) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({len(raw_records)} records) in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
