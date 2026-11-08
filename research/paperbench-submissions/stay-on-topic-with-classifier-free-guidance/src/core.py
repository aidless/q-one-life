"""Architecture-level stub for PaperBench task stay-on-topic-with-classifier-free-guidance."""

from __future__ import annotations

RUBRIC_LEAVES = 121
CATEGORIES = ['Code Development', 'Code Execution', 'Result Analysis']
KEYWORDS = ['ANCOVA', 'ARC-c', 'ARC-e', 'Across', 'Addendum', 'Appendix', 'B-mono', 'BoolQ', 'Bottom', 'Chain', 'Chain-of-Thought', 'Classifier-Free']


def summarize_rubric() -> dict:
    return {"paper_id": 'stay-on-topic-with-classifier-free-guidance', "rubric_leaves": RUBRIC_LEAVES,
            "categories": CATEGORIES, "keywords": KEYWORDS}


def run(data: dict) -> dict:
    if data.get("cfg_slice"):
        from .cfg import run_cfg_slice
        return run_cfg_slice(**data["cfg_slice"])
    items = data.get("datasets", {}).get("items", [])
    return {"paper_id": 'stay-on-topic-with-classifier-free-guidance', "count": len(items),
            "rubric_leaves": RUBRIC_LEAVES, "status": "architecture_stub"}
