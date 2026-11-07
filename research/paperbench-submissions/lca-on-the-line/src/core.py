"""Architecture-level stub for PaperBench task lca-on-the-line."""

from __future__ import annotations

RUBRIC_LEAVES = 819
CATEGORIES = ['Code Development', 'Code Execution', 'Result Analysis']
KEYWORDS = ['Absolute', 'Algorithm', 'Aline-D', 'Aline-S', 'Appendix', 'CLIP_RN50', 'CLIP_RN50x4', 'ConvNext', 'Equation', 'Error', 'Hierarchical', 'ImageNet']


def summarize_rubric() -> dict:
    return {"paper_id": 'lca-on-the-line', "rubric_leaves": RUBRIC_LEAVES,
            "categories": CATEGORIES, "keywords": KEYWORDS}


def run(data: dict) -> dict:
    items = data.get("datasets", {}).get("items", [])
    return {"paper_id": 'lca-on-the-line', "count": len(items),
            "rubric_leaves": RUBRIC_LEAVES, "status": "architecture_stub"}
