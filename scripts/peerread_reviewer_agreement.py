"""Quantify how noisy the PeerRead human target is before claiming calibration."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np


def annotated_reviews(record: dict) -> list[dict]:
    rows = []
    seen = set()
    for review in record.get("reviews", []):
        if review.get("IS_META_REVIEW") or review.get("IS_ANNOTATED") is not True:
            continue
        reviewer = str(review.get("OTHER_KEYS") or "")
        if "AnonReviewer" not in reviewer:
            continue
        score = review.get("RECOMMENDATION")
        date = review.get("DATE")
        key = (reviewer, date)
        if key in seen:
            continue
        seen.add(key)
        if isinstance(score, int):
            rows.append({"reviewer": reviewer, "score": score, "date": date,
                         "confidence": review.get("REVIEWER_CONFIDENCE")})
    return rows


def icc_one_way(groups: list[list[float]]) -> float | None:
    """ICC(1,1) for unbalanced groups: (MSB - MSW) / (MSB + (k-1) MSW)."""
    groups = [group for group in groups if len(group) >= 2]
    if len(groups) < 3:
        return None
    n = len(groups)
    grand = np.mean([value for group in groups for value in group])
    ssb = sum(len(group) * (np.mean(group) - grand) ** 2 for group in groups)
    ssw = sum((value - np.mean(group)) ** 2 for group in groups for value in group)
    msb = ssb / (n - 1)
    dfw = sum(len(group) - 1 for group in groups)
    msw = ssw / dfw if dfw else 0.0
    k = np.mean([len(group) for group in groups])
    denominator = msb + (k - 1) * msw
    if denominator == 0:
        return None
    return float((msb - msw) / denominator)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "raw/peerread/data/iclr_2017"
    papers = []
    for split in ("train", "dev", "test"):
        for path in sorted((base / split / "reviews").glob("*.json")):
            record = json.loads(path.read_text())
            rows = annotated_reviews(record)
            if rows:
                papers.append({"paper_id": path.name.split(".")[0], "split": split,
                               "reviews": rows})

    multi = [paper for paper in papers if len(paper["reviews"]) >= 2]
    pairwise = []
    for paper in multi:
        scores = [row["score"] for row in paper["reviews"]]
        for a, b in itertools.combinations(scores, 2):
            pairwise.append((a, b))
    exact = sum(1 for a, b in pairwise if a == b) / len(pairwise) if pairwise else None
    close = sum(1 for a, b in pairwise if abs(a - b) <= 1) / len(pairwise) if pairwise else None
    icc = icc_one_way([[row["score"] for row in paper["reviews"]] for paper in multi])
    spreads = [max(row["score"] for row in paper["reviews"]) - min(row["score"] for row in paper["reviews"])
               for paper in multi]

    # How often does our paper-level rubric score fall inside the human range?
    rubric = {}
    for path in sorted((args.root / "peerread-expanded").glob("paper-*.json")):
        record = json.loads(path.read_text())
        if record.get("rubric"):
            rubric[record["paper_id"]] = 0.3 * record["rubric"]["novelty"] + 0.4 * record["rubric"]["rigor"] \
                + 0.3 * record["rubric"]["clarity"]
    inside = 0
    compared = 0
    for paper in multi:
        if paper["paper_id"] not in rubric:
            continue
        scores = [row["score"] for row in paper["reviews"]]
        compared += 1
        # rubric uses 1-5, humans 1-10; compare only after scaling rubric to 1-10
        scaled = (rubric[paper["paper_id"]] - 1) / 4 * 9 + 1
        inside += int(min(scores) <= scaled <= max(scores))

    report = {
        "schema": "qone-peerread-reviewer-agreement-v1",
        "papers_with_reviews": len(papers),
        "papers_with_at_least_two_reviews": len(multi),
        "review_rows": sum(len(paper["reviews"]) for paper in papers),
        "reviewer_count_distribution": {
            str(k): sum(1 for paper in papers if len(paper["reviews"]) == k)
            for k in sorted({len(paper["reviews"]) for paper in papers})
        },
        "mean_within_paper_spread": float(np.mean(spreads)) if spreads else None,
        "median_within_paper_spread": float(np.median(spreads)) if spreads else None,
        "spread_distribution": {str(int(k)): int(v) for k, v in
                                zip(*np.unique(spreads, return_counts=True), strict=False)} if spreads else {},
        "pairwise_exact_agreement": exact,
        "pairwise_within_one_point": close,
        "pairwise_count": len(pairwise),
        "icc_1_1": icc,
        "rubric_inside_human_range": {"compared": compared, "inside": inside,
                                      "rate": inside / compared if compared else None},
        "claim_limit": (
            "Descriptor of label noise in PeerRead; ICC(1,1) for unbalanced groups. "
            "Not a rubric calibration result."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "agreement.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
