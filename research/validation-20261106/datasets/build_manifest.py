import argparse
import collections
import csv
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path

from fetch_pilot import FILE_LIMIT, HF_REVISION, REPOS, ROOT, TOTAL_LIMIT, utc_now, verify, write_json


EMAIL = re.compile(r"[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}")
SECRET = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,})")


def scrub(value):
    if isinstance(value, str):
        return SECRET.sub("[REDACTED_SECRET]", EMAIL.sub("[REDACTED_EMAIL]", value))
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items() if key.lower() not in ["emails", "authors"]}
    return value


def encode_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def encode_jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def read_json(root, path):
    return json.loads((root / path).read_text())


def peerread(root, products):
    paper_pairs = []
    review_rows = []
    raw_scored = 0
    excluded_unverified_role = 0
    scored_duplicates = 0
    unofficial_aspect_scores_ignored = 0
    parsed_root = root / "raw/peerread/data/iclr_2017"
    candidates = []
    for parsed_path in sorted(parsed_root.glob("*/parsed_pdfs/*.pdf.json")):
        split = parsed_path.parent.parent.name
        paper_id = parsed_path.name.removesuffix(".pdf.json")
        review_path = parsed_path.parent.parent / "reviews" / (paper_id + ".json")
        candidates.append((split, str(json.loads(review_path.read_text()).get("accepted")).lower(), parsed_path))
    selected = []
    for split in ["train", "dev", "test"]:
        for decision in ["true", "false"]:
            selected += [item for item in candidates if item[0] == split and item[1] == decision][:4]
    for split, decision, parsed_path in selected:
        paper_id = parsed_path.name.removesuffix(".pdf.json")
        review_path = parsed_path.parent.parent / "reviews" / (paper_id + ".json")
        paper = json.loads(review_path.read_text())
        parsed = json.loads(parsed_path.read_text())
        sections = parsed["metadata"].get("sections") or []
        body_characters = sum(len(section.get("text") or "") for section in sections)
        if len(sections) < 3 or body_characters < 2000:
            raise ValueError("Insufficient parsed body: " + paper_id)
        groups = collections.defaultdict(list)
        for index, review in enumerate(paper["reviews"]):
            if type(review.get("RECOMMENDATION")) not in (int, float) or review.get("IS_META_REVIEW", False):
                continue
            raw_scored += 1
            if not re.fullmatch(r"ICLR 2017 conference AnonReviewer[0-9]+", review.get("OTHER_KEYS", "")):
                excluded_unverified_role += 1
                continue
            if not (review.get("comments") or "").strip():
                raise ValueError("Scored review has no review text")
            groups[review["OTHER_KEYS"]].append((index, review))
        if not groups:
            raise ValueError("Paper has no verified reviewer recommendations")
        paper_output = f"processed/peerread/papers/{paper_id}.json"
        markers = [
            marker for marker in ["Published as a conference paper", "Under review as a conference paper"]
            if marker.lower() in parsed_path.read_text().lower()
        ]
        payload = encode_json(scrub({
            "paper_id": paper_id, "venue": paper.get("conference", "unknown"),
            "source_split": split, "title": parsed["metadata"].get("title", ""),
            "abstract": parsed["metadata"].get("abstractText", ""), "sections": sections,
            "body_characters_before_redaction": body_characters,
            "raw_parsed_path": str(parsed_path.relative_to(root)),
            "raw_parsed_sha256": sha256(parsed_path.read_bytes()),
            "submission_version_status": "unknown",
            "version_risk": "Parsed PDF may be a revision or camera-ready; not proven identical to the reviewed submission.",
            "observed_version_markers": markers,
        }))
        products[paper_output] = payload
        scores = []
        for alias, group in sorted(groups.items()):
            unique = {}
            for index, review in group:
                canonical = json.dumps(review, ensure_ascii=False, sort_keys=True)
                unique.setdefault(canonical, (index, review))
            scored_duplicates += len(group) - len(unique)
            def dated(item):
                try:
                    return datetime.strptime(item[1].get("DATE", ""), "%d %b %Y")
                except ValueError:
                    return datetime.min
            chosen_index, chosen = max(unique.values(), key=dated)
            unofficial_aspect_scores_ignored += "RECOMMENDATION_UNOFFICIAL" in chosen
            reviewer_hash = sha256(alias.encode())[:16]
            score = {
                "review_id": paper_id + ":" + reviewer_hash,
                "recommendation": chosen["RECOMMENDATION"],
                "reviewer_confidence": chosen.get("REVIEWER_CONFIDENCE", "unknown"),
                "date": chosen.get("DATE", "unknown"),
                "raw_review_index_zero_based": chosen_index,
                "all_raw_review_indices_zero_based": [index for index, _ in group],
            }
            scores.append(score)
            review_rows.append(scrub({
                **score, "paper_id": paper_id, "venue": paper.get("conference", "unknown"),
                "split": split, "paper_path": paper_output, "paper_sha256": sha256(payload),
                "review_text": chosen["comments"], "raw_review_path": str(review_path.relative_to(root)),
                "score_source_field": "RECOMMENDATION",
                "score_scale": "unknown",
                "submission_version_status": "unknown",
                "distinct_scored_versions_for_reviewer": len(unique),
            }))
        paper_pairs.append({
            "paper_id": paper_id, "venue": paper.get("conference", "unknown"), "split": split,
            "venue_decision": "accepted" if decision == "true" else "not_accepted",
            "paper_path": paper_output, "paper_sha256": sha256(payload),
            "raw_review_path": str(review_path.relative_to(root)),
            "raw_review_sha256": sha256(review_path.read_bytes()),
            "human_review_count": len(scores), "human_reviews": scores,
            "body_sections": len(sections), "body_characters": body_characters,
            "submission_version_status": "unknown", "observed_version_markers": markers,
        })
    products["processed/peerread/paper_review_pairs.jsonl"] = encode_jsonl(paper_pairs)
    products["processed/peerread/reviews.jsonl"] = encode_jsonl(review_rows)
    if len(paper_pairs) < 20 or len(review_rows) < 20:
        raise ValueError("PeerRead pilot target not met")
    by_split = {}
    for split in ["train", "dev", "test"]:
        selected = [row for row in paper_pairs if row["split"] == split]
        by_split[split] = {
            "paper_ids": [row["paper_id"] for row in selected],
            "papers": len(selected), "reviews": sum(row["human_review_count"] for row in selected),
        }
    all_ids = [row["paper_id"] for row in paper_pairs]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("Paper leakage between official splits")
    return {
        "id": "peerread-iclr2017-pilot", "repository": REPOS["peerread"][0],
        "revision": REPOS["peerread"][1], "availability": "downloaded",
        "license": "unknown", "license_evidence": "README discusses venue-specific licensing; no ICLR-specific license in pinned tree.",
        "paper_review_pairs": len(paper_pairs), "human_reviewer_recommendations": len(review_rows),
        "scored_rows_before_role_filter_and_dedup": raw_scored,
        "excluded_scored_rows_with_unverified_reviewer_role": excluded_unverified_role,
        "exact_duplicate_scored_rows_removed": scored_duplicates,
        "unique_reviewers_with_unofficial_aspect_scores_ignored": unofficial_aspect_scores_ignored,
        "score_field": "RECOMMENDATION",
        "score_scale": {
            "values": "integers 1-10", "type": "ordinal recommendation",
            "evidence": "official PeerRead paper N18-1149 §2.1: ICLR recommendations 1-10 and confidence 1-5",
            "evidence_path": "raw/peerread/peerread-N18-1149.pdf",
            "independent_live_schema_verification": "unknown (OpenReview API returned HTTP 403 challenge)",
        },
        "observed_recommendation_values": sorted({row["recommendation"] for row in review_rows}),
        "sampling": "Stratified convenience pilot: up to 4 accepted and 4 not-accepted papers per official split, ordered by paper ID, requiring a paired parsed body and official AnonReviewer recommendation. Not representative of all ICLR 2017 submissions.",
        "decision_balance": dict(collections.Counter(row["venue_decision"] for row in paper_pairs)),
        "split": by_split, "paper_disjoint": True,
        "minimum_body_characters": min(row["body_characters"] for row in paper_pairs),
        "submission_version_status": "unknown",
        "original_submission_matched_papers": 0,
        "unproven_properties": ["Original submission identity", "OCR/parse completeness", "Rubric dimension alignment", "Redistribution permission"],
        "usable_for": "Interface, pairing, and stratified accepted/not-accepted audit; exploratory analysis only while scale/version/license gates remain unresolved.",
        "excluded_target_fields": ["accepted as a score", "RECOMMENDATION_UNOFFICIAL", "ORIGINALITY", "CLARITY", "SOUNDNESS_CORRECTNESS"],
        "pairs_path": "processed/peerread/paper_review_pairs.jsonl",
        "reviews_path": "processed/peerread/reviews.jsonl",
    }


