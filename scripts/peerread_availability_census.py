"""Census PeerRead availability: papers, parsed PDFs, reviews, and intersection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def is_annotated_reviewer(review: dict) -> bool:
    if review.get("IS_META_REVIEW") or review.get("IS_ANNOTATED") is not True:
        return False
    return "AnonReviewer" in str(review.get("OTHER_KEYS") or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "raw/peerread/data/iclr_2017"
    report: dict = {"schema": "qone-peerread-availability-v1", "splits": {}}
    total_papers = 0
    total_parsed = 0
    total_reviewed = 0
    total_usable = 0
    total_reviewer_rows = 0
    total_unique_reviewers = 0
    for split in ("train", "dev", "test"):
        reviews_dir = base / split / "reviews"
        parsed_dir = base / split / "parsed_pdfs"
        paper_ids = set()
        for path in sorted(reviews_dir.glob("*.json")):
            paper_ids.add(path.name.split(".")[0])
        review_counts = {}
        for path in sorted(reviews_dir.glob("*.json")):
            paper_id = path.name.split(".")[0]
            record = json.loads(path.read_text())
            rows = [review for review in record.get("reviews", []) if is_annotated_reviewer(review)]
            if rows:
                review_counts[paper_id] = len(rows)
        parsed_ids = {path.name.split(".")[0] for path in sorted(parsed_dir.glob("*.json"))}
        usable = sorted(paper_ids & parsed_ids & set(review_counts))
        total_papers += len(paper_ids)
        total_parsed += len(parsed_ids)
        total_reviewed += len(review_counts)
        total_usable += len(usable)
        total_reviewer_rows += sum(review_counts.values())
        total_unique_reviewers += sum(1 for path in sorted(reviews_dir.glob("*.json"))
                                     for review in json.loads(path.read_text()).get("reviews", [])
                                     if is_annotated_reviewer(review))
        report["splits"][split] = {
            "papers_with_review_files": len(paper_ids),
            "parsed_pdfs": len(parsed_ids),
            "papers_with_annotated_reviews": len(review_counts),
            "usable": len(usable),
            "reviewer_rows": sum(review_counts.values()),
            "unique_reviewers": len({str(review.get("OTHER_KEYS") or "")
                                    for path in sorted(reviews_dir.glob("*.json"))
                                    for review in json.loads(path.read_text()).get("reviews", [])
                                    if is_annotated_reviewer(review)}),
            "usable_papers": usable,
        }
    report.update({
        "total_papers": total_papers, "total_parsed": total_parsed,
        "total_reviewed": total_reviewed, "total_usable": total_usable,
        "total_reviewer_rows": total_reviewer_rows,
        "total_unique_reviewers": total_unique_reviewers,
        "claim_limit": "Only ICLR 2017 fixed-revision PeerRead tree; other venues not counted.",
    })
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "census.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "total_papers": total_papers, "total_parsed": total_parsed,
        "total_reviewed": total_reviewed, "total_usable": total_usable,
        "total_reviewer_rows": total_reviewer_rows,
        "total_unique_reviewers": total_unique_reviewers,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
