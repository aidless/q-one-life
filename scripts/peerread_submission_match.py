"""Match PeerRead raw parsed_pdfs against the pilot's parsed papers."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode())


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = args.root / "raw/peerread/data/iclr_2017"
    processed = args.root / "processed/peerread"

    raw_records = {}
    for split in ("train", "dev", "test"):
        directory = raw / split / "parsed_pdfs"
        for path in sorted(directory.glob("*.json")):
            record = json.loads(path.read_text())
            metadata = record.get("metadata") or {}
            title = metadata.get("title") or ""
            authors = metadata.get("authors") or []
            sections = metadata.get("sections") or []
            body = "\n".join(
                (section.get("heading") or "") + "\n" + (section.get("text") or "")
                for section in sections
            )
            raw_records[path.name.split(".")[0]] = {
                "split": split, "title": title, "authors": authors,
                "sections": sections, "body": body,
                "body_sha256": sha256_text(body),
                "raw_path": str(path),
            }

    pairs_path = processed / "paper_review_pairs.jsonl"
    pairs = [json.loads(line) for line in pairs_path.read_text().splitlines() if line.strip()]
    matched = []
    unmatched = []
    for pair in pairs:
        paper_id = pair["paper_id"]
        raw_record = raw_records.get(paper_id)
        paper_record = json.loads((args.root / pair["paper_path"]).read_text())
        if raw_record is None:
            unmatched.append({"paper_id": paper_id, "reason": "no_raw_parsed_pdf"})
            continue
        raw_sections = raw_record["sections"]
        processed_sections = paper_record.get("sections") or []
        processed_body = "\n".join(
            (section.get("heading") or "") + "\n" + (section.get("text") or "")
            for section in processed_sections
        )
        matched.append({
            "paper_id": paper_id,
            "split": pair["split"],
            "raw_title": raw_record["title"],
            "processed_title": paper_record.get("title"),
            "title_match": normalize(raw_record["title"]) == normalize(paper_record.get("title") or ""),
            "raw_authors": raw_record["authors"],
            "processed_authors": paper_record.get("authors", paper_record.get("metadata", {}).get("authors", [])),
            "raw_body_sha256": raw_record["body_sha256"],
            "processed_body_sha256": sha256_text(processed_body),
            "body_identical": raw_record["body_sha256"] == sha256_text(processed_body),
            "raw_section_count": len(raw_sections),
            "processed_section_count": len(processed_sections),
            "raw_path": raw_record["raw_path"],
        })

    identical = [item for item in matched if item["body_identical"]]
    title_match = [item for item in matched if item["title_match"]]
    report = {
        "schema": "qone-peerread-submission-match-v1",
        "pilot_papers": len(pairs),
        "raw_parsed_pdfs_available": len(raw_records),
        "matched": len(matched),
        "unmatched": unmatched,
        "body_identical": len(identical),
        "title_match": len(title_match),
        "raw_section_distribution": dict(Counter(item["raw_section_count"] for item in matched)),
        "processed_section_distribution": dict(Counter(item["processed_section_count"] for item in matched)),
        "detail": matched,
        "claim_limit": (
            "Body identity compares the pilot's processed sections against the repository's "
            "parsed_pdfs metadata. It is not proof that the PDF is the reviewed submission version."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "match.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "pilot_papers": len(pairs), "raw_parsed_pdfs": len(raw_records),
        "matched": len(matched), "body_identical": len(identical),
        "title_match": len(title_match),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
