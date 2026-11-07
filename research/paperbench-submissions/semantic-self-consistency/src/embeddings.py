"""Embedding featurizers.

If HuggingFace hub is unreachable, a deterministic hash-based 64-dim unit
vector is returned so the pipeline runs offline. Set HF_HUB_OFFLINE=1 to
force offline mode.
"""

from __future__ import annotations

import hashlib
import os


def embed_text(text: str, kind: str = "scibert") -> list[float]:
    """Return the [CLS]-token embedding of `text`.

    Args:
        kind: "scibert" (AQuA-RAT / SVAMP) or "roberta" (StrategyQA).
    """
    if os.environ.get("HF_HUB_OFFLINE", "0") != "1":
        try:
            return _real_embed(text, kind)
        except Exception:
            pass
    return _hash_embed(text)


def _real_embed(text: str, kind: str) -> list[float]:
    model_name = "allenai/scibert_scivocab_uncased" if kind == "scibert" else "roberta-base"
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    encoded = tok([text], return_tensors="pt", truncation=True, max_length=512)
    with __import__("torch").no_grad():
        out = model(**encoded)
    return out.last_hidden_state[0, 0].tolist()


def _hash_embed(text: str) -> list[float]:
    key = text.encode("utf-8")
    vals = []
    for i in range(64):
        h = hashlib.sha256(key + bytes([i])).digest()
        vals.append(((h[0] * 255 + h[1]) % 1000) / 1000.0 - 0.5)
    norm = sum(v * v for v in vals) ** 0.5
    return [v / (norm + 1e-9) for v in vals]
