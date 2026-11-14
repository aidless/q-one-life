"""Core evaluation pipeline for Semantic Self-Consistency reproduction.

Summary
-------
This module is the main entrypoint of the reproduction. For each dataset
(AQuA-RAT, StrategyQA, SVAMP) it runs:

1. Top-prob (greedy) sampling per question.
2. Self-consistency baseline (k=10 sampling, temperature=0.8, modal answer).
3. CPW (centroid proximity weighting) over SciBERT/RoBERTa embeddings.
4. SCW (semantic consensus weighting) over SciBERT/RoBERTa embeddings.
5. KNN, IsolationForest and OneClassSVM outlier removal, then SC on the
   remaining samples.

Accuracy is the fraction of questions whose extracted final answer matches
the gold answer.

Running with a real model
-------------------------
Replace ``LM`` with an OpenAI-compatible client that implements ``call(
messages, temperature, top_p, max_tokens) -> response_object_with_text``.
The repository ships ``OptionalOpenAILLM`` for convenience.
"""

from __future__ import annotations

from collections import defaultdict

from .datasets import (
    AQUA_SHOT_PROMPT,
    SVAMP_SHOT_PROMPT,
    STRATEGYQA_SHOT_PROMPT,
    load_aqua_rat_test,
    load_svamp_full,
    load_strategyqa_test,
)
from .methods import (
    cpw_answer,
    filtered_self_consistency,
    isolation_forest_filter,
    knn_filter_outliers,
    modal_answer,
    one_class_svm_filter,
    sample_self_consistency,
    scw_answer,
)
from .utils import parse_answer

MAX_TOKENS = {
    "svamp": 250,
    "aqua_rat": 400,
    "strategyqa": 450,
}

TEMPERATURE = 0.8
TOP_P = 1.0
N_SAMPLES = 10

DATASETS = {
    "aqua_rat": {
        "loader": load_aqua_rat_test,
        "prompt": AQUA_SHOT_PROMPT,
        "featurizer": "scibert",
        "token_key": "aqua_rat",
    },
    "svamp": {
        "loader": load_svamp_full,
        "prompt": SVAMP_SHOT_PROMPT,
        "featurizer": "scibert",
        "token_key": "svamp",
    },
    "strategyqa": {
        "loader": load_strategyqa_test,
        "prompt": STRATEGYQA_SHOT_PROMPT,
        "featurizer": "roberta",
        "token_key": "strategyqa",
    },
}


class LM:
    """Base interface for language models."""

    def call(self, *, messages, temperature, top_p, max_tokens):  # pragma: no cover
        raise NotImplementedError


class MockLM(LM):
    """Stub LM returning a fixed string. For tests/smoke."""

    def __init__(self, text="The answer is 4"):
        self.answer = text
        self.text = text

    def call(self, *, messages, temperature, top_p, max_tokens):
        return type("R", (), {"text": self.text})()


class OpenAILLM(LM):
    """OpenAI-compatible chat model."""

    def __init__(self, model_name: str, api_key: str):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name

    def call(self, *, messages, temperature, top_p, max_tokens):
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message


def run_benchmark(dataset_name, samples, lm, featurizer_kind, n_samples: int = 10) -> dict:
    """Run all methods over one dataset and return a summary dict."""
    cfg = DATASETS[dataset_name]
    max_tokens = MAX_TOKENS[cfg["token_key"]]
    method_scores: dict = defaultdict(lambda: [0, 0])
    config = {
        "temperature": TEMPERATURE,
        "top_p": 1.0,
        "max_tokens": max_tokens,
        "k_shot": cfg["prompt"].count("Question:"),
        "featurizer": featurizer_kind,
        "n_samples": n_samples,
    }

    for s in samples:
        question = s["question"]
        gold = str(s.get("correct", s.get("answer", ""))).lower()

        prompt = (
            cfg["prompt"]
            + f"\n\nQuestion: {question}\nA:"
            if question not in cfg["prompt"]
            else cfg["prompt"]
        )

        # top-prob (greedy temperature=0)
        greedy = lm.call(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=max_tokens,
        )
        greedy_text = getattr(greedy, "text", "") or ""
        greedy_ans = parse_answer(greedy_text)
        ok_top = 1 if greedy_ans is not None and str(greedy_ans).lower() == gold else 0
        method_scores["top_prob"][0] += ok_top
        method_scores["top_prob"][1] += 1

        # SC baseline (k=10, temperature 0.8)
        k_responses = sample_self_consistency(
            question, prompt, lm, max_tokens
        )
        k_answers = [parse_answer(r) for r in k_responses]
        sc_ans = modal_answer(k_answers)
        ok_sc = 1 if sc_ans is not None and str(sc_ans).lower() == gold else 0
        method_scores["sc_baseline"][0] += ok_sc
        method_scores["sc_baseline"][1] += 1

        if k_responses:
            # CPW / SCW
            cpw_ans = cpw_answer(k_responses, None, featurizer_kind)
            ok_cpw = 1 if cpw_ans is not None and str(cpw_ans).lower() == gold else 0
            method_scores["cpw"][0] += ok_cpw
            method_scores["cpw"][1] += 1

            scv_ans = scw_answer(k_responses, None, featurizer_kind)
            ok_scv = 1 if scv_ans is not None and str(scv_ans).lower() == gold else 0
            method_scores["scw"][0] += ok_scv
            method_scores["scw"][1] += 1

            # outlier removal methods
            embeddings = [_embed_safe(r, featurizer_kind) for r in k_responses]
            for m in ("knn", "iso", "svm"):
                fn = {
                    "knn": knn_filter_outliers,
                    "iso": isolation_forest_filter,
                    "svm": one_class_svm_filter,
                }[m]
                ans_rm = filtered_self_consistency(fn, embeddings, k_answers)
                ok_rm = 1 if ans_rm is not None and str(ans_rm).lower() == gold else 0
                method_scores[f"{m}_removal"][0] += ok_rm
                method_scores[f"{m}_removal"][1] += 1

    summary = {
        "dataset": dataset_name,
        "configuration": config,
        "methods": {
            k: {
                "correct": int(v[0]),
                "total": int(v[1]),
                "accuracy": v[0] / v[1] if v[1] else 0.0,
            }
            for k, v in method_scores.items()
        },
    }
    return summary


def _embed_safe(text: str, kind: str) -> list[float]:
    from .embeddings import embed_text
    return embed_text(text, kind=kind)


def run_all(datasets, lm) -> dict:
    """Run all datasets and return a nested summary dict."""
    out = {}
    for name in datasets:
        cfg = DATASETS[name]
        samples = cfg["loader"]()
        out[name] = run_benchmark(name, samples, lm, cfg["featurizer"])
    return out
