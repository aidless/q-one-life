#!/usr/bin/env python3
"""Real RTP toxicity scoring, steering-style pairs, and a bounded DPO slice.

This is an open-model experiment slice. It is deliberately not a claim that the
paper's GPT-2 DPO recipe, Wikitext-2 prompts, or published tables are reproduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_prompts(path: Path, limit: int) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            prompt = row.get("prompt")
            text = prompt.get("text") if isinstance(prompt, dict) else prompt
            if text:
                rows.append({"text": str(text), "challenging": str(row.get("challenging", ""))})
            if len(rows) >= limit:
                break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lm", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--rtp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--max-new-tokens", type=int, default=20)
    parser.add_argument("--dpo-steps", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

    started = time.monotonic()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = args.device
    lm_tokenizer = AutoTokenizer.from_pretrained(str(args.lm))
    lm_tokenizer.pad_token = lm_tokenizer.eos_token
    lm = AutoModelForCausalLM.from_pretrained(str(args.lm), torch_dtype="float16")
    lm.to(device)
    lm.eval()
    classifier_tokenizer = AutoTokenizer.from_pretrained(str(args.classifier))
    classifier = AutoModelForSequenceClassification.from_pretrained(
        str(args.classifier), torch_dtype="float16")
    classifier.to(device)
    classifier.eval()
    labels = list(classifier.config.id2label.values())
    toxicity_index = labels.index("toxicity") if "toxicity" in labels else 0

    prompts = load_prompts(args.rtp, args.limit)
    toxic_ids_by_name = {}
    for word in ("shit", "fuck", "damn", "hate", "idiot"):
        ids = lm_tokenizer.encode(" " + word, add_special_tokens=False)
        if ids:
            toxic_ids_by_name[word] = ids[:3]

    def toxicity_score(text: str) -> float:
        encoded = classifier_tokenizer(text, return_tensors="pt", truncation=True,
                                       max_length=256).to(device)
        with torch.no_grad():
            logits = classifier(**encoded).logits.float().cpu()[0]
        value = float(torch.sigmoid(logits[toxicity_index]))
        return value

    def generate(prompt: str, seed: int, toxic_bias: float = 0.0) -> tuple[str, float]:
        torch.manual_seed(seed)
        encoded = lm_tokenizer(prompt, return_tensors="pt").to(device)
        generated = encoded["input_ids"]
        past = None
        for _ in range(args.max_new_tokens):
            with torch.no_grad():
                outputs = lm(input_ids=generated if past is None else generated[:, -1:],
                             past_key_values=past, use_cache=True)
                logits = outputs.logits[0, -1].float()
                past = outputs.past_key_values
                if toxic_bias:
                    for ids in toxic_ids_by_name.values():
                        logits[ids] += toxic_bias
                probabilities = torch.softmax(logits, dim=-1)
                next_id = int(torch.multinomial(probabilities, num_samples=1))
            generated = torch.cat([generated, torch.tensor([[next_id]], device=device)], dim=1)
            if next_id == lm_tokenizer.eos_token_id:
                break
        continuation = lm_tokenizer.decode(generated[0, encoded["input_ids"].shape[1]:],
                                            skip_special_tokens=True).strip()
        return continuation, toxicity_score(prompt + " " + continuation)

    rows = []
    for index, prompt in enumerate(prompts):
        positive, positive_score = generate(prompt["text"], args.seed + index, 0.0)
        negative, negative_score = generate(prompt["text"], args.seed + 100000 + index, 3.0)
        rows.append({
            "index": index,
            "prompt": prompt["text"],
            "challenging": prompt["challenging"],
            "positive": positive,
            "negative": negative,
            "positive_toxicity": positive_score,
            "negative_toxicity": negative_score,
            "toxicity_delta": negative_score - positive_score,
        })
        if (index + 1) % 16 == 0:
            print(json.dumps({"done": index + 1, "total": len(prompts),
                              "elapsed_s": round(time.monotonic() - started, 1)}), flush=True)

    valid_pairs = [row for row in rows
                   if row["negative_toxicity"] > row["positive_toxicity"] + 0.05]
    dpo = {"enabled": False, "steps": 0, "pairs_used": 0,
           "reason": "no_eligible_pairs" if not valid_pairs else ""}
    if valid_pairs and args.dpo_steps > 0:
        lm.eval()
        optimizer = torch.optim.AdamW(lm.parameters(), lr=1e-6)
        pair_order = list(valid_pairs)
        random.Random(args.seed).shuffle(pair_order)
        losses = []
        for step in range(args.dpo_steps):
            batch = pair_order[:min(args.batch_size, len(pair_order))]
            chosen_texts = [row["prompt"] + " " + row["positive"] for row in batch]
            rejected_texts = [row["prompt"] + " " + row["negative"] for row in batch]
            encoded_chosen = lm_tokenizer(chosen_texts, return_tensors="pt", padding=True,
                                          truncation=True, max_length=128).to(device)
            encoded_rejected = lm_tokenizer(rejected_texts, return_tensors="pt", padding=True,
                                            truncation=True, max_length=128).to(device)
            with torch.no_grad():
                reference_chosen = lm(**encoded_chosen).logits.float().log_softmax(dim=-1)
                reference_rejected = lm(**encoded_rejected).logits.float().log_softmax(dim=-1)
            policy_chosen = lm(**encoded_chosen).logits.float().log_softmax(dim=-1)
            policy_rejected = lm(**encoded_rejected).logits.float().log_softmax(dim=-1)
            chosen_gain = (policy_chosen - reference_chosen).sum(dim=-1).mean()
            rejected_gain = (policy_rejected - reference_rejected).sum(dim=-1).mean()
            loss = -torch.nn.functional.logsigmoid(0.1 * (chosen_gain - rejected_gain))
            losses.append(float(loss.detach().float().cpu()))
            if not bool(torch.isfinite(loss)):
                dpo = {"enabled": False, "steps": len(losses), "pairs_used": len(valid_pairs),
                       "reason": "non_finite_loss", "first_loss": losses[0], "last_loss": losses[-1],
                       "note": "Training stopped at first non-finite loss; no DPO claim is made."}
                break
            optimizer.zero_grad()
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(lm.parameters(), 10.0)
            if not bool(torch.isfinite(grad_norm)):
                dpo = {"enabled": False, "steps": len(losses), "pairs_used": len(valid_pairs),
                       "reason": "non_finite_gradient", "first_loss": losses[0], "last_loss": losses[-1],
                       "note": "Training stopped at first non-finite gradient; no DPO claim is made."}
                break
            optimizer.step()
        if not dpo.get("reason"):
            dpo = {"enabled": True, "steps": len(losses), "pairs_used": len(valid_pairs),
                   "beta": 0.1, "learning_rate": 1e-6, "max_grad_norm": 10.0,
                   "batch_size": min(args.batch_size, len(valid_pairs)),
                   "first_loss": losses[0], "last_loss": losses[-1],
                   "loss_reduced": losses[-1] < losses[0],
                   "note": "Bounded in-process slice; reference logits are read before each optimizer step, not the paper's full DPO training."}
        lm.eval()

    mean_positive = float(np.mean([row["positive_toxicity"] for row in rows]))
    mean_negative = float(np.mean([row["negative_toxicity"] for row in rows]))
    receipt = {
        "schema": "qone-mechanistic-toxicity-dpo-slice-v1",
        "official": False,
        "lm": str(args.lm),
        "classifier": str(args.classifier),
        "classifier_labels": labels,
        "rtp": str(args.rtp),
        "rtp_sha256": sha256_file(args.rtp),
        "rows": len(rows),
        "max_new_tokens": args.max_new_tokens,
        "seed": args.seed,
        "device": device,
        "positive_samples_generated": sum(bool(row["positive"]) for row in rows),
        "negative_samples_generated": sum(bool(row["negative"]) for row in rows),
        "pairs_with_negative_more_toxic": len(valid_pairs),
        "mean_positive_toxicity": mean_positive,
        "mean_negative_toxicity": mean_negative,
        "mean_toxicity_delta": mean_negative - mean_positive,
        "dpo": dpo,
        "rows_detail": rows,
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": ("Real GPT-2-medium and unbiased-toxic-roberta on public RealToxicityPrompts; "
                 "PPLM-style toxic-token bias is not the paper's PPLM implementation and "
                 "the bounded DPO slice is not full paper DPO fine-tuning."),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in receipt if key != "rows_detail"}, indent=1),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
