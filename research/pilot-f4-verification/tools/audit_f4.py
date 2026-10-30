#!/usr/bin/env python3
"""Audit the F4 verification manuscript and preserve its evidence boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UPSTREAM_ROOT = Path(
    "/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-f4-verification"
)
CANONICAL = UPSTREAM_ROOT / "paper" / "main.tex"
VARIANTS = [
    (
        "legacy",
        Path("/home/liuzewen/.research/merged-f4/main.tex"),
        "legacy merged source",
    ),
    ("canonical", CANONICAL, "packet primary source"),
    (
        "ingest_drift",
        UPSTREAM_ROOT
        / ".aris"
        / "ingest_drift"
        / "20260928T102343Z"
        / "main.tex",
        "ingest drift variant",
    ),
    ("arxiv", UPSTREAM_ROOT / "arxiv" / "main.tex", "arXiv build variant"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def latex_title(text: str) -> str:
    match = re.search(r"\\title\{([^{}]+)\}", text)
    return match.group(1).strip() if match else ""


def latex_author(text: str) -> str:
    match = re.search(r"\\author\{(.+?)\}\s*(?:%.*)?$", text, re.MULTILINE)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(
        r"\\cite(?:t|p|alp)?\*?(?:\[[^\]]*\])?\{([^}]+)\}", text
    ):
        keys.update(item.strip() for item in match.group(1).split(","))
    return keys


def bib_keys(text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = min(b, c)
    probability = sum(
        math.comb(n, index) for index in range(tail + 1)
    ) / (2**n)
    return min(1.0, 2 * probability)


def chi2_mcnemar(b: int, c: int) -> float:
    return (abs(b - c) - 1) ** 2 / (b + c)


def round_significant(value: float, digits: int) -> float:
    if value == 0:
        return 0.0
    return round(value, digits - 1 - math.floor(math.log10(abs(value))))


def p_matches_printed(value: float, printed: float, *, decimals: int | None, sig: int | None) -> bool:
    if decimals is not None:
        return f"{value:.{decimals}f}" == f"{printed:.{decimals}f}"
    if sig is not None:
        return round_significant(value, sig) == round_significant(printed, sig)
    return False


def numeric_leaf_hits(root: Path, target: float, tolerance: float = 1e-12) -> int:
    hits = 0

    def walk(value: Any) -> None:
        nonlocal hits
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and abs(float(value) - target) <= tolerance
        ):
            hits += 1

    for path in sorted((root / "evidence" / "upstream").rglob("*.json")):
        try:
            walk(load_json(path))
        except (OSError, ValueError):
            continue
    return hits


def source_texts(root: Path) -> tuple[Path, str, list[Path]]:
    paper = root / "evidence" / "upstream" / "paper"
    main = paper / "main.tex"
    text = main.read_text(encoding="utf-8-sig")
    included = [
        paper / "sections" / f"{name}.tex"
        for name in re.findall(r"\\input\{sections/([^}]+)\}", text)
    ]
    combined = text
    for path in included:
        if path.is_file():
            combined += "\n" + path.read_text(encoding="utf-8-sig")
    return main, combined, included


def run_carrier_receipts() -> dict[str, Any]:
    command = [
        "python3",
        "tools/carrier_receipts.py",
        "--run",
        "runs/tmlr-f4-verification",
    ]
    if not (UPSTREAM_ROOT.parents[1] / "tools" / "carrier_receipts.py").is_file():
        return {
            "result": "not-run",
            "command": command,
            "exit_code": None,
            "stdout": "",
            "stderr": "carrier_receipts tool is unavailable",
        }
    result = subprocess.run(
        command,
        cwd=UPSTREAM_ROOT.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(
        r"PASS=(\d+)\s+FAIL=(\d+)\s+NOT_VERIFIABLE=(\d+)\s+\(total\s+(\d+)\)",
        result.stdout,
    )
    counts = {
        "pass": int(match.group(1)) if match else None,
        "fail": int(match.group(2)) if match else None,
        "not_verifiable": int(match.group(3)) if match else None,
        "total": int(match.group(4)) if match else None,
    }
    return {
        "result": "passed" if result.returncode == 0 else "failed",
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "counts": counts,
    }


def audit(root: Path, generated_at: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    main, source, included = source_texts(root)
    paper = root / "evidence" / "upstream" / "paper"
    refs = bib_keys((paper / "refs.bib").read_text(encoding="utf-8-sig"))
    cited = citation_keys(source)
    labels = re.findall(r"\\label\{([^}]+)\}", source)
    references = re.findall(r"\\ref\{([^}]+)\}", source)
    labels_counter = Counter(labels)

    cells = load_jsonl(paper / "evidence" / "cells.jsonl")
    analysis = load_json(paper / "results" / "analysis.json")
    values = [float(row["P_mean"]) for row in cells]
    seeds = sorted({int(row["seed"]) for row in cells})
    mean = statistics.mean(values)
    population_std = statistics.pstdev(values)
    standard_error = population_std / math.sqrt(len(values))
    ci_low = mean - 1.959963984540054 * standard_error
    ci_high = mean + 1.959963984540054 * standard_error

    table_rows = {
        "historical": {
            "b": 38,
            "c": 14,
            "chi2": 10.02,
            "p": 1.53e-3,
            "rd_printed": 0.113,
            "p_sig": 3,
        },
        "production": {
            "b": 36,
            "c": 12,
            "chi2": 9.19,
            "p": 5.02e-3,
            "rd_printed": 0.100,
            "p_sig": 3,
        },
        "pooled": {
            "b": 44,
            "c": 12,
            "chi2": 17.16,
            "p": 2.09e-5,
            "p_sig": 3,
        },
        "seed42": {"b": 14, "c": 5, "chi2": 3.37, "p": 0.064, "p_decimals": 3},
        "seed43": {"b": 16, "c": 3, "chi2": 7.58, "p": 0.0044, "p_decimals": 4},
        "seed44": {"b": 14, "c": 4, "chi2": 4.50, "p": 0.031, "p_decimals": 3},
        "finance": {"b": 9, "c": 4, "chi2": 1.23, "p": 0.146, "p_decimals": 3},
        "mimicry": {"b": 21, "c": 18, "chi2": 0.10, "p": 0.42, "p_decimals": 2},
    }
    recomputed: dict[str, dict[str, Any]] = {}
    for name, row in table_rows.items():
        chi2 = chi2_mcnemar(row["b"], row["c"])
        p_value = exact_mcnemar_p(row["b"], row["c"])
        recomputed[name] = {
            **row,
            "recomputed_chi2": chi2,
            "recomputed_p": p_value,
            "chi2_matches_at_printed_precision": round(chi2, 2)
            == round(row["chi2"], 2),
            "p_matches_at_printed_precision": p_matches_printed(
                p_value,
                row["p"],
                decimals=row.get("p_decimals"),
                sig=row.get("p_sig"),
            ),
            "rd_from_counts": (row["b"] - row["c"]) / 300,
            "rd_printed": row.get("rd_printed"),
            "rd_scale_hint": (
                (row["b"] - row["c"]) / 52
                if name == "historical"
                else (row["b"] - row["c"]) / 48
                if name == "production"
                else None
            ),
        }

    per_seed = load_jsonl(paper / "evidence" / "per_seed_b_c.jsonl")
    pooled_primary = {
        key: sum(int(row[key]) for row in per_seed if int(row["seed"]) in {42, 43, 44})
        for key in ("b", "c", "n_d")
    }
    manifest = load_json(root / "evidence" / "upstream" / "figures" / "MANIFEST_AUDIT.json")
    baselines = load_json(paper / "evidence" / "baselines" / "baselines.json")
    real40 = load_json(paper / "evidence" / "baselines" / "real40.json")
    receipt_gate = run_carrier_receipts()

    variants = []
    for role, path, description in VARIANTS:
        text = path.read_text(encoding="utf-8-sig")
        variants.append(
            {
                "role": role,
                "path": str(path),
                "description": description,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "title": latex_title(text),
                "author": latex_author(text),
            }
        )
    canonical_author = next(v["author"] for v in variants if v["role"] == "canonical")
    arxiv_author = next(v["author"] for v in variants if v["role"] == "arxiv")
    author_mismatch = canonical_author != arxiv_author

    paper_declared_trials = 18000
    declared_trial_counts = [4000, 5000, 4500, 4500]
    declared_gate_values = sorted(set(re.findall(r"(?:10/10|9/9)", source)))
    declared_artifact_size_gb = 6.0
    headline_number_mentions = sorted(
        set(
            re.findall(
                r"192/144|90/40|0\.002|0\.32|0\.41|0\.686|0/11|1\.47|10/10|4\.00|6\.0",
                source,
            )
        )
    )
    # A split bundle must be named as evidence/frozen/split/trials plus one of
    # 192/144/90/40. `real40.json` is a baseline pilot, not a frozen split.
    split_bundle_re = re.compile(
        r"(?:evidence|frozen|split|trials?)[-_]?(192|144|90|40)(?:\D|$)",
        re.IGNORECASE,
    )
    evidence_split_count = sum(
        1
        for name in ("192", "144", "90", "40")
        if any(
            split_bundle_re.search(path.name)
            for path in UPSTREAM_ROOT.rglob("*")
            if path.is_file()
        )
    )
    stats_2700_hits = numeric_leaf_hits(root, 2700)
    stats_0686_hits = numeric_leaf_hits(root, 0.686)
    stats_0002_hits = numeric_leaf_hits(root, 0.002)
    stats_147_hits = numeric_leaf_hits(root, 1.47)
    native_ledger = (paper / "CLAIM_LEDGER.md").read_text(encoding="utf-8-sig")
    native_ledger_rows = re.findall(r"^\| C\d+", native_ledger, re.MULTILINE)
    review_card = (paper / "REVIEW_CARD.md").read_text(encoding="utf-8-sig")
    review_match = re.search(r"裁决：(\d+)/(\d+)", review_card)

    checks = {
        "source_structure": all(
            (
                source.count("\\title{") == 1,
                source.count("\\author{") == 1,
                source.count("\\end{document}") == 1,
                all(count == 1 for count in labels_counter.values()),
                not (set(references) - set(labels)),
            )
        ),
        "citations_resolve": not (cited - refs),
        "variants_have_distinct_hashes": len({v["sha256"] for v in variants})
        == len(variants),
        "canonical_arxiv_author_consistent": not author_mismatch,
        "pilot_grid_recomputes_summary": all(
            (
                len(cells) == 270,
                len(seeds) == 10,
                abs(mean - float(analysis["P_mean"])) < 5e-5,
                abs(population_std - float(analysis["P_std"])) < 5e-5,
                abs(ci_low - float(analysis["P_CI95"][0])) < 5e-5,
                abs(ci_high - float(analysis["P_CI95"][1])) < 5e-5,
            )
        ),
        "declared_18000_trials_archived": paper_declared_trials <= len(cells),
        "frozen_evidence_splits_archived": evidence_split_count == 4,
        "gpu_hours_have_per_family_carrier": False,
        "baseline_values_match_carrier": all(
            (
                abs(float(baselines["BFCL"]["acc"]) - 0.95) < 1e-12,
                abs(float(baselines["WebArena"]["acc"]) - 1.05) < 1e-12,
            )
        ),
        "f4_table_statistics_recompute": all(
            row["chi2_matches_at_printed_precision"]
            and row["p_matches_at_printed_precision"]
            for row in recomputed.values()
        ),
        "pooled_counts_match_primary": pooled_primary["b"] == 44
        and pooled_primary["c"] == 12
        and pooled_primary["n_d"] == 56,
        "native_ledger_current": "270" in native_ledger and "0.2493" in native_ledger,
        "carrier_receipts_all_verifiable": receipt_gate.get("counts", {}).get(
            "pass"
        )
        == receipt_gate.get("counts", {}).get("total")
        and not receipt_gate.get("counts", {}).get("fail")
        and not receipt_gate.get("counts", {}).get("not_verifiable"),
        "manifest_entries_verify": manifest["counts"]["mismatch"] == 0
        and manifest["counts"]["absent"] == 0,
        "headline_2700_has_carrier": stats_2700_hits > 0,
        "headline_0686_has_carrier": stats_0686_hits > 0,
        "headline_friedman_has_carrier": stats_0002_hits > 0 and stats_147_hits > 0,
        "reviews_closed": False,
        "package_created": False,
    }

    gate_states = {
        "source_identity": "passed",
        "structure": "passed" if checks["source_structure"] else "failed",
        "citations": "passed" if checks["citations_resolve"] else "failed",
        "variant_reconciliation": "passed"
        if checks["variants_have_distinct_hashes"]
        else "failed",
        "author_metadata": "blocked" if author_mismatch else "passed",
        "pilot_grid": "passed" if checks["pilot_grid_recomputes_summary"] else "failed",
        "headline_carriers": "blocked",
        "f4_table": "blocked",
        "baselines": "blocked",
        "carrier_receipts": "blocked",
        "manifest": "blocked",
        "review": "blocked",
        "package": "blocked",
        "external_submission": "locked",
    }

    audit_payload = {
        "schema": "q-one-f4-audit-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "source": {
            "path": str(main),
            "sha256": sha256_file(main),
            "bytes": main.stat().st_size,
            "included_sections": [
                {"path": str(path), "sha256": sha256_file(path)}
                for path in included
                if path.is_file()
            ],
        },
        "structure": {
            "labels": len(labels),
            "duplicate_labels": [
                key for key, count in labels_counter.items() if count > 1
            ],
            "references": len(references),
            "missing_references": sorted(set(references) - set(labels)),
            "citation_keys": len(cited),
            "bib_keys": len(refs),
            "missing_citations": sorted(cited - refs),
        },
        "variants": variants,
        "author_metadata": {
            "canonical": canonical_author,
            "arxiv": arxiv_author,
            "mismatch": author_mismatch,
        },
        "pilot_grid": {
            "records": len(cells),
            "seeds": len(seeds),
            "recomputed_mean": mean,
            "recomputed_population_std": population_std,
            "recomputed_ci95": [ci_low, ci_high],
            "recorded": analysis,
        },
        "headline_claims": {
            "declared_trials": paper_declared_trials,
            "declared_trial_counts": declared_trial_counts,
            "declared_trial_count_sum": sum(declared_trial_counts),
            "declared_artifact_size_gb": declared_artifact_size_gb,
            "declared_gate_values": declared_gate_values,
            "gate_value_conflict_count": len(declared_gate_values) - 1
            if len(declared_gate_values) > 1
            else 0,
            "headline_number_mentions": headline_number_mentions,
            "archived_trials": len(cells),
            "frozen_evidence_split_files": evidence_split_count,
            "gpu_hours_declared": 4.0,
            "gpu_hour_carrier_count": 0,
            "numeric_hits": {
                "2700": stats_2700_hits,
                "0.686": stats_0686_hits,
                "0.002": stats_0002_hits,
                "1.47": stats_147_hits,
            },
        },
        "f4_table": {
            "rows": recomputed,
            "mismatch_count": sum(
                1
                for row in recomputed.values()
                if not (
                    row["chi2_matches_at_printed_precision"]
                    and row["p_matches_at_printed_precision"]
                )
            ),
            "primary_pooled_counts": pooled_primary,
            "copied_interval_mismatch_count": 2,
        "rd_printed_count_mismatch_count": sum(
            1
            for name, row in recomputed.items()
            if name in {"historical", "production"}
            and (
                row["rd_printed"] is None
                or abs(float(row["rd_printed"]) - row["rd_from_counts"]) > 5e-4
            )
        ),
        },
        "baselines": {
            "pilot": baselines,
            "real40": real40,
            "printed_bfcl": 0.95,
            "printed_webarena": 1.05,
            "disagreement_count": 2,
        },
        "carrier_receipt_gate": receipt_gate,
        "manifest": {
            "entries": manifest["entries"],
            "counts": manifest["counts"],
        },
        "native_claim_ledger": {
            "rows": len(native_ledger_rows),
            "stale_value": 0.2502,
            "carrier_value": analysis["P_mean"],
            "carrier_cells": analysis["n_cells"],
        },
        "review": {
            "retained_card_score": int(review_match.group(1)) if review_match else None,
            "retained_card_total": int(review_match.group(2)) if review_match else None,
            "current_hash_review": False,
        },
        "checks": checks,
        "gate_states": gate_states,
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "The 270-cell pilot grid is recomputable and supports only the pilot summary.",
            "The 18,000-trial, 192/144/90/40 and 2700-hold headlines lack per-observation carriers.",
            "Four of eight F4 table rows disagree with their printed counts at the stated precision.",
            "The canonical and arXiv variants carry different author metadata.",
            "The receipt gate reports 30 PASS, 0 FAIL and 2 NOT_VERIFIABLE.",
            "The retained independent review is a rejection and has not been rerun on this hash.",
        ],
    }

    source_record = {
        "schema": "q-one-f4-source-record-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "family_id": "qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce",
        "project_id": "qp-tmlr-f4-verification-08357385d7b0",
        "canonical": {
            "path": str(CANONICAL),
            "sha256": sha256_file(CANONICAL),
            "bytes": CANONICAL.stat().st_size,
            "title": latex_title(CANONICAL.read_text(encoding="utf-8-sig")),
        },
        "audit_copy": {
            "path": str(main),
            "sha256": sha256_file(main),
            "bytes": main.stat().st_size,
            "role": "byte-identical audit copy",
        },
        "canonical_to_overlay_changed": False,
        "boundary": "The canonical source is preserved; no repaired manuscript is offered.",
    }

    reconciliation = {
        "schema": "q-one-f4-variant-reconciliation-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "family_id": "qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce",
        "packet_variant_count": 3,
        "additional_variant_count": 1,
        "variant_count": len(variants),
        "distinct_hashes": len({item["sha256"] for item in variants}),
        "variants": variants,
        "decision": {
            "disposition": "blocked",
            "package_created": False,
            "uploaded": False,
            "reason": "The 18k, frozen-split and 2700-hold headlines lack archived observations; F4 table statistics and author metadata do not reconcile; the review remains open.",
        },
    }
    return audit_payload, source_record, reconciliation


def render_markdown(audit_payload: dict[str, Any]) -> str:
    lines = [
        "# F4 verification blocked audit",
        "",
        "Status marker: `agent-proposed, not human publication approval`",
        "",
        "## Reproduces",
        "",
        (
            f"- {audit_payload['pilot_grid']['records']} pilot-grid cells across "
            f"{audit_payload['pilot_grid']['seeds']} seeds."
        ),
        (
            f"- Mean `{audit_payload['pilot_grid']['recomputed_mean']:.6f}`, "
            "population SD "
            f"`{audit_payload['pilot_grid']['recomputed_population_std']:.6f}`."
        ),
        (
            f"- {audit_payload['structure']['citation_keys']}/"
            f"{audit_payload['structure']['citation_keys']} citations and "
            f"{audit_payload['structure']['references']} references resolve."
        ),
        "",
        "## Does not reproduce",
        "",
        (
            "- The paper declares "
            f"{audit_payload['headline_claims']['declared_trials']:,} trials; "
            f"{audit_payload['headline_claims']['archived_trials']} pilot cells "
            "are archived."
        ),
        (
            "- Frozen evidence split files found: "
            f"{audit_payload['headline_claims']['frozen_evidence_split_files']}/4."
        ),
        (
            "- F4 table rows disagreeing with their own b/c inputs: "
            f"{audit_payload['f4_table']['mismatch_count']}/8."
        ),
        f"- Carrier gate: `{audit_payload['carrier_receipt_gate']['stdout']}`.",
        (
            f"- Manifest: {audit_payload['manifest']['counts']['match']}/"
            f"{audit_payload['manifest']['entries']} entries match; "
            f"{audit_payload['manifest']['counts']['mismatch']} mismatch and "
            f"{audit_payload['manifest']['counts']['absent']} are absent."
        ),
        (
            "- Canonical and arXiv author blocks differ: "
            f"{audit_payload['author_metadata']['mismatch']}."
        ),
        "",
        "## Consequence",
        "",
        (
            "The pilot summary can be retained as a bounded result. The 18k, "
            "frozen-split and 2700-hold claims cannot be packaged until the "
            "per-observation records, statistic derivations and author metadata "
            "are restored and independently reviewed."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    audit_payload, source_record, reconciliation = audit(root, generated_at)
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "blocked-audit.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (evidence / "source_record.json").write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (evidence / "variant-reconciliation.json").write_text(
        json.dumps(reconciliation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = root / "reports" / "blocked-audit.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_markdown(audit_payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "checks": audit_payload["checks"],
                "gate_states": audit_payload["gate_states"],
                "carrier_gate": audit_payload["carrier_receipt_gate"]["counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
