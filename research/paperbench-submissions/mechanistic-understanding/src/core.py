"""Architecture-level stub for PaperBench task mechanistic-understanding."""

from __future__ import annotations

RUBRIC_LEAVES = 96
CATEGORIES = ['Code Development', 'Code Execution', 'Result Analysis']
KEYWORDS = ['Appendix', 'GPT-2', 'Gaussian', 'However', 'Jigsaw', 'Precision', 'RMSProp', 'RealToxicityPrompt', 'RealToxicityPrompts', 'Section', 'Substracting', 'Table']


def summarize_rubric() -> dict:
    return {"paper_id": 'mechanistic-understanding', "rubric_leaves": RUBRIC_LEAVES,
            "categories": CATEGORIES, "keywords": KEYWORDS}


def run(data: dict) -> dict:
    limit = data.get("limit")
    if isinstance(limit, int) and limit > 0:
        from .pipeline import run_reproduction_slice
        return run_reproduction_slice(limit=limit)
    items = data.get("datasets", {}).get("items", [])
    return {"paper_id": 'mechanistic-understanding', "count": len(items),
            "rubric_leaves": RUBRIC_LEAVES, "status": "architecture_stub"}
