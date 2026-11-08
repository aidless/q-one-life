"""Executable LCA distance and LCA alignment loss slice.

Implements the pure-algorithm leaves of `lca-on-the-line`:
- lowest common ancestor, node depth, information content
- LCA distance via information content and via tree depth
- Algorithm 1 alignment loss (reverse LCA matrix, softmax, one-hot, CE/BCE)

Uses a small in-repo toy taxonomy. It does NOT query the paper's 75 vision /
vision-language models and does NOT download ImageNet or any OOD test set.
"""

from __future__ import annotations

import math
from collections import Counter


class Tree:
    """Small rooted tree; `parent[node] is None` marks the root."""

    def __init__(self, parent: dict[str, str | None]):
        self.parent = parent
        self.leaves = [n for n, p in parent.items() if p is not None or n == self._root()]
        self._leaf_set = {
            n for n in parent if n not in {p for p in parent.values() if p is not None}
        }

    def _root(self) -> str:
        roots = [n for n, p in self.parent.items() if p is None]
        if len(roots) != 1:
            raise ValueError("tree must have exactly one root")
        return roots[0]

    def ancestors(self, node: str) -> list[str]:
        chain = [node]
        while self.parent.get(chain[-1]) is not None:
            chain.append(self.parent[chain[-1]])
        return chain

    def depth(self, node: str) -> int:
        return len(self.ancestors(node)) - 1

    def lca(self, left: str, right: str) -> str:
        a = self.ancestors(left)
        b = set(self.ancestors(right))
        return next(node for node in a if node in b)

    def leaf_count(self, node: str) -> int:
        return sum(1 for leaf in self._leaf_set if node in self.ancestors(leaf))

    def information_content(self, node: str) -> float:
        total = len(self._leaf_set)
        under = self.leaf_count(node)
        if total == 0 or under == 0:
            return 0.0
        return math.log2(total) - math.log2(under)

    def distance_information(self, left: str, right: str) -> float:
        return self.information_content(self.lca(left, right))

    def distance_depth(self, left: str, right: str) -> float:
        ancestor = self.lca(left, right)
        return (self.depth(left) - self.depth(ancestor)) + (
            self.depth(right) - self.depth(ancestor)
        )

    def distance_matrix(self, metric: str = "information") -> list[list[float]]:
        leaves = sorted(self._leaf_set)
        fn = self.distance_information if metric == "information" else self.distance_depth
        return [[fn(a, b) for b in leaves] for a in leaves]


def toy_tree() -> Tree:
    return Tree({
        "root": None,
        "animal": "root",
        "vehicle": "root",
        "dog": "animal",
        "cat": "animal",
        "car": "vehicle",
        "truck": "vehicle",
    })


def softmax(logits: list[list[float]]) -> list[list[float]]:
    out = []
    for row in logits:
        m = max(row)
        exps = [math.exp(x - m) for x in row]
        total = sum(exps)
        out.append([x / total for x in exps])
    return out


def one_hot(targets: list[int], n_classes: int) -> list[list[float]]:
    return [[1.0 if i == t else 0.0 for i in range(n_classes)] for t in targets]


def lca_alignment_loss(
    logits: list[list[float]],
    targets: list[int],
    lca_matrix: list[list[float]],
    alignment_mode: str = "CE",
    lambda_weight: float = 0.03,
) -> float:
    """Algorithm 1, pure Python. `lca_matrix` is already scaled to [0, 1]."""
    if alignment_mode not in ("CE", "BCE"):
        raise ValueError("alignment_mode must be CE or BCE")
    probs = softmax(logits)
    hot = one_hot(targets, len(logits[0]))
    reverse = [[1.0 - value for value in row] for row in lca_matrix]
    losses = []
    for row_idx, target in enumerate(targets):
        standard = -sum(
            h * math.log(max(p, 1e-12)) for h, p in zip(hot[row_idx], probs[row_idx])
        )
        if alignment_mode == "CE":
            soft = -sum(
                r * math.log(max(p, 1e-12))
                for r, p in zip(reverse[target], probs[row_idx])
            ) / len(probs[row_idx])
        else:
            soft = sum(
                -(
                    r * math.log(max(1 / (1 + math.exp(-z)), 1e-12))
                    + (1 - r) * math.log(max(1 - 1 / (1 + math.exp(-z)), 1e-12))
                )
                for r, z in zip(reverse[target], logits[row_idx])
            ) / len(logits[row_idx])
        losses.append(lambda_weight * standard + soft)
    return sum(losses) / len(losses)


def run_algorithm_slice() -> dict:
    tree = toy_tree()
    matrix = tree.distance_matrix("information")
    logits = [[2.0, 0.5, 0.1, 0.1], [0.2, 1.8, 0.3, 0.1]]
    loss_ce = lca_alignment_loss(logits, [0, 1], matrix, "CE")
    loss_bce = lca_alignment_loss(logits, [0, 1], matrix, "BCE")
    return {
        "paper_id": "lca-on-the-line",
        "status": "algorithm_slice",
        "leaves": sorted(tree._leaf_set),
        "lca_dog_cat": tree.lca("dog", "cat"),
        "depth_dog": tree.depth("dog"),
        "information_content_animal": tree.information_content("animal"),
        "distance_information_dog_car": tree.distance_information("dog", "car"),
        "distance_depth_dog_car": tree.distance_depth("dog", "car"),
        "alignment_loss_ce": loss_ce,
        "alignment_loss_bce": loss_bce,
        "note": "Toy taxonomy only; no ImageNet, no 75 models, no real judge score.",
    }
