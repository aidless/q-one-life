"""Shared utilities for Semantic Self-Consistency reproduction."""

from __future__ import annotations

import re
import string
from collections import defaultdict


ANSWER_RE = re.compile(r"The answer is\s*(.+?)\s*$", re.IGNORECASE)


def parse_answer(text: str) -> str | None:
    """Parse the answer after 'The answer is X' from a model response.

    Per the paper: strip whitespace, full stop (period), and parentheses.
    Returns None if no answer can be parsed.
    """
    m = ANSWER_RE.search(text)
    if m is None:
        return None
    ans = m.group(1).strip()
    ans = ans.strip().rstrip(".").strip()
    ans = ans.strip("()").strip()
    return ans if ans else None


def modal_answer(answers: list[str | None]) -> str | None:
    """Return the most common non-None answer among k parsed answers."""
    parsed = [a for a in answers if a is not None]
    if not parsed:
        return None
    counts: dict[str, int] = defaultdict(int)
    for a in parsed:
        counts[a] += 1
    return max(counts, key=lambda k: (counts[k], k))


def _embedding_cls_token(embedder, text: str) -> list[float]:
    """Run text through the embedder and return the [CLS] (first) token embedding."""
    out = embedder(text)
    if hasattr(out, "last_hidden_state"):
        vec = out.last_hidden_state[0].tolist()
    else:
        vec = out[0].tolist()
    return vec
