"""Architecture-level stub for PaperBench task all-in-one."""

from __future__ import annotations

RUBRIC_LEAVES = 174
CATEGORIES = ['Code Development', 'Code Execution', 'Result Analysis']
KEYWORDS = ['Across', 'Algorithm', 'Appendix', 'Bernoulli', 'Carlo', 'Chain', 'Classifier', 'Conditioning', 'Default', 'Diffusion', 'During', 'Early']


def summarize_rubric() -> dict:
    return {"paper_id": 'all-in-one', "rubric_leaves": RUBRIC_LEAVES,
            "categories": CATEGORIES, "keywords": KEYWORDS}


def run(data: dict) -> dict:
    items = data.get("datasets", {}).get("items", [])
    return {"paper_id": 'all-in-one', "count": len(items),
            "rubric_leaves": RUBRIC_LEAVES, "status": "architecture_stub"}
