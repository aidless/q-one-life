"""Architecture-level stub for PaperBench task rice."""

from __future__ import annotations

RUBRIC_LEAVES = 361
CATEGORIES = ['Code Development', 'Code Execution', 'Result Analysis']
KEYWORDS = ['Actor', 'Adversarial', 'Algorithm', 'Alternative', 'Appendix', 'Challenge', 'Cheng', 'Critic', 'Distillation', 'Experiment', 'Explanation', 'Figure']


def summarize_rubric() -> dict:
    return {"paper_id": 'rice', "rubric_leaves": RUBRIC_LEAVES,
            "categories": CATEGORIES, "keywords": KEYWORDS}


def run(data: dict) -> dict:
    items = data.get("datasets", {}).get("items", [])
    return {"paper_id": 'rice', "count": len(items),
            "rubric_leaves": RUBRIC_LEAVES, "status": "architecture_stub"}
