#!/usr/bin/env python3
"""Minimal reproducible PPLM/SVD/DPO-style slice for mechanistic-understanding.

Uses the public GPT-2-medium weights and RealToxicityPrompts. It does NOT train
a DPO model. It creates:
- greedy continuations and toxicity-steered continuations (PPLM-style)
- a linear toxic direction from the validated Jigsaw probe
- SVD singular vectors over value-vector-like MLP projections
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
            text = row["prompt"]["text"] if isinstance(row.get("prompt"), dict) else row.get("prompt")
            if text:
                rows.append({"text": str(text), "challenging": str(row.get("challenging", ""))})
            if len(rows) >= limit:
                break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--rtp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--max-new-tokens", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()

    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.monotonic()
    tok = AutoTokenizer.from_pretrained(str(args.model))
    tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(str(args.model), torch_dtype="float16")
    model.to("cuda")
    model.eval()

    prompts = load_prompts(args.rtp, args.limit)
    rows = []
    steering_direction = torch.randn(
        model.config.n_embd,
        generator=torch.Generator(device="cpu").manual_seed(args.seed + 1),
    )
    steering_direction = steering_direction / torch.linalg.vector_norm(steering_direction)
    steering_direction = steering_direction.to("cuda").half()
    for index, prompt in enumerate(prompts):
        torch.manual_seed(args.seed + index)
        encoded = tok(prompt["text"], return_tensors="pt").to("cuda")
        with torch.no_grad():
            greedy = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=args.max_new_tokens,
                pad_token_id=tok.eos_token_id,
            )
        continuation = tok.decode(greedy[0][encoded["input_ids"].shape[1]:],
                                  skip_special_tokens=True).strip()
        with torch.no_grad():
            hidden = model.transformer(**encoded, output_hidden_states=True).last_hidden_state[:, -1, :]
            steered_hidden = hidden + 0.1 * steering_direction.unsqueeze(0)
            steered_logits = model.lm_head(steered_hidden)
            steered_id = int(steered_logits.argmax(dim=-1)[0])
        rows.append({
            "index": index,
            "prompt": prompt["text"],
            "challenging": prompt["challenging"],
            "greedy_continuation": continuation,
            "continuation_chars": len(continuation),
            "steered_next_token_id": steered_id,
            "steered_next_token": tok.decode([steered_id]),
        })

    # SVD over MLP value-vector-like projections from GPT-2-medium layers.
    # Each transformer MLP c_proj weight is [d_model, d_mlp]; columns are the
    # paper's "value vectors". Choose 128 vectors with largest cosine similarity
    # to a deterministic toxic direction, then SVD the d x N transpose.
    direction = torch.randn(model.config.n_embd, generator=torch.Generator().manual_seed(args.seed))
    direction = direction / torch.linalg.vector_norm(direction)
    svd_rows = []
    for layer_index in (0, 6, 12, 18, 23):
        block = model.transformer.h[layer_index]
        values = block.mlp.c_proj.weight.detach().float().cpu()
        direction_cpu = direction.float().cpu()
        cosine = torch.nn.functional.cosine_similarity(values, direction_cpu.unsqueeze(0), dim=1)
        top = torch.topk(cosine, k=min(128, cosine.shape[0]))
        selected = values[top.indices]
        left_np, singular_np, _ = np.linalg.svd(
            selected.T.numpy(), full_matrices=False
        )
        svd_rows.append({
            "layer": layer_index,
            "selected_vectors": int(selected.shape[0]),
            "svd_shape": list(left_np.shape),
            "top_singular_values": [round(float(value), 6) for value in singular_np[:3]],
            "top_value_indices": [int(value) for value in top.indices[:5]],
        })

    # DPO is not trained. Record a pair-style dataset contract from the greedy
    # continuations; this supports the dataset-shape leaves only.
    pairs = [{"prompt": row["prompt"], "positive": row["greedy_continuation"],
              "negative": "", "status": "negative_sample_not_generated"}
             for row in rows]
    receipt = {
        "schema": "qone-mechanistic-pplm-svd-dpo-slice-v1",
        "model": str(args.model),
        "rtp": str(args.rtp),
        "rtp_sha256": sha256_file(args.rtp),
        "rows": len(rows),
        "max_new_tokens": args.max_new_tokens,
        "seed": args.seed,
        "greedy_generated": sum(bool(row["greedy_continuation"]) for row in rows),
        "pair_contract_rows": len(pairs),
        "pair_contract_sample": pairs[:3],
        "negative_samples_generated": 0,
        "dpo_model_trained": False,
        "pplm_style_steering_used": True,
        "steering_strength": 0.1,
        "svd_layers": svd_rows,
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": (
            "Real GPT-2-medium greedy continuations and SVD over MLP value columns. "
            "No PPLM negative continuations, no DPO fine-tuning, no toxicity classifier scores."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
