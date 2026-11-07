"""C04 证据审计：disjoint-field 部署是否产生过 READABLE。

从四臂计数载体逐臂求和，并检查正文是否报告 0 certifications。
不重新跑 3,200 个 board，只核对落盘计数与正文一致性。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "q-one-rebuttal-experiment-v1"
EXPERIMENT_ID = "C04-disjoint-audit"

SOURCE_MARKERS = {
    "reports_zero_certifications": "0 certifications",
    "reports_never_readable": "never \\texttt{READABLE}",
    "reports_3200_boards": "3,200 boards",
}


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
    parser.add_argument("--counts", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    counts_path = Path(args.counts).expanduser().resolve()
    source_path = Path(args.source).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    counts_bytes = counts_path.read_bytes()
    source_bytes = source_path.read_bytes()
    counts = json.loads(counts_bytes.decode("utf-8"))
    source_text = _normalized(source_bytes.decode("utf-8", errors="replace"))

    arms = counts.get("arms", {})
    unreadable = sum(int(arm.get("UNREADABLE", 0)) for arm in arms.values())
    marginal = sum(int(arm.get("MARGINAL", 0)) for arm in arms.values())
    total_boards = int(counts.get("total_boards", 0))
    readable = total_boards - unreadable - marginal

    reported_total = counts.get("total", {})
    checks = {
        "arm_sums_match_total_unreadable": unreadable == int(reported_total.get("UNREADABLE", -1)),
        "arm_sums_match_total_marginal": marginal == int(reported_total.get("MARGINAL", -1)),
        "counts_sum_to_3200": total_boards == 3200 and unreadable + marginal == 3200,
        "readable_is_zero": readable == 0,
    }
    for name, needle in SOURCE_MARKERS.items():
        checks[name] = needle in source_text

    verdict = "refuted" if all(checks.values()) else "not_refuted"

    receipt = {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "generated_at": _now(),
        "claim_id": "C04",
        "claim": (
            "A real public leaderboard with a gold pool disjoint from the "
            "ranked systems has produced a READABLE verdict."
        ),
        "inputs": {
            "counts": {
                "path": _portable(counts_path),
                "sha256": _sha256(counts_bytes),
            },
            "source": {
                "path": _portable(source_path),
                "sha256": _sha256(source_bytes),
            },
        },
        "counts": {
            "arms": {name: arm for name, arm in sorted(arms.items())},
            "total_boards": total_boards,
            "unreadable": unreadable,
            "marginal": marginal,
            "readable": readable,
        },
        "checks": checks,
        "verdict": verdict,
        "note": (
            "refuted 表示该 disjoint 部署没有任何 READABLE，C04 的正向主张不成立；"
            "这不否认 deployment 本身执行过。"
        ),
    }
    receipt_path = out / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "verdict": verdict,
        "readable": readable,
        "unreadable": unreadable,
        "marginal": marginal,
        "checks": checks,
        "receipt": str(receipt_path),
        "receipt_sha256": _sha256(receipt_path.read_bytes()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
