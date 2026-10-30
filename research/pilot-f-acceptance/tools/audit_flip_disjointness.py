#!/usr/bin/env python3
"""Recompute the uncorrected and continuity-corrected flip cell sets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import chi2, norm


def p_code(b: int, c: int) -> float:
    n = b + c
    return 2.0 * norm.sf(abs(b - c) / math.sqrt(n))


def p_exact(b: int, c: int) -> float:
    n = b + c
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0**n
    return min(1.0, 2.0 * tail)


def p_cc(b: int, c: int) -> float:
    n = b + c
    distance = abs(b - c)
    if distance == 0:
        return 1.0
    return float(chi2.sf((distance - 1) ** 2 / n, 1))


def cell_hash(cells: list[tuple[int, int, int]]) -> str:
    text = "\n".join(f"{b},{c},{n}" for b, c, n in sorted(cells)) + "\n"
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-root", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.overlay_root).expanduser().resolve()
    frozen_path = (
        root
        / "evidence"
        / "native"
        / "wave2-F-acceptance"
        / "revision_stats.json"
    )
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))

    uncorrected: list[tuple[int, int, int]] = []
    corrected: list[tuple[int, int, int]] = []
    for n in range(26, 501):
        for c in range(n // 2 + 1):
            b = n - c
            exact = p_exact(b, c)
            if p_code(b, c) < 0.05 and exact >= 0.05:
                uncorrected.append((b, c, n))
            if exact < 0.05 and p_cc(b, c) >= 0.05:
                corrected.append((b, c, n))

    uncorrected_set = set(uncorrected)
    corrected_set = set(corrected)
    intersection = sorted(uncorrected_set & corrected_set)
    expected_uncorrected = frozen["basic"]["flips_anti_cons"]
    expected_corrected = frozen["cc"]["flips_cons"]
    passed = (
        len(uncorrected) == expected_uncorrected
        and len(corrected) == expected_corrected
        and not intersection
    )
    report = {
        "schema": "q-one-flip-disjointness-v1",
        "generated_at": args.generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": "passed" if passed else "failed",
        "frozen_counts": {
            "uncorrected_anti_conservative": expected_uncorrected,
            "continuity_corrected_conservative": expected_corrected,
        },
        "observed_counts": {
            "uncorrected_anti_conservative": len(uncorrected),
            "continuity_corrected_conservative": len(corrected),
            "intersection": len(intersection),
        },
        "uncorrected_sha256": cell_hash(uncorrected),
        "corrected_sha256": cell_hash(corrected),
        "intersection": intersection,
        "uncorrected_examples": [
            {"b": b, "c": c, "n": n} for b, c, n in sorted(uncorrected)[:10]
        ],
        "corrected_examples": [
            {"b": b, "c": c, "n": n} for b, c, n in sorted(corrected)
        ],
        "formula_source": "tools/audit_flip_disjointness.py",
        "frozen_source": frozen_path.relative_to(root).as_posix(),
        "notes": [
            "The two sets use the same audited region n=26..500 and mirrored half-plane.",
            "The intersection is computed from full cell tuples, not only aggregate counts.",
        ],
    }
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else root / "reports" / "flip-disjointness.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"state": report["state"], **report["observed_counts"]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