def ridar(root, products):
    annotations_path = "raw/ridar-hf/riv-gold/annotations.jsonl"
    annotations = [json.loads(line) for line in (root / annotations_path).read_text().splitlines() if line.strip()]
    annotations_by_id = {row["id"]: (index + 1, row) for index, row in enumerate(annotations)}
    if len(annotations_by_id) != len(annotations):
        raise ValueError("Duplicate RIDAR annotation IDs")
    paired = []
    for path in sorted((root / "raw/ridar-hf/riv-gold/trajectories").glob("*/trace.jsonl")):
        line_number, annotation = annotations_by_id[path.parent.name]
        trace = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        evidence_count = 0
        for behavior in annotation["behaviors"].values():
            for act in behavior["acts"]:
                for evidence in act["evidence"]:
                    if not (1 <= evidence["start"] <= evidence["end"] <= len(trace)):
                        raise ValueError("RIDAR evidence span outside the complete trajectory")
                    evidence_count += 1
        paired.append({
            "trajectory_id": path.parent.name, "split": "RIV-Gold",
            "trace_path": str(path.relative_to(root)), "trace_sha256": sha256(path.read_bytes()),
            "records": len(trace), "annotation_path": annotations_path,
            "annotation_line_one_based": line_number,
            "behaviors": annotation["behaviors"], "verified_evidence_spans": evidence_count,
        })
    products["processed/ridar/paired_trajectories.jsonl"] = encode_jsonl(scrub(paired))
    categories = sorted({category for row in annotations for category in row["behaviors"]})
    return {
        "id": "ridar-riv-gold-pilot", "repository": REPOS["ridar"][0],
        "code_revision": REPOS["ridar"][1], "dataset_revision": HF_REVISION,
        "dataset_url": "https://huggingface.co/datasets/THU-KEG/RIDAR",
        "availability": "downloaded", "license": "MIT",
        "license_evidence": ["raw/ridar/LICENSE", "raw/ridar-hf/README.md"],
        "split": "RIV-Gold; no author train/dev/test partition verified",
        "human_annotated_trajectories": len(annotations),
        "complete_downloaded_trajectories": len(paired),
        "behavior_categories_present": categories,
        "behavior_instances": sum(len(row["behaviors"]) for row in annotations),
        "annotated_acts": sum(len(behavior["acts"]) for row in annotations for behavior in row["behaviors"].values()),
        "downloaded_trace_records": sum(row["records"] for row in paired),
        "verified_evidence_spans": sum(row["verified_evidence_spans"] for row in paired),
        "sampling": "Two smallest complete RIV-Gold trace.jsonl files no larger than 2 MiB in the pinned HF tree.",
        "absent_category_semantics": "unknown; absent keys are not automatically negative labels",
        "trace_attachments": "unknown; image artifacts not downloaded",
        "model_detection_outputs_used_as_human_labels": False,
        "pairs_path": "processed/ridar/paired_trajectories.jsonl",
    }


