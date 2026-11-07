"""C03 构造效度审计：原文的强主张是否已被收窄。

这不是构造效度的证明。它只验证当前源码是否明确采用 A1 建议的窄主张：
规则回答"是否超过金标生产者"，不估计排名错误率，也不证明两个系统可区分。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "q-one-rebuttal-experiment-v1"
EXPERIMENT_ID = "C03-construct-audit"

NARROW_MARKERS = {
    "does_not_estimate_ranking_error": "does not estimate a ranking error rate",
    "does_not_certify_distinguishable": (
        "does not certify that two systems are distinguishable"
    ),
    "necessary_not_sufficient": (
        "necessary condition for citing the top of a board"
    ),
    "perfect_gold_counterexample": (
        "refused even though that ordering is plainly resolvable"
    ),
}

ORIGINAL_CLAIM = (
    "measures leaderboard readability rather than only agreement with the "
    "gold producers"
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.home())
    except ValueError:
        return str(path)
    return f"<HOME>/{relative.as_posix()}"


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    ledger_path = Path(args.ledger).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    source_bytes = source_path.read_bytes()
    ledger_bytes = ledger_path.read_bytes()
    source_text = _normalized(source_bytes.decode("utf-8", errors="replace"))
    ledger_text = ledger_bytes.decode("utf-8", errors="replace")

    paragraph = ""
    marker = "What the rule certifies"
    start = source_text.find(marker)
    if start != -1:
        paragraph = source_text[start:start + 1800]

    checks = {
        name: needle in paragraph for name, needle in NARROW_MARKERS.items()
    }
    checks["original_claim_absent_from_source"] = ORIGINAL_CLAIM not in source_text
    checks["paragraph_found"] = bool(paragraph)

    narrowed = all(checks.values())
    verdict = "narrowed" if narrowed else "not_narrowed"

    c03_line = ""
    for line in ledger_text.splitlines():
        if re.match(r"^\|\s*C03\s*\|", line):
            c03_line = line.strip()
            break

    receipt = {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "generated_at": _now(),
        "claim_id": "C03",
        "ledger_row": c03_line,
        "original_claim": ORIGINAL_CLAIM,
        "inputs": {
            "source": {
                "path": _portable(source_path),
                "sha256": _sha256(source_bytes),
            },
            "ledger": {
                "path": _portable(ledger_path),
                "sha256": _sha256(ledger_bytes),
            },
            "paragraph_sha256": _sha256(paragraph.encode("utf-8")),
        },
        "checks": checks,
        "verdict": verdict,
        "note": (
            "narrowed 表示当前源码采用窄主张，原 C03 强主张已被撤回；"
            "这不等于构造效度已被证明。"
        ),
    }
    receipt_path = out / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "verdict": verdict,
        "checks": checks,
        "receipt": str(receipt_path),
        "receipt_sha256": _sha256(receipt_path.read_bytes()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
