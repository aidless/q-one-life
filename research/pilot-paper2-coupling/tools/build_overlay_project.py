#!/usr/bin/env python3
"""Build a schema-valid project manifest from the current overlay receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    source = root / "source" / "main.tex"
    source_hash = sha256_file(source)

    evidence_specs = [
        (
            "evidence/source_record.json",
            "verified",
            "Canonical source identity plus the current overlay revision.",
        ),
        (
            "evidence/variant-reconciliation.json",
            "verified",
            "Canonical, duplicate, old, and drift source versions reconciled.",
        ),
        (
            "evidence/upstream/paper/main.tex",
            "verified",
            "Byte-identical canonical upstream retained before overlay edits.",
        ),
        (
            "evidence/upstream/source/CLAIM_LEDGER.md",
            "verified",
            "Native P2-C1..P2-C14 ledger retained for semantic comparison.",
        ),
        (
            "evidence/upstream/source/MANIFEST_ingest.json",
            "verified",
            "Ingest manifest for the frozen source project.",
        ),
        (
            "evidence/CARRIER_RECEIPTS.json",
            "verified",
            "Frozen numerical carrier receipts produced before the overlay.",
        ),
        (
            "evidence/carrier-audit.json",
            "verified",
            "Independent re-evaluation of every carrier receipt.",
        ),
        (
            "evidence/native-audit.json",
            "verified",
            "Evidence-boundary, citation, held-out, proof-audit and template checks.",
        ),
        (
            "evidence/upstream/source/evidence/scope_P2C11.md",
            "candidate",
            "Native scope note containing the unresolved p=0.12 drift statement.",
        ),
        (
            "evidence/upstream/source/review_real/summary.json",
            "verified",
            "Frozen role-review summary with five Major findings.",
        ),
        (
            "evidence/upstream/source/reviews/main.multi/meta-review.md",
            "verified",
            "Multi-reviewer meta-review recommending Major Revisions.",
        ),
        (
            "reports/claim-ledger-verification.md",
            "verified",
            "Six-column overlay claim-ledger verification report.",
        ),
        (
            "reports/carrier-audit.md",
            "verified",
            "Human-readable carrier receipt audit.",
        ),
        (
            "reports/source-revision.json",
            "verified",
            "Overlay-only revision binding for template and metadata hygiene.",
        ),
        (
            "reports/source-revision.diff",
            "verified",
            "Exact upstream-to-overlay source diff.",
        ),
        (
            "reports/cleanroom/receipt.json",
            "verified",
            "Two-run isolated compile receipt.",
        ),
        (
            "reports/package-audit.json",
            "verified",
            "Mechanical three-file arXiv source-tree audit.",
        ),
        (
            "reports/package/package-receipt.json",
            "verified",
            "Deterministic candidate archive and extraction compile receipt.",
        ),
        (
            "reports/package/paper2-arxiv-candidate.tar.gz",
            "verified",
            "Internal candidate archive; not upload-authorized.",
        ),
    ]
    evidence = []
    for relative, state, description in evidence_specs:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        evidence.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "state": state,
                "origin": "Paper 2 Research Factory overlay",
                "description": description,
            }
        )

    claim_specs = [
        ("C01", "Theory and experiment inventory", "candidate"),
        ("C02", "Favorable-region scope", "candidate"),
        ("C03", "Tight-bound validation scope", "candidate"),
        ("C04", "Pinsker regime scope", "candidate"),
        ("C05", "Logistic gamma estimand map", "candidate"),
        ("C06", "Conditional product-bound proof", "candidate"),
        ("C07", "T5, T6 and T8 consistency boundary", "candidate"),
        ("C08", "T7 polytope reconciliation", "candidate"),
        ("C09", "Sample-size and estimator comparability", "candidate"),
        ("C10", "Standard baselines scope", "candidate"),
        ("C11", "GPT-4o drift evidence conflict", "blocked"),
        ("C12", "Eleven condition rows and table-carrier traceability", "verified"),
        ("C13", "Reproducibility completeness boundary", "candidate"),
        ("C14", "Independent review closure", "blocked"),
    ]
    claims = [
        {
            "claim_id": claim_id,
            "location": location,
            "state": state,
            "evidence_refs": ["CLAIM_LEDGER.md", "evidence/native-audit.json"],
        }
        for claim_id, location, state in claim_specs
    ]

    cleanroom = json.loads(
        (root / "reports" / "cleanroom" / "receipt.json").read_text(
            encoding="utf-8"
        )
    )
    package_receipt = json.loads(
        (root / "reports" / "package" / "package-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    archive_hash = package_receipt["archive"]["sha256"]
    blockers = [
        "Independent proof audit of the conditional and product bounds is absent.",
        "The held-out 30-40 condition validation is absent.",
        "The native p=0.12 GPT-4o drift statement conflicts with p_bootstrap=1.0 in the frozen evidence.",
        "The T7 satisfied-cell count differs between the native scope note and the frozen output.",
        "The meta-review remains open with Major Revisions.",
        "Final author, category, abstract, license and upload authorization remain user decisions.",
    ]
    package_files = []
    for entry in package_receipt["entries"]:
        package_files.append(
            {"path": f"source/{entry['path']}", "sha256": entry["sha256"]}
        )
    package_files.extend(
        [
            {
                "path": "reports/cleanroom/receipt.json",
                "sha256": sha256_file(
                    root / "reports" / "cleanroom" / "receipt.json"
                ),
            },
            {
                "path": "reports/cleanroom/main.pdf",
                "sha256": sha256_file(root / "reports" / "cleanroom" / "main.pdf"),
            },
            {
                "path": "reports/package/package-receipt.json",
                "sha256": sha256_file(
                    root / "reports" / "package" / "package-receipt.json"
                ),
            },
            {
                "path": "reports/package/paper2-arxiv-candidate.tar.gz",
                "sha256": archive_hash,
            },
        ]
    )

    gate_specs = [
        (
            "paper2-carrier-recomputation",
            "numbers",
            "passed",
            "evidence/carrier-audit.json",
            "All 176 frozen carrier receipts resolve and match their printed values.",
        ),
        (
            "paper2-citation-resolution",
            "citations",
            "passed",
            "evidence/native-audit.json",
            "All seven cite keys resolve to local bibitems.",
        ),
        (
            "paper2-source-identity",
            "reproducibility",
            "passed",
            "evidence/source_record.json",
            "The canonical and overlay source hashes are bound explicitly.",
        ),
        (
            "paper2-cleanroom-compile",
            "package",
            "passed",
            "reports/cleanroom/receipt.json",
            "Two isolated compiles produced byte-identical 14-page PDFs.",
        ),
        (
            "paper2-package-audit",
            "package",
            "passed",
            "reports/package-audit.json",
            "The three-file source tree passes the mechanical arXiv audit.",
        ),
        (
            "paper2-candidate-archive",
            "package",
            "passed",
            "reports/package/package-receipt.json",
            "The archive rebuild is deterministic and extracts to a 14-page compile.",
        ),
        (
            "paper2-proof-audit",
            "review",
            "blocked",
            "evidence/native-audit.json",
            "No independent proof audit receipt exists for the current source.",
        ),
        (
            "paper2-heldout-validation",
            "numbers",
            "blocked",
            "evidence/native-audit.json",
            "No held-out condition dataset or validation receipt exists.",
        ),
        (
            "paper2-scientific-review",
            "review",
            "blocked",
            "evidence/upstream/source/reviews/main.multi/meta-review.md",
            "The meta-review still recommends Major Revisions.",
        ),
        (
            "paper2-metadata-license",
            "other",
            "blocked",
            "reports/package/package-receipt.json",
            "Final author, category, abstract, license and upload authorization remain unconfirmed.",
        ),
    ]
    gate_receipts = []
    for gate_id, scope, state, relative, summary in gate_specs:
        receipt = root / relative
        gate_receipts.append(
            {
                "gate_id": gate_id,
                "scope": scope,
                "state": state,
                "receipt": relative,
                "receipt_sha256": sha256_file(receipt),
                "source_sha256": source_hash,
                "summary": summary,
            }
        )

    project = {
        "schema": "q-one-research-project-v1",
        "paper_id": "qf-a-conditional-coupling-diversity-precisi-7336590fb7",
        "title": "A Conditional Coupling--Diversity--Precision Bound for TTRL-Based LLM Evaluation",
        "status": "review_pending",
        "target": "arxiv",
        "root": str(root),
        "origin": (
            "<WORKSPACE_ROOT>/Projects/agi-paper-pipeline/runs/"
            "tmlr-paper2-consolidated/paper/main.tex"
        ),
        "manuscript": {
            "path": "source/main.tex",
            "sha256": source_hash,
            "published_source_sha256": None,
            "matches_published_source": None,
            "source_url": None,
        },
        "evidence": evidence,
        "claims": claims,
        "experiments": [
            {
                "experiment_id": "paper2-carrier-recomputation",
                "state": "reproduced",
                "receipt": "evidence/carrier-audit.json",
                "environment_sha256": None,
            },
            {
                "experiment_id": "paper2-cleanroom-compile",
                "state": "reproduced",
                "receipt": "reports/cleanroom/receipt.json",
                "environment_sha256": None,
            },
            {
                "experiment_id": "paper2-candidate-archive",
                "state": "reproduced",
                "receipt": "reports/package/package-receipt.json",
                "environment_sha256": None,
            },
            {
                "experiment_id": "paper2-heldout-validation",
                "state": "blocked",
                "receipt": "evidence/native-audit.json",
                "environment_sha256": None,
            },
            {
                "experiment_id": "paper2-independent-proof-audit",
                "state": "blocked",
                "receipt": "evidence/native-audit.json",
                "environment_sha256": None,
            },
        ],
        "reviews": [
            {
                "review_id": "paper2-role-review-r6",
                "kind": "method",
                "state": "open",
                "critical": 0,
                "major": 5,
                "receipt": "evidence/upstream/source/review_real/summary.json",
            },
            {
                "review_id": "paper2-multi-reviewer-meta-review",
                "kind": "statistics",
                "state": "open",
                "critical": 3,
                "major": 5,
                "receipt": (
                    "evidence/upstream/source/reviews/main.multi/meta-review.md"
                ),
            },
        ],
        "package": {
            "state": "compiled",
            "files": package_files,
            "blockers": blockers,
        },
        "gate_receipts": gate_receipts,
        "measurements": [
            {
                "name": "carrier_receipts_passed",
                "value": 176,
                "unit": "checks",
                "definition": "Frozen carrier fields and printed manuscript values passing re-evaluation.",
                "source": "evidence/carrier-audit.json#summary.passed",
                "state": "observed",
            },
            {
                "name": "carrier_receipts_failed",
                "value": 0,
                "unit": "checks",
                "definition": "Frozen carrier fields or printed values failing re-evaluation.",
                "source": "evidence/carrier-audit.json#summary.failed",
                "state": "observed",
            },
            {
                "name": "cleanroom_pdf_pages",
                "value": cleanroom["pdf"]["pages"],
                "unit": "pages",
                "definition": "Pages in the deterministic clean-room PDF.",
                "source": "reports/cleanroom/receipt.json#pdf.pages",
                "state": "observed",
            },
            {
                "name": "source_package_files",
                "value": len(package_receipt["entries"]),
                "unit": "files",
                "definition": "Files admitted to the internal arXiv candidate archive.",
                "source": "reports/package/package-receipt.json#entries",
                "state": "observed",
            },
            {
                "name": "candidate_archive_bytes",
                "value": package_receipt["archive"]["bytes"],
                "unit": "bytes",
                "definition": "Size of the deterministic internal candidate archive.",
                "source": "reports/package/package-receipt.json#archive.bytes",
                "state": "observed",
            },
            {
                "name": "bound_decision_rows",
                "value": 11,
                "unit": "rows",
                "definition": "Condition rows in the frozen sample-size decision case.",
                "source": "evidence/native-audit.json#counts.bound_decision_rows",
                "state": "observed",
            },
            {
                "name": "heldout_data_files",
                "value": 0,
                "unit": "files",
                "definition": "Held-out condition datasets in the frozen upstream evidence.",
                "source": "evidence/native-audit.json#counts.heldout_data_files",
                "state": "blocked",
            },
            {
                "name": "proof_audit_receipts",
                "value": 0,
                "unit": "receipts",
                "definition": "Independent proof-audit receipts in the frozen upstream evidence.",
                "source": "evidence/native-audit.json#counts.proof_audit_receipts",
                "state": "blocked",
            },
        ],
        "notes": [
            "The upstream manuscript is preserved byte-for-byte.",
            "The overlay edits only packaging, scope wording and off-topic template text.",
            "All 176 frozen numerical carrier receipts pass re-evaluation.",
            "Only condition-table traceability is verified; proof and held-out validation remain blocked.",
            "The internal candidate archive is not authorized for upload.",
        ],
    }
    output = root / "project.json"
    output.write_text(
        json.dumps(project, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "project": str(output),
                "source_sha256": source_hash,
                "claims": len(claims),
                "gate_receipts": len(gate_receipts),
                "package_files": len(package_files),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