def paperbench(root):
    prefix = "raw/paperbench/project/paperbench/"
    rubric = read_json(root, prefix + "data/papers/semantic-self-consistency/rubric.json")
    nodes = []
    def walk(node):
        nodes.append(node)
        for child in node["sub_tasks"]:
            walk(child)
    walk(rubric)
    identifiers = [node["id"] for node in nodes]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate PaperBench rubric IDs")
    splits = {}
    for path in sorted((root / (prefix + "experiments/splits")).glob("*.txt")):
        tasks = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        splits[path.stem] = {"tasks": len(tasks), "selected_task_present": "semantic-self-consistency" in tasks}
    lfs_pointers = []
    for path in sorted((root / (prefix + "data/papers/semantic-self-consistency")).glob("*.md")):
        pointer = path.read_text()
        if pointer.startswith("version https://git-lfs.github.com/spec/v1"):
            expected = re.search(r"oid sha256:([0-9a-f]{64})", pointer).group(1)
            resolved = root / "raw/paperbench/materialized" / path.name
            if sha256(resolved.read_bytes()) != expected:
                raise ValueError("LFS materialization mismatch")
            lfs_pointers.append(str(path.relative_to(root)))
    return {
        "id": "paperbench-dev-semantic-self-consistency", "repository": REPOS["paperbench"][0],
        "revision": REPOS["paperbench"][1], "availability": "task_bundle_downloaded_not_executed",
        "license": {"repository_code": "MIT", "rubric_and_judge_annotations": "unknown", "embedded_paper": "unknown"},
        "license_evidence": "raw/paperbench/LICENSE.md; root license does not establish rights to every embedded paper.",
        "task": "semantic-self-consistency", "split": "dev", "official_split_inventory": splits,
        "rubric_nodes": len(nodes), "rubric_leaf_requirements": sum(not node["sub_tasks"] for node in nodes),
        "lfs_pointers_materialized_and_oid_verified": lfs_pointers,
        "paper_markdown": "raw/paperbench/materialized/paper.md",
        "rubric": prefix + "data/papers/semantic-self-consistency/rubric.json",
        "human_judge_validation_expected_result": prefix + "data/judge_eval/semantic-self-consistency/0/grading/expected_result.json",
        "judge_validation_submission_artifacts": "not_downloaded",
        "dependencies_and_external_training_data": "unknown; not fetched",
        "end_to_end_runs": 0, "official_benchmark_score": "unknown",
        "usage": "External replication and judge-schema pilot; do not train on held-out tasks or report schema parsing as an end-to-end score.",
    }


