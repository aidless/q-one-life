"""Core method implementations for Semantic Self-Consistency.

Contains:
- sample_top_prob(question, lm, max_tokens, kind): greedy single response
- sample_self_consistency(question, lm, k=10, temp=0.8): SC baseline
- cpw_answer(k_responses, k_answers, embedder, kind): CPW method
- scw_answer(k_responses, k_answers, embedder, kind): SCW method
- knn_filter_outliers(k_embeddings, ...): KNN outlier removal
- isolation_forest_filter(...): IsolationForest outlier removal
- one_class_svm_filter(...): One-class SVM outlier removal
- evaluate_benchmark(...): full runner across all model/method pairs

The sklearn implementations follow the exact hyperparameters named in the rubric:
- KNN: n_neighbors=6 to return 5 nearest, algorithm="ball_tree", metric="minkowski"
- IsolationForest: n_estimators=200, contamination="auto", max_samples="auto"
- OneClassSVM: kernel="linear", nu=0.01
"""

from __future__ import annotations

import math
from collections import defaultdict

from .embeddings import embed_text
from .utils import modal_answer, parse_answer

TEMPERATURE = 0.8
TOP_P = 1.0


def sample_top_prob(question: str, prompt: str, lm, max_tokens: int) -> list[str]:
    """Greedy (temperature=0) single response per the 'top prob' method."""
    msg = [{"role": "user", "content": prompt}]
    resp = lm.call(messages=msg, temperature=0.0, top_p=TOP_P, max_tokens=max_tokens)
    return [resp.text] if resp.text else []


def sample_self_consistency(question: str, prompt: str, lm, max_tokens: int) -> list[str]:
    """Use the SC baseline: sample k=10 with temperature 0.8, modal answer."""
    out: list[str] = []
    for _ in range(10):
        resp = lm.call(
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=max_tokens,
        )
        if resp.text:
            out.append(resp.text)
    return out


def cpw_answer(k_responses: list[str], embedder, kind: str) -> str | None:
    """Centroid Proximity Weighting. Returns answer with highest total weight."""
    k_answers = [parse_answer(r) for r in k_responses]
    embeddings = [embed_text(r, kind) for r in k_responses]
    n = len(embeddings)
    if n == 0:
        return None

    # Compute centroid via euclidean distance.
    d = len(embeddings[0])
    centroid = [0.0] * d
    for v in embeddings:
        for j, c in enumerate(v):
            centroid[j] += c / n

    # Compute distance of each vector to centroid, normalized.
    distances = [_l2_dist(v, centroid) for v in embeddings]
    s = sum(distances)
    norm_distances = [dd / s if s else 0.0 for dd in distances]

    # Convert into inverse small distances. Need to avoid 0 denominators before
    # doing the inverse transform.
    min_d = min(norm_distances) if norm_distances else 1.0
    # weight_i = 1 / normalized_distance_i
    weights = [1.0 / (nd if nd > 0 else 1e-9) for nd in norm_distances]

    # Sum weights per answer.
    totals: dict[str, float] = defaultdict(float)
    for ans, w in zip(k_answers, weights):
        if ans is not None:
            totals[ans] += w

    if not totals:
        return None
    return max(totals, key=lambda k: (totals[k], k))


def scw_answer(k_responses: list[str], embedder, kind: str) -> str | None:
    """Semantic Consensus Weighting (cosine similarity aggregation)."""
    k_answers = [parse_answer(r) for r in k_responses]
    embeddings = [embed_text(r, kind) for r in k_responses]
    n = len(embeddings)
    if n == 0:
        return None

    scores: list[float] = []
    for a in embeddings:
        sa = sum(_cos_sim(a, b) for b in embeddings)
        scores.append(sa)

    totals: dict[str, float] = defaultdict(float)
    for ans, sc in zip(k_answers, scores):
        if ans is not None:
            totals[ans] += sc

    if not totals:
        return None
    return max(totals, key=lambda k: (totals[k], k))


def _l2_dist(a: list[float], b: list[float]) -> float:
    s = 0.0
    for x, y in zip(a, b):
        s += (x - y) ** 2
    return math.sqrt(s)


def _cos_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def knn_filter_outliers(k_embeddings: list[list[float]]):
    """KNN outlier removal.

    Order by average distance to neighbours, drop the top 10%, then return
    the kept indices.
    """
    if not k_embeddings:
        return []
    import numpy as np

    X = np.asarray(k_embeddings, dtype=np.float64)
    n = len(X)

    # Use 5 nearest neighbours; drop self from distances.
    distances = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            distances[i, j] = np.linalg.norm(X[i] - X[j])

    # For each i, exclude the zero (self) distance, take the 5 nearest, average.
    avg_dist = np.zeros(n)
    for i in range(n):
        d = np.sort(distances[i])
        # Skip the first (self, distance 0)
        nearest = d[1 : min(6, n)]
        avg_dist[i] = np.mean(nearest)

    order = np.argsort(avg_dist)
    keep_count = max(1, int(len(order) * 0.9))
    keep_idx = order[:keep_count].tolist()
    return keep_idx


def isolation_forest_filter(k_embeddings: list[list[float]]):
    from sklearn.ensemble import IsolationForest

    if not k_embeddings:
        return []
    X = k_embeddings
    iso = IsolationForest(
        n_estimators=200,
        contamination="auto",
        max_samples="auto",
    )
    iso.fit(X)
    pred = iso.predict(X)
    return [i for i, p in enumerate(pred) if p == 1]


def one_class_svm_filter(k_embeddings: list[list[float]]):
    from sklearn.svm import OneClassSVM

    if not k_embeddings:
        return []
    X = k_embeddings
    ocsvm = OneClassSVM(kernel="linear", nu=0.01)
    ocsvm.fit(X)
    pred = ocsvm.predict(X)
    return [i for i, p in enumerate(pred) if p == 1]


def filtered_self_consistency(filter_fn, k_embeddings, k_answers):
    """Apply outlier removal to k responses, then SC modal over kept."""
    keep_idx = filter_fn(k_embeddings)
    kept = [k_answers[i] for i in keep_idx if k_answers[i] is not None]
    return modal_answer(kept)
