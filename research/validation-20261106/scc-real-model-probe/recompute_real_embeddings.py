#!/usr/bin/env python3
"""Recompute CPW/SCW on stored real-model responses using real HF encoders.

Does not call the generator model again. Reads every `runs/*/summary.raw.jsonl`,
re-embeds each response with SciBERT (AQuA/SVAMP) or RoBERTa (StrategyQA),
then re-runs the submission's exact `cpw_answer` / `scw_answer` logic with the
real [CLS] vectors. Also reports the deterministic hash-embedding baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

KIND = {"aqua": "scibert", "svamp": "scibert", "strategyqa": "roberta"}
MODELS = {
    "scibert": "allenai/scibert_scivocab_uncased",
    "roberta": "roberta-base",
}
PATHS = {
    "scibert": "allenai/scibert_scivocab_uncased",
    "roberta": "roberta-base",
}


def canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def norm(value):
    return None if value is None else str(value).strip().lower().rstrip(".")


def load_encoder(kind: str, weights: Path):
    from transformers import AutoModel, AutoTokenizer

    name = str(weights / PATHS[kind])
    tok = AutoTokenizer.from_pretrained(name, model_max_length=512)
    model = AutoModel.from_pretrained(name)
    model.eval()
    return tok, model


MAX_LENGTH = 256
BATCH_SIZE = 16


def cls_embeddings(texts: list[str], tok, model, device: str = "cpu") -> list[list[float]]:
    import torch

    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        encoded = tok(batch, return_tensors="pt", truncation=True,
                      max_length=MAX_LENGTH, padding=True)
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            out = model(**encoded)
        vectors.extend(out.last_hidden_state[:, 0, :].cpu().tolist())
    return vectors


def method_with_vectors(responses: list[str], answers: list[str | None],
                        vectors: list[list[float]], method: str) -> str | None:
    """Exact same aggregation as src/methods.py, but with precomputed vectors."""
    from collections import defaultdict
    import math

    n = len(vectors)
    if n == 0:
        return None
    if method == "cpw":
        d = len(vectors[0])
        centroid = [sum(v[j] for v in vectors) / n for j in range(d)]
        distances = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, centroid))) for v in vectors]
        s = sum(distances)
        norm_d = [x / s if s else 0.0 for x in distances]
        weights = [1.0 / (x if x > 0 else 1e-9) for x in norm_d]
    else:
        def cos(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return dot / (na * nb) if na and nb else 0.0
        weights = [sum(cos(a, b) for b in vectors) for a in vectors]
    totals: dict[str, float] = defaultdict(float)
    for ans, w in zip(answers, weights):
        if ans is not None:
            totals[ans] += w
    return max(totals, key=lambda k: (totals[k], k)) if totals else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--submission-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hash-embedder", default="hash")
    parser.add_argument("--datasets", default="aqua,svamp,strategyqa",
                        help="only recompute these datasets (comma-separated)")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    args = parser.parse_args()

    sys.path.insert(0, str(args.submission_root.resolve()))
    from src.embeddings import _hash_embed  # noqa: E402
    from run_real_model_probe import extract_answer  # noqa: E402

    wanted_kinds = {KIND[d.strip()] for d in args.datasets.split(",") if d.strip()}
    import torch

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    encoders = {
        kind: load_encoder(kind, args.weights)
        for kind in wanted_kinds
    }
    for _, (_, model) in encoders.items():
        model.to(device)
    records = []
    for raw_path in sorted(args.root.glob("*/summary.raw.jsonl")):
        summary = json.loads((raw_path.parent / "summary.json").read_text())
        prompt_mode = summary["prompt_mode"]
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            records.append((prompt_mode, rec))

    from collections import defaultdict
    grouped: dict[tuple, list] = defaultdict(list)
    for prompt_mode, rec in records:
        grouped[(prompt_mode, rec["dataset"])].append(rec)

    results = []
    for (prompt_mode, dataset), rows in sorted(grouped.items()):
        if dataset not in {d.strip() for d in args.datasets.split(",") if d.strip()}:
            continue
        kind = KIND[dataset]
        tok, model = encoders[kind]
        correct = {"hash_cpw": 0, "hash_scw": 0, "real_cpw": 0, "real_scw": 0, "sc": 0}
        for rec in rows:
            gold = norm(rec["gold"])
            responses = rec["samples"]
            answers = [extract_answer(r, "aqua_rat" if dataset == "aqua" else dataset)[0]
                       for r in responses]
            hash_vec = [_hash_embed(r) for r in responses]
            real_vec = cls_embeddings(responses, tok, model, device)
            for label, vecs in (("hash", hash_vec), ("real", real_vec)):
                cpw = method_with_vectors(responses, answers, vecs, "cpw")
                scw = method_with_vectors(responses, answers, vecs, "scw")
                correct[f"{label}_cpw"] += int(norm(cpw) == gold)
                correct[f"{label}_scw"] += int(norm(scw) == gold)
            correct["sc"] += int(norm(rec["sc_answer"]) == gold)
        n = len(rows)
        results.append({
            "prompt_mode": prompt_mode,
            "dataset": dataset,
            "rows": n,
            "embedder": kind,
            "device": device,
            "accuracy_sc_modal": correct["sc"] / n,
            "accuracy_hash_cpw": correct["hash_cpw"] / n,
            "accuracy_hash_scw": correct["hash_scw"] / n,
            "accuracy_real_cpw": correct["real_cpw"] / n,
            "accuracy_real_scw": correct["real_scw"] / n,
        })
        print(json.dumps(results[-1]), flush=True)

    summary = {
        "weights_root": str(args.weights),
        "models": MODELS,
        "device": device,
        "max_length": 256,
        "batch_size": 16,
        "results": results,
        "note": (
            "Real encoders replace the offline hash featurizer for CPW/SCW only; "
            "responses and prompts are unchanged from the recorded real 0.5B model batches."
        ),
    }
    summary["canonical_sha256"] = canonical_sha256(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