def lightweight(root):
    existing_root = ROOT.parent / "pilot-data"
    manifest_path = existing_root / "manifest.json"
    data = json.loads(manifest_path.read_text())
    datasets = []
    for record in data["datasets"]:
        path = existing_root / record["path"]
        raw = path.read_bytes()
        exported = json.loads(raw)
        if sha256(raw) != record["sha256"]:
            raise ValueError("Existing user-exported data hash mismatch")
        if len(exported["X"]) != record["rows"] or len(exported["y"]) != record["rows"]:
            raise ValueError("Existing user-exported feature/label row mismatch")
        if any(len(row) != record["features"] for row in exported["X"]):
            raise ValueError("Existing user-exported feature count mismatch")
        datasets.append({**record, "path": str(path), "verified_features_and_labels": True})
    uci_license = {}
    for identifier in [17, 109]:
        page = (root / f"raw/uci/{identifier}-page.html").read_text()
        uci_license[str(identifier)] = "CC-BY-4.0" if "creativecommons.org/licenses/by/4.0" in page else "unknown"
    return {
        "id": "lightweight-existing-sklearn-1.9.1", "availability": "reuse_existing_user_exports",
        "manifest_path": str(manifest_path), "manifest_sha256": sha256(manifest_path.read_bytes()),
        "datasets": datasets, "split": "unsplit; user owns the six-task development split protocol",
        "local_training_or_benchmark_runs": 0,
        "download_policy": "Upstream raw files were acquired before the user's local-export update; subsequent work reuses the existing exports without downloading them again.",
        "upstream_sklearn_revision_audited": REPOS["sklearn"][1],
        "upstream_code_license": "BSD-3-Clause", "upstream_uci_dataset_licenses": uci_license,
        "diabetes_dataset_license": "unknown",
        "usage": "Development and software validation; public/model-contaminated datasets do not establish novel scientific discovery.",
    }


