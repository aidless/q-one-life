"""Classifier-Free Guidance logits slice (paper Eq. 7).

Implements `logits = gamma * logits_cond + (1 - gamma) * logits_uncond`
for arbitrary causal-LM logits tensors. The unconditional branch starts at the
last prompt token, so the first generated token is the first scored position.

No GPT-2/Pythia weights, benchmark datasets, training or judge are used here.
"""

from __future__ import annotations

from typing import Any


def combine_logits(logits_cond: Any, logits_uncond: Any, gamma: float) -> Any:
    if not isinstance(gamma, (int, float)) or isinstance(gamma, bool):
        raise ValueError("gamma must be a real number")
    if gamma < 0:
        raise ValueError("gamma must be >= 0")
    if logits_cond.shape != logits_uncond.shape:
        raise ValueError("conditional and unconditional logits must have the same shape")
    return gamma * logits_cond + (1.0 - gamma) * logits_uncond


def unconditional_start(prompt_length: int) -> int:
    if prompt_length < 1:
        raise ValueError("prompt must contain at least one token")
    return prompt_length - 1


def cfg_logits(cond_scores: Any, uncond_scores: Any, gamma: float) -> Any:
    """Thin alias used by the submission's run interface."""
    return combine_logits(cond_scores, uncond_scores, gamma)


def benchmark_manifest() -> list[dict]:
    """Official section 3.1 benchmark sources; none are downloaded here."""
    sources = [
        ("ARC-c", "https://huggingface.co/datasets/allenai/ai2_arc"),
        ("ARC-e", "https://huggingface.co/datasets/allenai/ai2_arc"),
        ("BoolQ", "https://huggingface.co/datasets/google/boolq"),
        ("HellaSwag", "https://rowanzellers.com/hellaswag/"),
        ("PiQA", "https://github.com/ybisk/ybisk.github.io/tree/master/piqa"),
        ("SciQ", "https://huggingface.co/datasets/allenai/sciq"),
        ("TriviaQA", "https://huggingface.co/datasets/mandarjoshi/trivia_qa"),
        ("WinoGrande", "https://huggingface.co/datasets/allenai/winogrande"),
        ("LAMBADA", "https://huggingface.co/datasets/EleutherAI/lambada_openai"),
    ]
    return [
        {"name": name, "url": url, "available": False,
         "reason": "not downloaded; GPT-2/Pythia evaluation requires separate authorization"}
        for name, url in sources
    ]


def run_cfg_slice(logits_cond: Any = None, logits_uncond: Any = None,
                  gamma: float = 1.5, prompt_length: int = 4) -> dict:
    import torch

    if logits_cond is None:
        logits_cond = torch.tensor([[1.0, 2.0, 3.0]])
    if logits_uncond is None:
        logits_uncond = torch.tensor([[0.5, 0.5, 0.5]])
    guided = combine_logits(logits_cond, logits_uncond, gamma)
    return {
        "paper_id": "stay-on-topic-with-classifier-free-guidance",
        "status": "cfg_inference_slice",
        "gamma": gamma,
        "unconditional_start_index": unconditional_start(prompt_length),
        "guided_logits": guided.tolist(),
        "benchmarks": benchmark_manifest(),
        "note": "Toy logits only; no GPT-2/Pythia, no benchmark evaluation, no judge.",
    }