def build(root):
    products = {}
    datasets = [peerread(root, products), ridar(root, products), paperbench(root), lightweight(root)]
    ledger = read_json(root, "downloads.json")
    identities = {}
    for name, relative in [
        ("RIDAR", "raw/ridar/arxiv-2610.31372v1.html"),
        ("PaperBench", "raw/paperbench/arxiv-2504.01848v1.html"),
    ]:
        content = (root / relative).read_text()
        title = re.search(r'<meta name="citation_title" content="([^"]+)"', content)
        date = re.search(r'<meta name="citation_date" content="([^"]+)"', content)
        identities[name] = {
            "title": html.unescape(title.group(1)) if title else "unknown",
            "date": date.group(1) if date else "unknown", "evidence_path": relative,
        }
    manifest = {
        "schema_version": "qone-ai-researcher-datasets-v1", "audit_date": "2026-11-06",
        "generated_at_utc": utc_now(), "bounds": {
            "total_download_bytes": TOTAL_LIMIT, "payload_file_bytes": FILE_LIMIT,
            "metadata_file_bytes": 8 * 1024 * 1024, "experiments_executed": 0,
        },
        "primary_source_identity_checks": identities,
        "datasets": datasets, "raw_files": ledger["files"], "download_failures": ledger["failures"],
        "raw_downloaded_bytes": sum(row["bytes"] for row in ledger["files"]),
        "derived_files": [
            {"path": path, "bytes": len(payload), "sha256": sha256(payload)}
            for path, payload in sorted(products.items())
        ],
        "privacy": "Raw files are local and ignored by Git. Processed papers omit authors/emails; email and common credential patterns are redacted. No exhaustive secret-free guarantee is claimed.",
        "unchecked_2026_titles": "All previously listed 2026 systems except the individually verified RIDAR title remain outside this dataset acceptance.",
    }
    return products, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "verify"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_relative_to(ROOT):
        raise ValueError("Output must remain inside the authorized datasets directory")
    verify(root)
    products, manifest = build(root)
    if args.action == "build":
        for path, payload in products.items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        write_json(root / "manifest.json", manifest)
    else:
        saved = read_json(root, "manifest.json")
        manifest["generated_at_utc"] = saved["generated_at_utc"]
        if manifest != saved:
            raise ValueError("Manifest no longer matches the raw evidence")
        for path, payload in products.items():
            if (root / path).read_bytes() != payload:
                raise ValueError("Derived artifact no longer matches raw inputs: " + path)
    for path, payload in products.items():
        if EMAIL.search(payload.decode()) or SECRET.search(payload.decode()):
            raise ValueError("Unredacted email/credential pattern in processed data: " + path)
    print(json.dumps({
        "status": "pass", "action": args.action, "raw_files": len(manifest["raw_files"]),
        "derived_files": len(products), "peerread_papers": datasets_count(manifest, "paper_review_pairs"),
        "peerread_reviews": datasets_count(manifest, "human_reviewer_recommendations"),
    }))


def datasets_count(manifest, field):
    return next(dataset[field] for dataset in manifest["datasets"] if field in dataset)


if __name__ == "__main__":
    main()
